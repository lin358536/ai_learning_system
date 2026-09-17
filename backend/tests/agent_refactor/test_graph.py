# 智途校园 - Agent 重构验证：LangGraph 图结构与节点
"""覆盖 T04 验收（离线部分）：图编译、state 可序列化、初始消息结构、
[待确认] 过滤、工具节点容错、respond 节点 intent 推导（任务书 1.7）。"""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel


class _EmptyArgs(BaseModel):
    """无入参工具的 args_schema（langchain 在 func=None 时不做签名推断，需显式提供）"""

from app.agent.graph import _history_to_messages, build_agent_graph
from app.agent.node_execute_tool import TOOL_RESULT_MAX_CHARS, make_execute_tool_node
from app.agent.node_respond import make_respond_node
from app.agent.tools.toolkit import ToolContext
from app.skills.skill_engine import get_skill_engine


class _FakeSkill:
    def __init__(self, key):
        self.key = key

    def get_prompt(self, ctx):
        return "假 system prompt"


def _ctx():
    return ToolContext(db=None, user_id=3)


class TestBuildGraph:
    def test_compiles(self):
        skill = get_skill_engine().route(None)
        graph, initial = build_agent_graph(_ctx(), skill, [], [], "你好")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream_events")

    def test_initial_state_serializable(self):
        """任务书 1.1：state 不含 db 等不可序列化对象。"""
        skill = get_skill_engine().route(None)
        _, initial = build_agent_graph(_ctx(), skill, [], [], "你好")
        business = {k: v for k, v in initial.items() if k != "messages"}
        json.dumps(business)  # 不抛异常即可序列化
        assert "db" not in business
        assert set(initial.keys()) == {
            "messages",
            "user_id",
            "conversation_id",
            "intent",
            "profile_context",
            "tool_call_count",
            "final_content",
        }

    def test_initial_message_structure(self):
        """共享约定 9：System + History + Human。"""
        skill = get_skill_engine().route(None)
        history = [
            {"role": "user", "content": "之前的提问"},
            {"role": "assistant", "content": "之前的回答"},
        ]
        _, initial = build_agent_graph(_ctx(), skill, [], history, "本轮消息")
        msgs = initial["messages"]
        assert isinstance(msgs[0], SystemMessage)
        assert isinstance(msgs[-1], HumanMessage)
        assert msgs[-1].content == "本轮消息"
        assert isinstance(msgs[1], HumanMessage)
        assert isinstance(msgs[2], AIMessage)
        # system prompt 非空且为技能渲染产物
        assert len(msgs[0].content) > 100

    def test_pending_confirmation_filtered(self):
        history = [
            {"role": "assistant", "content": "[待确认] 是否生成规划？"},
            {"role": "user", "content": "正常消息"},
            {"role": "assistant", "content": ""},  # 空内容过滤
        ]
        msgs = _history_to_messages(history)
        assert len(msgs) == 1
        assert msgs[0].content == "正常消息"

    def test_long_history_content_truncated(self):
        msgs = _history_to_messages([{"role": "user", "content": "x" * 3000}])
        assert len(msgs[0].content) == 2003  # 2000 + "..."

    def test_empty_history_and_empty_conversation(self):
        """边界：空历史首轮对话。"""
        msgs = _history_to_messages([])
        assert msgs == []
        msgs = _history_to_messages(None)
        assert msgs == []


class TestGraphRuntime:
    async def test_empty_key_error_propagates(self, empty_key_env):
        """空 key 下图运行至 LLM 调用处抛出带 [zhitu] 的 RuntimeError（供 API 层包装）。

        前置条件由 empty_key_env 夹具显式注入空 key（不依赖真实 .env）。
        """
        skill = get_skill_engine().route(None)
        graph, initial = build_agent_graph(_ctx(), skill, [], [], "你好")
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            await graph.ainvoke(initial)


