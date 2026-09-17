# 智途校园 - Agent 重构验证：import 链完整性
"""覆盖任务书 T01/T03 验收：新旧两条链路 import 均无断裂。"""
import time


def test_llm_package_exports():
    from app.llm import get_llm, get_llm_with_tools, get_prompt_manager, get_harness

    assert callable(get_llm)
    assert callable(get_llm_with_tools)
    assert callable(get_prompt_manager)
    assert callable(get_harness)


def test_get_llm_empty_key_raises_zhitu_error(empty_key_env):
    """T01 验收：key 为空时 get_llm() 抛出带 [zhitu] 前缀的明确异常。

    前置条件由 empty_key_env 夹具显式注入空 key，不依赖真实 .env。
    """
    from app.core.config import get_settings
    from app.llm import get_llm

    assert get_settings().DEEPSEEK_API_KEY == "", "前置条件：DEEPSEEK_API_KEY 应为空"
    try:
        get_llm()
        raise AssertionError("空 key 下 get_llm() 未抛异常")
    except RuntimeError as e:
        assert "[zhitu]" in str(e)
        assert "DEEPSEEK_API_KEY" in str(e)


def test_agent_graph_import():
    from app.agent.graph import build_agent_graph

    assert callable(build_agent_graph)


def test_skill_engine_import():
    from app.skills.skill_engine import get_skill_engine

    assert callable(get_skill_engine)


def test_old_tool_chain_intact():
    """旧链 tool_registry 必须仍是完整 6 工具（Coze 回退路径）。"""
    import app.agent  # noqa: F401 触发旧工具注册
    from app.agent.tools.registry import tool_registry

    keys = {t.key for t in tool_registry.all_tools()}
    assert keys == {
        "generate_plan",
        "generate_resume",
        "query_plans",
        "query_resumes",
        "query_profile",
        "query_points",
    }, f"旧工具注册表不完整: {keys}"


def test_old_generate_tools_import():
    """T03 验收：旧 generate 工具 import 无报错（回退路径完好）。"""
    import app.agent.tools.generate_plan  # noqa: F401
    import app.agent.tools.generate_resume  # noqa: F401


def test_old_skills_package_intact():
    """旧 skills 包（plan_skill/resume_skill/skill_registry）不受影响。"""
    import app.skills  # noqa: F401
    from app.skills.registry import skill_registry

    keys = {s.key for s in skill_registry.all_skills()}
    assert {"plan_skill", "resume_skill"} <= keys, f"旧技能注册表异常: {keys}"


def test_new_toolkit_registry():
    from app.agent.tools.toolkit import TOOL_FACTORIES, ToolContext

    assert set(TOOL_FACTORIES.keys()) == {
        "query_plans",
        "query_resumes",
        "query_profile",
        "query_points",
    }
    ctx = ToolContext(db=None, user_id=1)
    assert ctx.user_id == 1


async def test_mcp_skeleton_empty_registry():
    """T03 验收：MCP 注册表为空时 load_mcp_tools() 返回 [] 且 <10ms。"""
    from app.agent.tools.mcp_tools import load_mcp_tools
    from app.mcpserver.registry import MCP_SERVERS

    assert MCP_SERVERS == {}, "本期 MCP 注册表应为空"
    t0 = time.monotonic()
    tools = await load_mcp_tools()
    elapsed_ms = (time.monotonic() - t0) * 1000
    assert tools == []
    assert elapsed_ms < 10, f"空注册表装载耗时 {elapsed_ms:.1f}ms，应 <10ms"
