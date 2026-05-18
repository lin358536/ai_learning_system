# 智途校园 - 工具：生成简历
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.ai_service import AiService
from app.services.resume_service import ResumeService
from app.services.profile_service import ProfileService
from app.services.plan_service import PlanService
from app.skills.registry import skill_registry


class GenerateResumeTool(BaseTool):
    """AI生成简历"""

    @property
    def key(self) -> str:
        return "generate_resume"

    @property
    def name(self) -> str:
        return "生成简历"

    @property
    def description(self) -> str:
        return "写简历、制作简历、生成简历、帮我写简历"

    def should_confirm(self) -> bool:
        return True

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        """调用AI生成简历"""
        # 获取用户画像
        profile_service = ProfileService()
        profile = await profile_service.get_profile(db, user_id)

        # 获取规划作为素材
        plan_service = PlanService()
        plans = await plan_service.get_plans(db, user_id)

        profile_text = "用户画像未知"
        if profile:
            skills = json.loads(profile.skills) if isinstance(profile.skills, str) else (profile.skills or [])
            profile_text = (
                f"专业: {profile.major}\n"
                f"目标岗位: {profile.target_job}\n"
                f"技能: {', '.join(skills) if skills else '暂无'}\n"
                f"学历: {profile.education}\n"
                f"毕业年份: {profile.graduation_year or '未知'}"
            )

        plans_text = ""
        if plans:
            plan_lines = []
            for p in plans[:3]:
                plan_lines.append(f"- {p['title']}（进度 {p['progress']}%）")
            plans_text = "\n\n用户的学习规划:\n" + "\n".join(plan_lines)

        # 获取简历技能的system prompt
        skill = skill_registry.get("resume_skill")
        system_prompt = skill.system_prompt() if skill else "你是一位专业的简历工程师。"

        user_msg = f"{profile_text}{plans_text}\n\n请根据以上信息，为用户撰写一份专业的求职简历。"

        ai = AiService()
        resume_data = await ai.chat_json(
            system_prompt=system_prompt,
            history=[],
            user_message=user_msg,
        )

        if resume_data is None:
            return {"error": "AI生成失败，请重试"}

        return {
            "type": "confirm",
            "data": resume_data,
            "preview": {
                "title": resume_data.get("title", "我的简历"),
            },
        }

    async def confirm(self, db: AsyncSession, user_id: int, data: dict) -> dict:
        """用户确认后保存简历并发送邮件"""
        resume_service = ResumeService()
        resume = await resume_service.save_resume(
            db=db,
            user_id=user_id,
            title=data.get("title", "我的简历"),
            content=data,
        )

        # 加积分
        from app.services.points_service import PointsService
        points_service = PointsService()
        await points_service.add_points(
            db=db, user_id=user_id, amount=15,
            reason="生成简历", source="resume",
        )

        # 发送简历邮件
        email_sent = False
        try:
            from sqlalchemy import select
            from app.models.user import User
            from app.services.email_service import get_email_service

            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user and user.email:
                email_svc = get_email_service()
                email_sent = email_svc.send_resume(
                    to_email=user.email,
                    resume_data=data,
                    username=user.name or user.username,
                )
        except Exception as e:
            print(f"[generate_resume] 邮件发送异常: {e}")

        return {
            "message": f"简历「{resume.title}」已保存！{'已发送到您的邮箱。' if email_sent else ''}",
            "resume_id": resume.id,
            "email_sent": email_sent,
        }
