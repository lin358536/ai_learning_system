# 智途校园 - LLM 模型参数与降级策略
"""集中管理 LLM 采样参数、降级策略常量与工具调用失败判定。"""
import httpx
import openai

from app.core.config import get_settings


def get_model_params() -> dict:
    """获取 LLM 采样参数（从 get_settings() 读取，禁止硬编码）。"""
    settings = get_settings()
    return {
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }


# ── 降级策略常量 ────────────────────────────────────────────────
# DeepSeek 工具调用连续失败 N 次后，降级为「无工具 + 关键词意图路由」模式
TOOL_CALL_FAILURE_THRESHOLD: int = 3

# 备用 provider（Qwen），DeepSeek 整体不可用时可切换（本期仅保留配置，不自动切换）
FALLBACK_PROVIDER: str = "qwen"


def is_tool_call_failure(exc: BaseException) -> bool:
    """
    判定异常是否属于「工具调用类失败」。

    覆盖场景：
    - OpenAI 兼容层抛出的工具调用参数/格式错误（BadRequestError 中含 tool 字样）
    - 模型返回了无法解析的 tool_calls
    """
    if isinstance(exc, openai.BadRequestError):
        msg = str(exc).lower()
        if "tool" in msg or "function" in msg:
            return True
    if isinstance(exc, ValueError) and "tool_call" in str(exc).lower():
        return True
    return False


def is_retryable(exc: BaseException) -> bool:
    """
    判定异常是否可重试（仅网络/限流类）。

    可重试：连接错误、超时、限流(429)、服务端错误(>=500)
    不可重试：鉴权失败(401/403)、参数错误(400)、模型不存在(404)
    """
    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout,
                        httpx.PoolTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, openai.APITimeoutError):
        return True
    if isinstance(exc, openai.APIConnectionError):
        return True
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.InternalServerError):
        return True
    return False
