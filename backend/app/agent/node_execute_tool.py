# 智途校园 - 节点：工具执行
"""遍历 tool_calls → 闭包工具执行 → ToolMessage 回写 state，异常转友好文案。"""
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.state import AgentState

# 单个工具执行结果超过此长度时截断，防止撑爆上下文
TOOL_RESULT_MAX_CHARS: int = 8000


def make_execute_tool_node(tool_map: dict[str, BaseTool]):
    """
    构造 execute_tool 节点（闭包绑定工具字典）。

    Args:
        tool_map: 工具名 → StructuredTool（由 build_agent_graph 从 tools 构建，
                  ToolContext 已在工厂闭包中绑定 db/user_id）
    """

    async def execute_tool(state: AgentState) -> dict:
        messages = state["messages"]
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"tool_call_count": state.get("tool_call_count", 0)}

        tool_messages: list[ToolMessage] = []
        for tc in last.tool_calls:
            name = tc.get("name", "")
            args = tc.get("args") or {}
            call_id = tc.get("id", "")

            tool = tool_map.get(name)
            if tool is None:
                # 未注册工具：直接回友好文案，不中断图
                content = f"未知工具：{name}。可用工具：{', '.join(tool_map.keys())}"
                tool_messages.append(ToolMessage(content=content, tool_call_id=call_id))
                continue

            try:
                output = await tool.ainvoke(args)
                content = output if isinstance(output, str) else str(output)
            except Exception as e:
                # 单工具异常 catch 住，返回错误文案 ToolMessage，图继续跑
                print(f"[zhitu][node_execute_tool] 工具 {name} 执行异常: {type(e).__name__}: {e}")
                content = (
                    f"工具 {name} 执行出错：{str(e)[:200]}。"
                    "请基于已有信息继续回答，或告知用户该功能暂时不可用。"
                )

            # 超长截断
            if len(content) > TOOL_RESULT_MAX_CHARS:
                content = content[:TOOL_RESULT_MAX_CHARS] + "\n...(工具结果过长，已截断)"

            tool_messages.append(ToolMessage(content=content, tool_call_id=call_id))

        new_count = state.get("tool_call_count", 0) + 1
        print(
            f"[zhitu][node_execute_tool] 执行 {len(tool_messages)} 个工具调用，"
            f"累计轮次 {new_count}"
        )
        return {"messages": tool_messages, "tool_call_count": new_count}

    return execute_tool
