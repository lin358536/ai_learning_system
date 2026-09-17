# 智途校园 - 节点：LLM 调用
"""PromptManager 渲染 system prompt（首轮注入）+ bind_tools + 经 Harness 规范化调用。"""
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agent.state import AgentState
from app.llm import get_harness
from app.llm.llm_provider import get_llm_with_tools


def make_call_model_node(skill, tools: list[BaseTool]):
    """
    构造 call_model 节点（闭包绑定技能与工具集）。

    Args:
        skill: 当前技能（SkillBase 子类实例）
        tools: 该技能允许的 LangChain 工具列表
    """

    async def call_model(state: AgentState) -> dict:
        messages: list[BaseMessage] = list(state["messages"])

        # 防御性检查：若首条不是 SystemMessage（首轮注入由图工厂完成），补注入
        if not messages or not isinstance(messages[0], SystemMessage):
            system_prompt = skill.get_prompt(state.get("profile_context") or {})
            messages = [SystemMessage(content=system_prompt)] + messages

        # 工具绑定：tools 为空时不 bind（纯对话）
        llm = get_llm_with_tools(tools)

        # 经 Harness 包装：输入校验 + 指数退避重试 + 输出护栏 + trace 日志
        harness = get_harness()
        ai_message = await harness.invoke(
            llm,
            messages,
            skill_key=skill.key,
            trace_label=str(state.get("conversation_id") or "")[:8],
        )

        print(
            f"[zhitu][node_call_model] skill={skill.key} "
            f"round={state.get('tool_call_count', 0) + 1} "
            f"tool_calls={len(ai_message.tool_calls) if ai_message.tool_calls else 0}"
        )
        return {"messages": [ai_message]}

    return call_model
