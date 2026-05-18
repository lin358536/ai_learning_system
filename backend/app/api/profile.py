# 智途校园 - 画像路由
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.profile import ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["个人画像"])


@router.get("")
async def get_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService()
    profile = await service.get_profile(db, user["user_id"])
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "用户画像不存在"}},
        )
    return {"success": True, "data": profile}


@router.put("")
async def update_profile(
    req: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService()
    try:
        data = await service.update_profile(db, user["user_id"], req.model_dump(exclude_none=True))
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": str(e)}},
        )
