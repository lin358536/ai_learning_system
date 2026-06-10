# 智途校园 - 认证业务逻辑
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile
from app.core.security import hash_password, create_access_token


class AuthService:
    """认证服务 — 注册、登录、用户查询"""

    async def register(self, db: AsyncSession, username: str, password: str,
                       email: str | None, name: str | None) -> dict:
        """注册新用户，自动创建空白画像"""
        # 检查用户名
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 检查邮箱
        if email:
            existing_email = await db.execute(select(User).where(User.email == email))
            if existing_email.scalar_one_or_none():
                raise ValueError("邮箱已被注册")

        # 创建用户
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            name=name or username,
        )
        db.add(user)
        await db.flush()

        # 创建空白画像
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()

        token = create_access_token({"sub": str(user.id)})

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
            },
            "token": token,
        }

    async def login(self, db: AsyncSession, username: str, password: str) -> dict:
        """登录验证"""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("账号或密码错误")

        from app.core.security import verify_password
        if not verify_password(password, user.password_hash):
            raise ValueError("账号或密码错误")

        token = create_access_token({"sub": str(user.id)})

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
            },
            "token": token,
        }

    async def get_user_with_profile(self, db: AsyncSession, user_id: int) -> dict:
        """获取用户信息 + 画像"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("用户不存在")

        profile_data = None
        if user.profile:
            from app.services.profile_service import ProfileService
            profile_data = ProfileService.to_dict(user.profile)

        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "student_id": user.student_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "profile": profile_data,
        }
