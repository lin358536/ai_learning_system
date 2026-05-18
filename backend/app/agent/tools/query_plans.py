# 智途校园 - 工具：查询学习规划
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.plan_service import PlanService


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
