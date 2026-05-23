# 智途校园 - 能力维度路由
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.ability_service import AbilityService

router = APIRouter(prefix="/abilities", tags=["能力维度"])


@router.get("")
async def get_abilities(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AbilityService()
    data = await service.get_abilities(db, user["user_id"])
    return {"success": True, "data": data}
