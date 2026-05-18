# 智途校园 - 画像业务逻辑
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


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
