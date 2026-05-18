# 智途校园 - 积分路由
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.points_service import PointsService

router = APIRouter(prefix="/points", tags=["积分"])


@router.get("")
async def get_points(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PointsService()
    data = await service.get_user_points(db, user["user_id"])
    return {"success": True, "data": data}


@router.get("/rank")
async def get_ranking(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = PointsService()
    data = await service.get_ranking(db, limit=limit)
    return {"success": True, "data": {"leaderboard": data}}
