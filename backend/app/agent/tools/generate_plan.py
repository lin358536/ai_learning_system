# 智途校园 - 工具：生成学习规划
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.ai_service import AiService
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from app.skills.registry import skill_registry


class GeneratePlanTool(BaseTool):
    """AI生成学习规划"""

    @property
    def key(self) -> str:
        return "generate_plan"

    @property
    def name(self) -> str:
        return "生成学习规划"

    @property
    def description(self) -> str:
        return "制定学习规划、学习计划、学习路径"

    def should_confirm(self) -> bool:
        return True

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        """调用AI生成规划，返回规划数据和confirm_id"""
        # 获取用户画像作为上下文
        profile_service = ProfileService()
        profile = await profile_service.get_profile(db, user_id)

        # 获取已有规划列表避免重复
        plan_service = PlanService()
        existing_plans = await plan_service.get_plans(db, user_id)

        profile_text = "用户画像未知"
        if profile:
            skills = json.loads(profile.skills) if isinstance(profile.skills, str) else (profile.skills or [])
            profile_text = (
                f"专业: {profile.major}\n"
                f"目标岗位: {profile.target_job}\n"
                f"技能: {', '.join(skills) if skills else '暂无'}\n"
                f"学历: {profile.education}\n"
                f"毕业年份: {profile.graduation_year or '未知'}\n"
                f"升学意向: {'有' if profile.upgrade_intent else '无'}"
            )

        existing_text = ""
        if existing_plans:
            titles = [f"- {p['title']}({p['status']})" for p in existing_plans[:3]]
            existing_text = f"\n\n用户已有规划:\n" + "\n".join(titles)

        # 获取规划技能的system prompt
        skill = skill_registry.get("plan_skill")
        system_prompt = skill.system_prompt() if skill else "你是一位专业的学习规划师。"

        user_msg = f"{profile_text}{existing_text}\n\n请根据以上信息，为用户制定一份新的个性化学习规划。"

        ai = AiService()
        plan_data = await ai.chat_json(
            system_prompt=system_prompt,
            history=[],
            user_message=user_msg,
        )

        if plan_data is None:
            return {"error": "AI生成失败，请重试"}

        return {
            "type": "confirm",
            "data": plan_data,
            "preview": {
                "title": plan_data.get("title", "学习规划"),
                "stages": [s.get("name", "") for s in plan_data.get("stages", [])],
            },
        }

    async def confirm(self, db: AsyncSession, user_id: int, data: dict) -> dict:
        """用户确认后保存规划并生成每日任务"""
        plan_service = PlanService()
        plan = await plan_service.save_plan(
            db=db,
            user_id=user_id,
            title=data.get("title", "学习规划"),
            content=data,
        )

        # 加积分
        from app.services.points_service import PointsService
        points_service = PointsService()
        await points_service.add_points(
            db=db, user_id=user_id, amount=20,
            reason="创建学习规划", source="plan",
        )

        # 统计生成的任务数
        task_count = len(data.get("daily_tasks", []))

        return {
            "message": f"规划已保存！已为你创建了 {task_count} 个每日任务。",
            "plan_id": plan.id,
        }
