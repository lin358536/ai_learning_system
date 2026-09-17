# 智途校园 - Agent 重构验证：LLMHarness
"""覆盖 T02 验收：输入校验、指数退避重试、think 标签剥离（含未闭合）。"""
import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.llm import llm_harness
from app.llm.llm_harness import LLMHarness, strip_think_tags
from app.llm.model_config import is_retryable, is_tool_call_failure


class FakeLLM:
    """可控的假 LLM：按脚本抛异常或返回固定 AIMessage。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        action = self.script.pop(0) if self.script else AIMessage(content="ok")
        if isinstance(action, BaseException):
            raise action
        return action


class TestValidateMessages:
    def test_empty_list_rejected(self):
        with pytest.raises(ValueError, match="消息列表为空"):
            LLMHarness.validate_messages([])

    def test_too_many_messages_rejected(self):
        msgs = [HumanMessage(content=f"m{i}") for i in range(llm_harness.MAX_MESSAGES + 1)]
        with pytest.raises(ValueError, match="超上限"):
            LLMHarness.validate_messages(msgs)

    def test_oversized_message_rejected(self):
        msgs = [HumanMessage(content="x" * (llm_harness.MAX_INPUT_CHARS + 1))]
        with pytest.raises(ValueError, match="长度超上限"):
            LLMHarness.validate_messages(msgs)

    def test_empty_last_human_message_rejected(self):
        msgs = [SystemMessage(content="s"), HumanMessage(content="   ")]
        with pytest.raises(ValueError, match="内容为空"):
            LLMHarness.validate_messages(msgs)

    def test_valid_messages_pass(self):
        LLMHarness.validate_messages(
            [SystemMessage(content="s"), HumanMessage(content="你好")]
        )

    def test_tool_message_tail_allowed(self):
        """tool 循环中末条是 ToolMessage 的场景合法。"""
        LLMHarness.validate_messages(
            [
                SystemMessage(content="s"),
                HumanMessage(content="查积分"),
                ToolMessage(content="总积分 100", tool_call_id="c1"),
            ]
        )


class TestStripThinkTags:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("<think>推理过程</think>正式回答", "正式回答"),
            ("<thinkable>想</thinkable>答案", "答案"),
            ("<THINK>大写标签</THINK>内容", "内容"),
            ("前缀<think>多行\n推理\n过程</think>后缀", "前缀后缀"),
            ("正式回答<think>未闭合的推理流式截断", "正式回答"),  # 未闭合剥离到末尾
            ("<think>只有未闭合标签", ""),
            ("没有标签的正常文本", "没有标签的正常文本"),
            ("", ""),
        ],
    )
    def test_strip(self, raw, expected):
        assert strip_think_tags(raw) == expected


class TestRetry:
    async def test_retry_exhaustion_after_3_attempts(self, monkeypatch):
        """不可达异常 3 次后退避抛出（T02 验收）。"""
        monkeypatch.setattr(llm_harness, "RETRY_DELAYS", (0.01, 0.01, 0.01))
        fake = FakeLLM([httpx.ConnectError("boom")] * 3)
        with pytest.raises(httpx.ConnectError):
            await LLMHarness().invoke(fake, [HumanMessage(content="hi")])
        assert fake.calls == 3, f"应重试 3 次，实际 {fake.calls} 次"

    async def test_non_retryable_raises_immediately(self, monkeypatch):
        monkeypatch.setattr(llm_harness, "RETRY_DELAYS", (0.01, 0.01, 0.01))
        fake = FakeLLM([ValueError("参数错误")])
        with pytest.raises(ValueError):
            await LLMHarness().invoke(fake, [HumanMessage(content="hi")])
        assert fake.calls == 1, "不可重试异常不应重试"

    async def test_succeed_after_transient_failures(self, monkeypatch):
        monkeypatch.setattr(llm_harness, "RETRY_DELAYS", (0.01, 0.01, 0.01))
        fake = FakeLLM(
            [httpx.ConnectError("boom"), httpx.ReadTimeout("t"), AIMessage(content="成功")]
        )
        result = await LLMHarness().invoke(fake, [HumanMessage(content="hi")])
        assert result.content == "成功"
        assert fake.calls == 3

    async def test_output_guard_strips_think_on_result(self):
        fake = FakeLLM([AIMessage(content="<think>推理</think>干净回答")])
        result = await LLMHarness().invoke(fake, [HumanMessage(content="hi")])
        assert result.content == "干净回答"

    async def test_trace_id_log(self, capsys):
        fake = FakeLLM([AIMessage(content="ok")])
        await LLMHarness().invoke(fake, [HumanMessage(content="hi")], skill_key="chat")
        out = capsys.readouterr().out
        assert "[zhitu][harness][" in out
        assert "skill=chat" in out


class TestRetryableJudgement:
    def test_network_errors_retryable(self):
        assert is_retryable(httpx.ConnectError("x"))
        assert is_retryable(httpx.ReadTimeout("x"))
        assert is_retryable(httpx.ConnectTimeout("x"))

    def test_value_error_not_retryable(self):
        assert not is_retryable(ValueError("x"))

    def test_tool_call_failure_judgement(self):
        assert is_tool_call_failure(ValueError("invalid tool_calls format"))
        assert not is_tool_call_failure(ValueError("other error"))
