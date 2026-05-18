# 智途校园 - 积分业务逻辑
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.points import Point


class PointsService:
    """积分服务 — 查询、排名、奖励"""

    async def add_points(self, db: AsyncSession, user_id: int, amount: int,
                         reason: str, source: str) -> Point:
        """添加积分记录"""
        point = Point(
            user_id=user_id,
            amount=amount,
            reason=reason,
            source=source,
        )
        db.add(point)
        await db.flush()
        return point

    async def get_user_points(self, db: AsyncSession, user_id: int) -> dict:
        """获取用户积分信息：总数、排名、近期记录"""
        # 总积分
        total_result = await db.execute(
            select(func.coalesce(func.sum(Point.amount), 0))
            .where(Point.user_id == user_id)
        )
        total = int(total_result.scalar() or 0)

        # 排名（比当前用户积分高的用户数 + 1）
        rank_result = await db.execute(
            select(func.count())
            .select_from(
                select(Point.user_id)
                .group_by(Point.user_id)
                .having(func.sum(Point.amount) > total)
                .subquery()
            )
        )
        rank = int(rank_result.scalar() or 0) + 1

        # 总用户数
        users_result = await db.execute(select(func.count(User.id)))
        total_users = int(users_result.scalar() or 0)

        # 近期记录（最近10条）
        recent_result = await db.execute(
            select(Point)
            .where(Point.user_id == user_id)
            .order_by(Point.created_at.desc())
            .limit(10)
        )
        recent = recent_result.scalars().all()

        return {
            "total": total,
            "rank": rank,
            "total_users": total_users,
            "recent": [
                {
                    "amount": p.amount,
                    "reason": p.reason,
                    "source": p.source,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in recent
            ],
        }

    async def get_ranking(self, db: AsyncSession, limit: int = 10) -> list[dict]:
        """获取积分排行榜"""
        result = await db.execute(
            select(
                Point.user_id,
                func.sum(Point.amount).label("total"),
            )
            .group_by(Point.user_id)
            .order_by(func.sum(Point.amount).desc())
            .limit(limit)
        )
        rows = result.all()

        leaderboard = []
        for index, (uid, total) in enumerate(rows):
            # 查用户名
            user_result = await db.execute(select(User).where(User.id == uid))
            user = user_result.scalar_one_or_none()
            leaderboard.append({
                "rank": index + 1,
                "name": user.name if user else "匿名",
                "points": int(total),
            })

        return leaderboard
