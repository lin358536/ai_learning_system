# 智途校园 - LLM Provider 层（DeepSeek OpenAI 兼容 API）
"""ChatOpenAI 封装：懒加载单例 get_llm() / get_llm_with_tools(tools)。"""
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.config import get_settings
from app.llm.model_config import get_model_params

# 模块级懒加载单例（共享约定：模块级变量 + 模块函数取用）
_llm_instance: BaseChatModel | None = None


def _build_llm() -> BaseChatModel:
    """构建 ChatOpenAI 实例（DeepSeek OpenAI 兼容端点）。"""
    # 延迟 import，避免模块加载期强依赖 langchain-openai
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError(
            "[zhitu][llm_provider] DEEPSEEK_API_KEY 未配置："
            "请在 backend/.env 中填写 DEEPSEEK_API_KEY 后重启服务"
        )

    params = get_model_params()
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        streaming=True,  # 关键：streaming=True 时 ainvoke 内部走流式请求，
                         # astream_events 才能冒泡出 on_chat_model_stream 增量
        temperature=params["temperature"],
        max_tokens=params["max_tokens"],
    )


def get_llm() -> BaseChatModel:
    """获取 LLM 懒加载单例。api_key 为空时抛出带 [zhitu] 前缀的明确异常。"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = _build_llm()
    return _llm_instance


def get_llm_with_tools(tools: list[BaseTool]) -> Any:
    """获取绑定了工具的 LLM（bind_tools 后的 Runnable）。tools 为空时返回裸 LLM。"""
    llm = get_llm()
    if tools:
        return llm.bind_tools(tools)
    return llm


def reset_llm() -> None:
    """重置单例（配置变更/测试时使用）。"""
    global _llm_instance
    _llm_instance = None
