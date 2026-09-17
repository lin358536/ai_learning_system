# 智途校园 - 通用对话技能（新版插件体系，兜底）
from app.skills.skill_engine import SkillBase


class ChatSkill(SkillBase):
    """通用对话技能 —— 兜底路由，LLM tool calling 自主决策是否查询数据。"""

    key: str = "chat"
    prompt_skill: str = "chat"
    # 通用技能开放全部只读查询工具
    allowed_tools: list[str] = [
        "query_plans",
        "query_resumes",
        "query_profile",
        "query_points",
    ]
    # chat 技能承接所有未命中 plan/resume 的意图（兜底，由 SkillEngine.route 保证）
    intents: list[str] = [
        "chat",
        "query_plans",
        "query_resumes",
        "query_profile",
        "query_points",
    ]
