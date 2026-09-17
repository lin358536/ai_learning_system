# 智途校园 - Agent 状态定义
"""AgentState：仅含可序列化字段，绝不放 db_session 等请求级对象。"""
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    LangGraph 全局状态。

    设计约束（任务文档 1.1）：
    - AsyncSession 不可序列化，会破坏 state 快照与 add_messages reducer 的纯函数约定；
    - 请求级依赖（db/user_id 的会话句柄）一律经 ToolContext 在 build_agent_graph
      工厂闭包中绑定，不进 state。
    """

    # 对话消息（含 SystemMessage / HumanMessage / AIMessage / ToolMessage），
    # add_messages reducer 负责追加合并
    messages: Annotated[list, add_messages]
    # 业务字段（可序列化）
    user_id: int
    conversation_id: str
    intent: str
    profile_context: dict
    tool_call_count: int
    final_content: str
