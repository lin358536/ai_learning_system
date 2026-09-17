# 智途校园 - 学习规划技能（新版插件体系）
from app.skills.skill_engine import SkillBase


class PlanSkill(SkillBase):
    """规划技能 —— 主模型在 plan system prompt 约束下直出 JSON 规划（与 Coze 行为一致）。"""

    key: str = "plan"
    prompt_skill: str = "plan"
    # 生成前可查画像与已有规划，辅助定制
    allowed_tools: list[str] = ["query_profile", "query_plans"]
    intents: list[str] = ["generate_plan"]
