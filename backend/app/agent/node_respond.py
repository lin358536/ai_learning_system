# 智途校园 - 节点：响应汇总
"""汇总 final_content、按任务文档 1.7 规则推导 intent、产出 done 事件所需字段。"""
from langchain_core.messages import AIMessage

from app.agent.intent import parse_intent_from_reply
from app.agent.state import AgentState
from app.llm import strip_think_tags


def make_respond_node(skill):
    """
    构造 respond 节点（闭包绑定本次路由的技能）。

    intent 推导规则（1.7）：
    1) 本次运行路由的 Skill 是 plan/resume → intent = generate_plan / generate_resume
    2) 否则 → parse_intent_from_reply(full_content)（关键词兜底）
    3) 否则 → "chat"
    """

    async def respond(state: AgentState) -> dict:
        # 取末条有内容的 AIMessage 作为最终回复
        final_content = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final_content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                break

        # 输出护栏：剥离 <think>/<thinkable> 标签
        final_content = strip_think_tags(final_content)

        # intent 推导（封闭集：generate_plan / generate_resume / chat）
        if skill.key == "plan":
            intent = "generate_plan"
        elif skill.key == "resume":
            intent = "generate_resume"
        else:
            intent = parse_intent_from_reply(final_content)

        print(
            f"[zhitu][node_respond] skill={skill.key} intent={intent} "
            f"content_len={len(final_content)}"
        )
        return {"final_content": final_content, "intent": intent}

    return respond
