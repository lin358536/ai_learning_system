# 智途校园 - 简历路由
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.resume_service import ResumeService
from app.services.email_service import get_email_service
from app.models.user import User
from app.models.resume import Resume

router = APIRouter(prefix="/resumes", tags=["简历"])


class ResumeSaveRequest(BaseModel):
    """保存简历请求"""
    title: str = Field("我的简历", max_length=200, description="简历标题")
    content: str = Field(..., min_length=10, description="简历内容（Markdown文本，来自云虾AI生成）")
    send_email: bool = Field(False, description="是否发送到用户邮箱")


@router.post("/save")
async def save_resume(
    req: ResumeSaveRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    保存AI生成的简历（Markdown文本）。
    可选发送到用户邮箱。
    """
    user_id = user["user_id"]
    service = ResumeService()

    # 保存到数据库
    import json
    resume = Resume(
        user_id=user_id,
        title=req.title,
        content=json.dumps({"markdown": req.content}, ensure_ascii=False),
    )
    db.add(resume)
    await db.flush()
    resume_id = resume.id
    resume_title = resume.title
    await db.commit()

    result = {
        "id": resume_id,
        "title": resume_title,
    }

    # 是否发送邮件
    email_sent = False
    if req.send_email:
        # 查用户邮箱
        user_result = await db.execute(select(User).where(User.id == user_id))
        user_obj = user_result.scalar_one_or_none()
        if user_obj and user_obj.email:
            email_svc = get_email_service()
            email_sent = email_svc.send_resume_text(
                to_email=user_obj.email,
                resume_markdown=req.content,
                username=user_obj.name or "同学",
                resume_title=req.title,
            )
        else:
            email_sent = False

    return {
        "success": True,
        "data": {
            **result,
            "email_sent": email_sent,
            "message": "简历已保存" + ("并发送到邮箱" if email_sent else ""),
        },
    }


@router.get("")
async def get_resumes(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ResumeService()
    resumes = await service.get_resumes(db, user["user_id"])
    return {"success": True, "data": {"resumes": resumes}}


@router.get("/{resume_id}")
async def get_resume_detail(
    resume_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ResumeService()
    resume = await service.get_resume_detail(db, resume_id, user["user_id"])
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "简历不存在"}},
        )
    return {"success": True, "data": resume}


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ResumeService()
    ok = await service.delete_resume(db, resume_id, user["user_id"])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "简历不存在"}},
        )
    return {"success": True, "data": {"message": "简历已删除"}}
