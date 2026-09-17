# 智途校园 - 技能引擎（新版插件体系，与旧 skills/registry.py 并存）
"""新 SkillBase 插件基类 + SkillEngine（intent → skill 路由 + 工具装配）。"""
from abc import ABC

from langchain_core.tools import BaseTool, StructuredTool


class SkillBase(ABC):
    """
    新技能插件基类。

    与旧 app/skills/base.py 的 BaseSkill 并存（旧体系服务于 Coze 回退路径，不动）。

    子类以类属性声明：
    - key: 技能唯一标识（plan / resume / chat）
    - prompt_skill: PromptManager 中的 prompt key（即技能目录名）
    - allowed_tools: 允许该技能使用的 LangChain 工具名列表（对应 toolkit.TOOL_FACTORIES）
    - intents: 该技能承接的意图列表（用于 SkillEngine.route 反查）
    """

    key: str = "chat"
    prompt_skill: str = "chat"
    allowed_tools: list[str] = []
    intents: list[str] = []

    def get_prompt(self, context: dict | None = None) -> str:
        """经 PromptManager 渲染该技能的 system prompt（画像变量注入模板）。"""
        # 延迟 import，避免 app.llm 与 app.skills 之间潜在循环
        from app.llm.prompt_manager import get_prompt_manager

        return get_prompt_manager().render(self.prompt_skill, context or {})


class SkillEngine:
    """
    技能引擎 —— intent 路由 + 工具装配。

    路由规则（见任务文档 1.7）：
    - 命中 generate_plan / generate_resume → 对应 plan / resume 技能
    - 其余（query_* / None / chat）→ chat 技能（LLM tool calling 自主决策）
    """

    def __init__(self):
        self._skills: dict[str, SkillBase] = {}
        # 延迟 import：技能子类定义在 app/skills/<name>/ 下，与旧 skills 包同目录
        from app.skills.plan import PlanSkill
        from app.skills.resume import ResumeSkill
        from app.skills.chat import ChatSkill

        self.register(PlanSkill())
        self.register(ResumeSkill())
        self.register(ChatSkill())

    def register(self, skill: SkillBase) -> None:
        """注册技能（扩展点：新技能只需新建 skills/<name>/ 目录并在此注册）。"""
        self._skills[skill.key] = skill

    def route(self, intent: str | None) -> SkillBase:
        """
        意图 → 技能路由。未命中任何技能意图时兜底返回 chat 技能。
        """
        if intent:
            for skill in self._skills.values():
                if intent in skill.intents:
                    return skill
        return self._skills["chat"]

    def get_tools(self, skill: SkillBase, ctx) -> list[BaseTool]:
        """
        按 skill.allowed_tools 从 toolkit 工厂注册表装配 StructuredTool。

        Args:
            skill: 目标技能
            ctx: ToolContext(db, user_id) —— 工厂闭包绑定的请求级依赖
        """
        # 延迟 import，避免 skill_engine ↔ toolkit 循环依赖
        from app.agent.tools.toolkit import TOOL_FACTORIES

        tools: list[BaseTool] = []
        for name in skill.allowed_tools:
            factory = TOOL_FACTORIES.get(name)
            if factory is None:
                print(f"[zhitu][skill_engine] 技能 {skill.key} 引用了未注册工具: {name}，已跳过")
                continue
            tool = factory(ctx)
            if isinstance(tool, StructuredTool | BaseTool):
                tools.append(tool)
        return tools

    def all_skills(self) -> list[SkillBase]:
        """全部已注册技能（观测用）。"""
        return list(self._skills.values())


# 模块级懒加载单例
_skill_engine: SkillEngine | None = None


def get_skill_engine() -> SkillEngine:
    """获取 SkillEngine 懒加载单例。"""
    global _skill_engine
    if _skill_engine is None:
        _skill_engine = SkillEngine()
    return _skill_engine
