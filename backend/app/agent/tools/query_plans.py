# 智途校园 - 工具：查询学习规划
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.plan_service import PlanService

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool
    from app.agent.tools.toolkit import ToolContext


class QueryPlansTool(BaseTool):
    """查询用户的学习规划列表"""

    @property
    def key(self) -> str:
        return "query_plans"

    @property
    def name(self) -> str:
        return "查询学习规划"

    @property
    def description(self) -> str:
        return "查看学习规划、我的规划、规划列表、规划进度"

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        plan_service = PlanService()
        plans = await plan_service.get_plans(db, user_id)

        if not plans:
            return {"summary": "你还没有学习规划，告诉我你的专业和目标岗位，我可以帮你制定一份。"}

        # 构建摘要
        lines = []
        for p in plans:
            status_text = {"draft": "草稿", "confirmed": "进行中", "archived": "已归档"}.get(p["status"], p["status"])
            lines.append(
                f"- 《{p['title']}》状态: {status_text}，"
                f"进度: {p['progress']}%（{p['completed_tasks']}/{p['total_tasks']}任务）"
            )

        return {
            "summary": f"你有 {len(plans)} 个学习规划：\n" + "\n".join(lines),
            "plans": plans,
        }


# ── LangChain StructuredTool 工厂（Agent 重构新增，旧类原样保留） ──

class QueryPlansArgs(BaseModel):
    """query_plans 入参（无参数，查询当前用户全部规划）"""


def make_tool(ctx: "ToolContext") -> "StructuredTool":
    """构造绑定 ToolContext 的 LangChain 工具（复用旧 QueryPlansTool 的业务逻辑与 summary 文案）。"""
    from langchain_core.tools import StructuredTool

    async def _arun() -> str:
        tool = QueryPlansTool()
        result = await tool.execute(ctx.db, ctx.user_id)
        return str(result.get("summary", ""))

    return StructuredTool(
        name="query_plans",
        description="查询当前用户的学习规划列表（标题、状态、进度）。无需参数。",
        func=None,
        coroutine=_arun,
        args_schema=QueryPlansArgs,
    )
