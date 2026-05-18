# 智途校园 - 简历业务逻辑
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume


class ResumeService:
    """简历服务 — 查询、删除"""

    async def get_resumes(self, db: AsyncSession, user_id: int) -> list[dict]:
        """获取用户简历列表"""
        result = await db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
        )
        resumes = result.scalars().all()

        return [
            {
                "id": r.id,
                "title": r.title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resumes
        ]

    async def get_resume_detail(self, db: AsyncSession, resume_id: int,
                                user_id: int) -> dict | None:
        """获取简历详情"""
        result = await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == user_id,
            )
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            return None

        content = {}
        if resume.content:
            try:
                content = json.loads(resume.content) if isinstance(resume.content, str) else resume.content
            except (json.JSONDecodeError, TypeError):
                content = {}

        return {
            "id": resume.id,
            "title": resume.title,
            "content": content,
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
        }

    async def delete_resume(self, db: AsyncSession, resume_id: int,
                            user_id: int) -> bool:
        """删除简历"""
        result = await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == user_id,
            )
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            return False

        await db.delete(resume)
        await db.flush()
        return True

    async def save_resume(self, db: AsyncSession, user_id: int,
                          title: str, content: dict) -> Resume:
        """保存AI生成的简历"""
        resume = Resume(
            user_id=user_id,
            title=title,
            content=json.dumps(content, ensure_ascii=False),
        )
        db.add(resume)
        await db.flush()
        return resume
