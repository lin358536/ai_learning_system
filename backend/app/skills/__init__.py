# 智途校园 - 技能包初始化
from app.skills.plan_skill import PlanSkill
from app.skills.resume_skill import ResumeSkill
from app.skills.registry import skill_registry

# 注册所有技能
skill_registry.register(PlanSkill())
skill_registry.register(ResumeSkill())

__all__ = ["skill_registry", "PlanSkill", "ResumeSkill"]
