# 智途校园 - LLM 工程化规范层（Harness）
"""输入校验、输出护栏、指数退避重试、trace_id 全链路日志。"""
import asyncio
import re
import time
import uuid

from langchain_core.messages import AIMessage, BaseMessage

from app.llm.model_config import is_retryable

# ── 工程化常量 ──────────────────────────────────────────────────
MAX_MESSAGES: int = 60          # 单次调用最大消息条数
MAX_INPUT_CHARS: int = 60000    # 单条消息最大字符数
MAX_OUTPUT_WARN: int = 8000     # 输出超长告警阈值
RETRY_MAX: int = 3              # 最大重试次数
RETRY_DELAYS: tuple[float, ...] = (2, 4, 8)  # 指数退避间隔（秒）

# 剥离推理模型输出中的思考标签：<think>...</think> / <thinkable>...</thinkable>
_THINK_TAG_RE = re.compile(
    r"<(?:think|thinking|thinkable)>(.*?)</(?:think|thinking|thinkable)>",
    re.DOTALL | re.IGNORECASE,
)
# 未闭合的思考标签（流式截断场景）：从开头标签起到文本末尾全部剥离
_THINK_OPEN_RE = re.compile(
    r"<(?:think|thinking|thinkable)>.*\Z",
    re.DOTALL | re.IGNORECASE,
)


def strip_think_tags(text: str) -> str:
    """
    输出护栏：剥离 <think>/<thinkable> 推理标签。

    同时处理闭合标签与流式截断产生的未闭合标签。
    """
    if not text:
        return text
    cleaned = _THINK_TAG_RE.sub("", text)
    cleaned = _THINK_OPEN_RE.sub("", cleaned)
    return cleaned.strip("\n")


class LLMHarness:
    """
    LLM 工程化规范层 —— 所有对 LLM 的调用统一经此包装：

    ① 输入校验（消息数/长度上限，拒绝空 user 消息）
    ② 调用（指数退避重试：3 次，2s/4s/8s，仅对网络/限流类异常）
    ③ 输出护栏（剥离 <think> 标签、内容长度告警）
    ④ trace：每次调用生成 trace_id，print [zhitu][harness][<trace_id>] ...
    """

    # ── 输入校验 ────────────────────────────────────────────────

    @staticmethod
    def validate_messages(messages: list[BaseMessage]) -> None:
        """校验消息列表：非空、条数上限、单条长度上限、最后一条必须是 user/非空内容。"""
        if not messages:
            raise ValueError("[zhitu][harness] 消息列表为空，拒绝调用 LLM")
        if len(messages) > MAX_MESSAGES:
            raise ValueError(
                f"[zhitu][harness] 消息条数超上限（{len(messages)} > {MAX_MESSAGES}），"
                "请缩短对话历史后重试"
            )
        for i, msg in enumerate(messages):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if len(content) > MAX_INPUT_CHARS:
                raise ValueError(
                    f"[zhitu][harness] 第 {i + 1} 条消息长度超上限"
                    f"（{len(content)} > {MAX_INPUT_CHARS} 字符）"
                )
        # 最后一条必须是用户消息（tool_calls 后的 ToolMessage 场景除外）
        last = messages[-1]
        if last.type == "human":
            content = last.content if isinstance(last.content, str) else str(last.content)
            if not content.strip():
                raise ValueError("[zhitu][harness] 用户消息内容为空，拒绝调用 LLM")

    # ── 输出护栏 ────────────────────────────────────────────────

    @staticmethod
    def guard_output(message: AIMessage) -> AIMessage:
        """输出护栏：剥离思考标签、超长告警（原对象不变，返回处理后的副本）。"""
        content = message.content if isinstance(message.content, str) else ""
        cleaned = strip_think_tags(content)
        if len(cleaned) > MAX_OUTPUT_WARN:
            print(
                f"[zhitu][harness] 输出内容超长告警: {len(cleaned)} 字符"
                f"（阈值 {MAX_OUTPUT_WARN}）"
            )
        if cleaned != content:
            message = message.model_copy(update={"content": cleaned})
        return message

    # ── 主入口 ──────────────────────────────────────────────────

    async def invoke(
        self,
        llm,
        messages: list[BaseMessage],
        *,
        skill_key: str = "chat",
        trace_label: str = "",
    ) -> AIMessage:
        """
        规范化的 LLM 调用入口。

        Args:
            llm: 已（可选）bind_tools 的 chat model（Runnable）
            messages: 消息列表（含 SystemMessage / 历史 / HumanMessage / ToolMessage）
            skill_key: 当前技能 key（观测日志用）
            trace_label: 追踪标签（如 conversation_id 前 8 位）

        Returns:
            AIMessage —— 输出护栏处理后的模型响应

        Raises:
            ValueError: 输入校验失败（不重试）
            原 LLM 异常: 重试耗尽后原样抛出（附重试日志）
        """
        trace_id = uuid.uuid4().hex[:8]
        label = f"[zhitu][harness][{trace_id}]"
        if trace_label:
            label = f"[zhitu][harness][{trace_id}][{trace_label}]"

        # ① 输入校验
        self.validate_messages(messages)

        # ② 指数退避重试调用（仅网络/限流类异常重试）
        start_ts = time.monotonic()
        last_exc: BaseException | None = None
        result: AIMessage | None = None
        for attempt in range(1, RETRY_MAX + 1):
            try:
                result = await llm.ainvoke(messages)
                break
            except Exception as exc:
                last_exc = exc
                if not is_retryable(exc) or attempt == RETRY_MAX:
                    break
                delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                print(
                    f"{label} skill={skill_key} 第 {attempt} 次调用失败"
                    f"（{type(exc).__name__}: {str(exc)[:120]}），{delay}s 后重试"
                )
                await asyncio.sleep(delay)

        if result is None:
            print(
                f"{label} skill={skill_key} 调用最终失败: "
                f"{type(last_exc).__name__}: {str(last_exc)[:200] if last_exc else 'unknown'}"
            )
            assert last_exc is not None
            raise last_exc

        # ③ 输出护栏
        result = self.guard_output(result)

        # ④ trace 日志（token 估算：中文≈字符数，粗略观测值）
        content_len = len(result.content) if isinstance(result.content, str) else 0
        elapsed_ms = int((time.monotonic() - start_ts) * 1000)
        tool_calls = len(result.tool_calls) if result.tool_calls else 0
        print(
            f"{label} skill={skill_key} tokens≈{content_len} "
            f"tool_calls={tool_calls} 耗时{elapsed_ms}ms"
        )
        return result


# 模块级懒加载单例
_harness: LLMHarness | None = None


def get_harness() -> LLMHarness:
    """获取 LLMHarness 懒加载单例。"""
    global _harness
    if _harness is None:
        _harness = LLMHarness()
    return _harness
