# 智途校园 - 认证路由
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        data = await AuthService().register(
            db=db,
            username=req.username,
            password=req.password,
            email=req.email,
            name=req.name,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        msg = str(e)
        code = "CONFLICT"
        if "密码" in msg:
            code = "UNAUTHORIZED"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": code, "message": msg}},
        )


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        data = await AuthService().login(db=db, username=req.username, password=req.password)
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": {"code": "UNAUTHORIZED", "message": str(e)}},
        )


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        data = await AuthService().get_user_with_profile(db, user["user_id"])
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": str(e)}},
        )
