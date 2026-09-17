# 智途校园 - 简历技能（新版插件体系）
from app.skills.skill_engine import SkillBase


class ResumeSkill(SkillBase):
    """简历技能 —— 主模型在 resume system prompt 约束下直出 JSON 简历。"""

    key: str = "resume"
    prompt_skill: str = "resume"
    # 生成前可查画像与已有简历，辅助定制
    allowed_tools: list[str] = ["query_profile", "query_resumes"]
    intents: list[str] = ["generate_resume"]
