# 智途校园 - LangGraph Agent 图工厂
"""graph 工厂：组装 call_model ⟷ execute_tool → respond，max_iter 防死循环。"""
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from app.agent.node_call_model import make_call_model_node
from app.agent.node_execute_tool import make_execute_tool_node
from app.agent.node_respond import make_respond_node
from app.agent.state import AgentState
from app.agent.tools.toolkit import ToolContext
from app.core.config import get_settings


def _history_to_messages(history: list[dict]) -> list[BaseMessage]:
    """
    将 chat_messages 加载的历史（[{"role","content"},...]）转为 LangChain 消息。

    - 过滤 "[待确认]" 前缀消息（旧 confirm 流程遗留，本期不使用）
    - 过滤过长内容（单条 >2000 字符截断，防上下文膨胀）
    """
    messages: list[BaseMessage] = []
    for msg in history or []:
        role = msg.get("role")
        content = str(msg.get("content") or "").strip()
        if not content or content.startswith("[待确认]"):
            continue
        if len(content) > 2000:
            content = content[:2000] + "..."
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def build_agent_graph(
    ctx: ToolContext,
    skill,
    tools: list[BaseTool],
    history: list[dict],
    user_message: str,
    *,
    conversation_id: str | None = None,
    profile_context: dict | None = None,
) -> tuple[Any, dict]:
    """
    构建 LangGraph Agent 图（请求级实例，闭包绑定 ctx / skill / tools）。

    Args:
        ctx: ToolContext(db, user_id) —— 只存在于闭包中，不进 AgentState
        skill: 本次路由的技能（SkillBase 子类）
        tools: 技能允许的工具列表（已闭包绑定 ctx）
        history: 对话历史 [{"role","content"},...]（最近 N 轮）
        user_message: 用户原始消息
        conversation_id: 会话 ID（观测/trace 用）
        profile_context: 用户画像（渲染 system prompt 用）

    Returns:
        (compiled_graph, initial_input) 二元组：
        - compiled_graph: 编译后的 LangGraph，调用方 astream_events(initial_input, version="v2")
        - initial_input: 初始 state（messages 已含首轮注入的 SystemMessage）
    """
    # ── 初始消息：SystemMessage(技能 prompt，画像已注入) + 历史 + 用户消息 ──
    # 注意：不再拼 build_context_message 的中文上下文块（画像已在 system prompt 注入）
    system_prompt = skill.get_prompt(profile_context or {})
    init_messages: list[BaseMessage] = [
        SystemMessage(content=system_prompt),
        *_history_to_messages(history),
        HumanMessage(content=user_message),
    ]

    initial_input: dict = {
        "messages": init_messages,
        "user_id": ctx.user_id,
        "conversation_id": conversation_id or "",
        "intent": "",
        "profile_context": profile_context or {},
        "tool_call_count": 0,
        "final_content": "",
    }

    # ── 闭包绑定的节点 ──
    tool_map = {t.name: t for t in tools}
    call_model = make_call_model_node(skill, tools)
    execute_tool = make_execute_tool_node(tool_map)
    respond = make_respond_node(skill)

    # ── 条件边：末条消息有 tool_calls → execute_tool，否则 → respond ──
    def route_after_model(state: AgentState) -> str:
        max_iter = get_settings().AGENT_MAX_ITER
        # 防死循环：工具循环轮数达上限时强制走 respond
        if state.get("tool_call_count", 0) >= max_iter:
            print(f"[zhitu][graph] 达到最大工具轮次 {max_iter}，强制进入 respond")
            return "respond"
        last = state["messages"][-1] if state["messages"] else None
        if isinstance(last, AIMessage) and last.tool_calls:
            return "execute_tool"
        return "respond"

    builder = StateGraph(AgentState)
    builder.add_node("call_model", call_model)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("respond", respond)

    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        route_after_model,
        {"execute_tool": "execute_tool", "respond": "respond"},
    )
    builder.add_edge("execute_tool", "call_model")
    builder.add_edge("respond", END)

    graph = builder.compile()
    return graph, initial_input
