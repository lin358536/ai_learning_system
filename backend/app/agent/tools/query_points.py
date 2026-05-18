# 智途校园 - 工具：查询积分
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.points_service import PointsService


class QueryPointsTool(BaseTool):
    """查询用户积分"""

    @property
    def key(self) -> str:
        return "query_points"

    @property
    def name(self) -> str:
        return "查询积分"

    @property
    def description(self) -> str:
        return "查看积分、我的积分、积分多少、积分排行、排名"

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        points_service = PointsService()
        data = await points_service.get_user_points(db, user_id)

        recent_lines = ""
        if data["recent"]:
            recent_lines = "\n\n最近积分记录：\n"
            for r in data["recent"][:5]:
                date_str = r["created_at"][:10] if r["created_at"] else ""
                recent_lines += f"- {date_str} {r['reason']} {'+' if r['amount'] > 0 else ''}{r['amount']}\n"

        return {
            "summary": (
                f"你的积分情况：\n"
                f"- 总积分: {data['total']} 分\n"
                f"- 排名: 第 {data['rank']} 名（共 {data['total_users']} 人）"
                f"{recent_lines}"
            ),
        }
