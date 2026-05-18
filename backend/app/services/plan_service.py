# 智途校园 - 学习规划业务逻辑
import json
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import LearningPlan, DailyTask


class PlanService:
    """规划服务 — 查询、删除"""

    async def get_plans(self, db: AsyncSession, user_id: int) -> list[dict]:
        """获取用户规划列表（含进度）"""
        result = await db.execute(
            select(LearningPlan)
            .where(LearningPlan.user_id == user_id)
            .order_by(LearningPlan.created_at.desc())
        )
        plans = result.scalars().all()

        items = []
        for plan in plans:
            # 计算任务完成进度
            total = len(plan.tasks) if plan.tasks else 0
            completed = sum(1 for t in plan.tasks if t.status == "completed") if plan.tasks else 0
            progress = int(completed / total * 100) if total > 0 else 0

            items.append({
                "id": plan.id,
                "title": plan.title,
                "status": plan.status,
                "progress": progress,
                "total_tasks": total,
                "completed_tasks": completed,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
            })
        return items

    async def get_plan_detail(self, db: AsyncSession, plan_id: int, user_id: int) -> dict | None:
        """获取规划详情（含关联的每日任务）"""
        result = await db.execute(
            select(LearningPlan).where(
                LearningPlan.id == plan_id,
                LearningPlan.user_id == user_id,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None

        # 解析content JSON
        content = {}
        if plan.content:
            try:
                content = json.loads(plan.content) if isinstance(plan.content, str) else plan.content
            except (json.JSONDecodeError, TypeError):
                content = {}

        # 关联任务
        tasks = []
        if plan.tasks:
            tasks = [
                {
                    "id": t.id,
                    "content": t.content,
                    "status": t.status,
                    "task_date": t.task_date.isoformat() if t.task_date else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in plan.tasks
            ]

        return {
            "id": plan.id,
            "title": plan.title,
            "content": content,
            "status": plan.status,
            "tasks": tasks,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        }

    async def delete_plan(self, db: AsyncSession, plan_id: int, user_id: int) -> bool:
        """删除规划（级联删除关联任务由DB外键处理）"""
        result = await db.execute(
            select(LearningPlan).where(
                LearningPlan.id == plan_id,
                LearningPlan.user_id == user_id,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return False

        await db.delete(plan)
        await db.flush()
        return True

    async def save_plan(self, db: AsyncSession, user_id: int, title: str,
                        content: dict) -> LearningPlan:
        """保存确认后的规划，并生成每日任务"""
        plan = LearningPlan(
            user_id=user_id,
            title=title,
            content=json.dumps(content, ensure_ascii=False),
            status="confirmed",
        )
        db.add(plan)
        await db.flush()

        # 从规划内容中提取任务并生成每日任务
        tasks_data = content.get("daily_tasks", [])
        from datetime import date, timedelta

        for i, task_content in enumerate(tasks_data):
            task = DailyTask(
                user_id=user_id,
                plan_id=plan.id,
                content=task_content,
                status="pending",
                task_date=date.today() + timedelta(days=i),
            )
            db.add(task)
        await db.flush()

        return plan