class TestExecuteToolNode:
    def _state_with_tool_calls(self, tool_calls, count=0):
        return {
            "messages": [AIMessage(content="", tool_calls=tool_calls)],
            "tool_call_count": count,
        }

    async def test_unknown_tool_friendly_message(self):
        node = make_execute_tool_node({"query_points": object()})
        state = self._state_with_tool_calls(
            [{"name": "hack_tool", "args": {}, "id": "c1"}]
        )
        out = await node(state)
        tm = out["messages"][0]
        assert isinstance(tm, ToolMessage)
        assert "未知工具" in tm.content
        assert "hack_tool" in tm.content

    async def test_tool_exception_not_crash(self):
        """T04 验收：工具内部抛异常 → 图不崩，回友好文案。"""

        async def _boom():
            raise RuntimeError("数据库连接失败")

        bad_tool = StructuredTool(name="bad_tool", description="t", func=None, coroutine=_boom, args_schema=_EmptyArgs)
        node = make_execute_tool_node({"bad_tool": bad_tool})
        state = self._state_with_tool_calls([{"name": "bad_tool", "args": {}, "id": "c1"}])
        out = await node(state)
        tm = out["messages"][0]
        assert "执行出错" in tm.content
        assert "bad_tool" in tm.content

    async def test_tool_result_truncation(self):
        async def _long():
            return "y" * (TOOL_RESULT_MAX_CHARS + 500)

        long_tool = StructuredTool(name="long_tool", description="t", func=None, coroutine=_long, args_schema=_EmptyArgs)
        node = make_execute_tool_node({"long_tool": long_tool})
        state = self._state_with_tool_calls([{"name": "long_tool", "args": {}, "id": "c1"}])
        out = await node(state)
        tm = out["messages"][0]
        assert "已截断" in tm.content
        assert len(tm.content) < TOOL_RESULT_MAX_CHARS + 100

    async def test_tool_call_count_increments(self):
        async def _ok():
            return "done"

        ok_tool = StructuredTool(name="ok_tool", description="t", func=None, coroutine=_ok, args_schema=_EmptyArgs)
        node = make_execute_tool_node({"ok_tool": ok_tool})
        state = self._state_with_tool_calls(
            [{"name": "ok_tool", "args": {}, "id": "c1"}], count=2
        )
        out = await node(state)
        assert out["tool_call_count"] == 3

    async def test_multiple_tool_calls_in_one_round(self):
        async def _ok():
            return "r"

        ok_tool = StructuredTool(name="ok_tool", description="t", func=None, coroutine=_ok, args_schema=_EmptyArgs)
        node = make_execute_tool_node({"ok_tool": ok_tool})
        state = self._state_with_tool_calls(
            [
                {"name": "ok_tool", "args": {}, "id": "c1"},
                {"name": "ghost", "args": {}, "id": "c2"},
            ]
        )
        out = await node(state)
        assert len(out["messages"]) == 2


class TestRespondNode:
    def _state(self, content):
        return {"messages": [AIMessage(content=content)]}

    async def test_plan_skill_forces_generate_plan(self):
        """1.7 规则 1：plan 技能 → intent=generate_plan（无论内容）。"""
        node = make_respond_node(_FakeSkill("plan"))
        out = await node(self._state("随便什么内容"))
        assert out["intent"] == "generate_plan"

    async def test_resume_skill_forces_generate_resume(self):
        node = make_respond_node(_FakeSkill("resume"))
        out = await node(self._state("随便什么内容"))
        assert out["intent"] == "generate_resume"

    async def test_chat_skill_fallback_parse(self):
        """1.7 规则 2/3：chat 技能按回复内容兜底解析。"""
        node = make_respond_node(_FakeSkill("chat"))
        out = await node(self._state("阶段一 目标 任务清单：..."))
        assert out["intent"] == "generate_plan"
        out2 = await node(self._state("今天聊得很开心"))
        assert out2["intent"] == "chat"

    async def test_think_tags_stripped_in_final(self):
        node = make_respond_node(_FakeSkill("chat"))
        out = await node(self._state("<think>推理</think>最终答案"))
        assert out["final_content"] == "最终答案"

    async def test_intent_closed_set(self):
        node = make_respond_node(_FakeSkill("chat"))
        out = await node(self._state("任意内容"))
        assert out["intent"] in {"generate_plan", "generate_resume", "chat"}
