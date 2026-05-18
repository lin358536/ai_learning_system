# 智途校园 - 技能注册中心
from app.skills.base import BaseSkill


class SkillRegistry:
    """技能注册中心 — 管理所有AI技能"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.key] = skill

    def get(self, key: str) -> BaseSkill | None:
        return self._skills.get(key)

    def get_by_description_match(self, text: str) -> BaseSkill | None:
        """根据描述关键词匹配技能"""
        best_match = None
        best_score = 0
        for skill in self._skills.values():
            desc = skill.description.lower()
            score = sum(1 for kw in text.lower().split() if kw in desc)
            if score > best_score:
                best_score = score
                best_match = skill
        return best_match

    def all_skills(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def all_descriptions(self) -> str:
        """返回所有技能的描述文本，供意图识别使用"""
        lines = []
        for skill in self._skills.values():
            lines.append(f"- {skill.key}: {skill.name} — {skill.description}")
        return "\n".join(lines)


# 全局实例
skill_registry = SkillRegistry()
