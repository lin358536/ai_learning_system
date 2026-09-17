# 智途校园 - Agent 重构验证：技能路由与工具装配
"""覆盖 T02 验收：4 个路由用例 + get_tools 按 allowed_tools 装配。"""
import pytest

from app.agent.tools.toolkit import ToolContext
from app.skills.skill_engine import get_skill_engine


class TestRoute:
    @pytest.mark.parametrize(
        "intent,expected_key",
        [
            ("generate_plan", "plan"),
            ("generate_resume", "resume"),
            ("query_points", "chat"),
            ("query_plans", "chat"),
            ("query_resumes", "chat"),
            ("query_profile", "chat"),
            (None, "chat"),
            ("chat", "chat"),
            ("unknown_intent_xyz", "chat"),  # 未命中兜底
        ],
    )
    def test_route(self, intent, expected_key):
        engine = get_skill_engine()
        assert engine.route(intent).key == expected_key


class TestGetTools:
    def _ctx(self):
        # 工厂仅闭包绑定，不触碰 db，None 即可
        return ToolContext(db=None, user_id=1)

    def test_chat_skill_all_query_tools(self):
        engine = get_skill_engine()
        skill = engine.route(None)
        tools = engine.get_tools(skill, self._ctx())
        assert {t.name for t in tools} == {
            "query_plans",
            "query_resumes",
            "query_profile",
            "query_points",
        }

    def test_plan_skill_tools(self):
        engine = get_skill_engine()
        skill = engine.route("generate_plan")
        tools = engine.get_tools(skill, self._ctx())
        assert {t.name for t in tools} == {"query_profile", "query_plans"}

    def test_resume_skill_tools(self):
        engine = get_skill_engine()
        skill = engine.route("generate_resume")
        tools = engine.get_tools(skill, self._ctx())
        assert {t.name for t in tools} == {"query_profile", "query_resumes"}

    def test_tools_have_description_and_schema(self):
        """StructuredTool 需带描述与 args_schema（DeepSeek bind_tools 依赖）。"""
        engine = get_skill_engine()
        tools = engine.get_tools(engine.route(None), self._ctx())
        for t in tools:
            assert t.description, f"工具 {t.name} 缺少 description"
            assert t.args_schema is not None, f"工具 {t.name} 缺少 args_schema"

    def test_skill_get_prompt(self):
        engine = get_skill_engine()
        for skill in engine.all_skills():
            prompt = skill.get_prompt({"user_name": "QA"})
            assert isinstance(prompt, str) and len(prompt) > 100
