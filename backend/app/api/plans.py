# 智途校园 - 学习规划路由
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.plan import DailyTask, LearningPlan
from app.models.points import Point
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["学习规划"])


class ToggleTaskRequest(BaseModel):
    completed: bool


@router.get("")
async def get_plans(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PlanService()
    plans = await service.get_plans(db, user["user_id"])
    return {"success": True, "data": {"plans": plans}}


@router.get("/{plan_id}")
async def get_plan_detail(
    plan_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PlanService()
    plan = await service.get_plan_detail(db, plan_id, user["user_id"])
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "规划不存在"}},
        )
    return {"success": True, "data": plan}


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PlanService()
    ok = await service.delete_plan(db, plan_id, user["user_id"])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "规划不存在"}},
        )
    return {"success": True, "data": {"message": "规划已删除"}}


@router.patch("/{plan_id}/tasks/{task_id}")
async def toggle_task(
    plan_id: int,
    task_id: int,
    req: ToggleTaskRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """切换任务完成状态，首次完成时加积分"""
    user_id = user["user_id"]

    # 验证规划归属
    plan = await db.execute(
        select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user_id)
    )
    plan_obj = plan.scalar_one_or_none()
    if not plan_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "规划不存在"}})

    # 查任务
    task = await db.execute(
        select(DailyTask).where(DailyTask.id == task_id, DailyTask.plan_id == plan_id, DailyTask.user_id == user_id)
    )
    task_obj = task.scalar_one_or_none()
    if not task_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "任务不存在"}})

    was_completed = task_obj.status == "completed"
    points_earned = 0

    if req.completed and not was_completed:
        # 标记完成 + 首次完成加积分
        task_obj.status = "completed"
        task_obj.completed_at = datetime.now()
        # 防止并发重复加分
        existing = await db.execute(
            select(Point).where(
                Point.user_id == user_id,
                Point.source == "task_complete",
                Point.reason == f"完成学习任务：{task_obj.content[:50]}",
            )
        )
        if not existing.scalar_one_or_none():
            point = Point(
                user_id=user_id,
                amount=5,
                reason=f"完成学习任务：{task_obj.content[:50]}",
                source="task_complete",
            )
            db.add(point)
            points_earned = 5
    elif not req.completed and was_completed:
        # 取消完成（不扣回积分）
        task_obj.status = "pending"
        task_obj.completed_at = None

    await db.flush()

    # 计算更新后的规划进度
    all_tasks = await db.execute(
        select(DailyTask).where(DailyTask.plan_id == plan_id)
    )
    tasks_list = all_tasks.scalars().all()
    total = len(tasks_list)
    completed = sum(1 for t in tasks_list if t.status == "completed")
    progress = int(completed / total * 100) if total > 0 else 0

    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "status": task_obj.status,
            "completed_at": task_obj.completed_at.isoformat() if task_obj.completed_at else None,
            "plan_progress": {
                "total": total,
                "completed": completed,
                "progress": progress,
            },
            "points_earned": points_earned,
        },
    }
