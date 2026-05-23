# 智途校园 - 能力维度计算服务
from datetime import datetime, timedelta
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.points import Point
from app.models.plan import LearningPlan, DailyTask
from app.models.chat import ChatMessage


class AbilityService:
    """能力维度服务 — 从用户行为数据计算能力雷达图维度"""

    async def get_abilities(self, db: AsyncSession, user_id: int) -> dict:
        """获取用户能力维度数据（0-1 范围）"""
        dimensions = [
            await self._study_time(db, user_id),
            await self._reading_volume(db, user_id),
            await self._knowledge_mastery(db, user_id),
            await self._goal_achievement(db, user_id),
            await self._continuous_checkin(db, user_id),
        ]
        return {
            "dimensions": dimensions,
            "updated_at": datetime.now().isoformat(),
        }

    async def _study_time(self, db: AsyncSession, user_id: int) -> dict:
        """学习时长 — 基于对话次数和活跃度"""
        result = await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.user_id == user_id)
        )
        conv_count = int(result.scalar() or 0)
        # 归一化：0-50次对话映射到 0-1
        value = min(conv_count / 50.0, 1.0)
        return {
            "name": "学习时长",
            "value": round(value, 2),
            "detail": f"{conv_count} 次对话",
        }

    async def _reading_volume(self, db: AsyncSession, user_id: int) -> dict:
        """阅读量 — 基于积分记录数量"""
        result = await db.execute(
            select(func.count(Point.id))
            .where(Point.user_id == user_id)
        )
        point_count = int(result.scalar() or 0)
        # 归一化：0-30条记录映射到 0-1
        value = min(point_count / 30.0, 1.0)
        return {
            "name": "阅读量",
            "value": round(value, 2),
            "detail": f"{point_count} 条记录",
        }

    async def _knowledge_mastery(self, db: AsyncSession, user_id: int) -> dict:
        """知识掌握 — 基于学习规划任务完成率"""
        plans_result = await db.execute(
            select(LearningPlan.id)
            .where(LearningPlan.user_id == user_id)
        )
        plan_ids = [p[0] for p in plans_result.all()]

        if not plan_ids:
            return {"name": "知识掌握", "value": 0.0, "detail": "暂无规划"}

        tasks_result = await db.execute(
            select(
                func.count(DailyTask.id),
                func.sum(case((DailyTask.status == "completed", 1), else_=0)),
            )
            .where(DailyTask.plan_id.in_(plan_ids))
        )
        row = tasks_result.first()
        total = int(row[0] or 0)
        completed = int(row[1] or 0)

        value = completed / total if total > 0 else 0.0
        return {
            "name": "知识掌握",
            "value": round(value, 2),
            "detail": f"{completed}/{total} 任务",
        }

    async def _goal_achievement(self, db: AsyncSession, user_id: int) -> dict:
        """目标达成 — 基于总积分相对于平均水平的比例"""
        total_result = await db.execute(
            select(func.coalesce(func.sum(Point.amount), 0))
            .where(Point.user_id == user_id)
        )
        user_total = int(total_result.scalar() or 0)

        subq = select(
            func.sum(Point.amount).label("total")
        ).group_by(Point.user_id).subquery()

        avg_result = await db.execute(
            select(func.avg(subq.c.total)).select_from(subq)
        )
        avg_points = float(avg_result.scalar() or 1)

        value = min(user_total / (avg_points * 1.5), 1.0) if avg_points > 0 else 0.0
        return {
            "name": "目标达成",
            "value": round(value, 2),
            "detail": f"{user_total} 积分",
        }

    async def _continuous_checkin(self, db: AsyncSession, user_id: int) -> dict:
        """连续打卡 — 基于最近活跃天数"""
        result = await db.execute(
            select(Point.created_at)
            .where(Point.user_id == user_id)
            .order_by(Point.created_at.desc())
        )
        dates = [r[0] for r in result.all() if r[0]]

        if not dates:
            return {"name": "连续打卡", "value": 0.0, "detail": "0 天"}

        streak = 0
        today = datetime.now().date()
        expected = today

        for dt in dates:
            d = dt.date() if isinstance(dt, datetime) else dt
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break

        # 归一化：0-30天映射到 0-1
        value = min(streak / 30.0, 1.0)
        return {
            "name": "连续打卡",
            "value": round(value, 2),
            "detail": f"{streak} 天",
        }
