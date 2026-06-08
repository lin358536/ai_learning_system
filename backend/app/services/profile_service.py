# 智途校园 - 画像业务逻辑
import json
import os
import uuid

import aiofiles
import imghdr
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

UPLOAD_DIR: str | None = None


def _get_upload_dir() -> str:
    global UPLOAD_DIR
    if UPLOAD_DIR is None:
        UPLOAD_DIR = os.path.join(
            os.path.dirname(__file__), "..", "..", "static", "avatars"
        )
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


class ProfileService:
    """画像服务 — 读取和更新用户画像"""

    async def get_profile(self, db: AsyncSession, user_id: int) -> UserProfile | None:
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def update_profile(self, db: AsyncSession, user_id: int, data: dict) -> dict:
        profile = await self.get_profile(db, user_id)
        if profile is None:
            raise ValueError("用户画像不存在")

        # 简单字符串字段直接更新
        update_fields = [
            "education", "major", "grade",
            "target_industry", "target_job", "job_style",
        ]
        for field in update_fields:
            if field in data and data[field] is not None:
                setattr(profile, field, data[field])

        # 布尔字段
        if "upgrade_intent" in data and data["upgrade_intent"] is not None:
            profile.upgrade_intent = data["upgrade_intent"]

        # JSON 数组字段：list → JSON 字符串
        for json_field in ("skills", "certificates"):
            if json_field in data and data[json_field] is not None:
                setattr(profile, json_field, json.dumps(data[json_field], ensure_ascii=False))

        await db.flush()

        return self._to_dict(profile)

    @staticmethod
    def _parse_json_field(value: str | None) -> list[str] | None:
        """安全解析 JSON 字段"""
        if not value:
            return None
        try:
            result = json.loads(value) if isinstance(value, str) else value
            return result if isinstance(result, list) else None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    async def upload_avatar(file: UploadFile, user_id: int, db: AsyncSession) -> dict:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": {"code": "INVALID_FORMAT", "message": "仅支持 JPG/PNG/GIF/WebP 格式"}},
            )

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": {"code": "FILE_TOO_LARGE", "message": "文件大小不能超过 2MB"}},
            )

        img_type = imghdr.what(None, h=content)
        allowed_types = {"jpeg", "png", "gif", "webp"}
        if img_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": {"code": "INVALID_CONTENT", "message": "文件内容不是有效的图片格式"}},
            )

        result = await db.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "error": {"code": "USER_NOT_FOUND", "message": "用户不存在"}},
            )

        upload_dir = _get_upload_dir()

        if db_user.avatar_url:
            old_path = os.path.join(upload_dir, os.path.basename(db_user.avatar_url))
            if os.path.exists(old_path):
                os.remove(old_path)

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)
        try:
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(content)
        except OSError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"success": False, "error": {"code": "FILE_WRITE_FAILED", "message": "文件写入失败，请稍后重试"}},
            )

        url = f"/static/avatars/{filename}"
        db_user.avatar_url = url
        await db.flush()

        return {"avatar_url": url}

    @classmethod
    def to_dict(cls, profile: UserProfile) -> dict:
        """将 UserProfile 转为字典（供外部调用）"""
        return cls._to_dict(profile)

    @classmethod
    def _to_dict(cls, profile: UserProfile) -> dict:
        return {
            "id": profile.id,
            "education": profile.education or "专科",
            "major": profile.major or "",
            "grade": profile.grade or "",
            "upgrade_intent": bool(profile.upgrade_intent),
            "target_industry": profile.target_industry or "",
            "target_job": profile.target_job or "",
            "job_style": profile.job_style or "",
            "skills": cls._parse_json_field(profile.skills),
            "certificates": cls._parse_json_field(profile.certificates),
        }
