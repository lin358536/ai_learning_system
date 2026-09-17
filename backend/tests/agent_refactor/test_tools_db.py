# 智途校园 - Agent 重构验证：工具层（真实 DB，绕过 LLM）
"""覆盖 T03 验收：AsyncSessionLocal 直调 4 个 query 工具，返回结构化 summary。

使用本机真实 MySQL（只读查询），测试用户 user_id=3（points/plans/resumes/profile 均有数据）。
"""
import pytest

from app.agent.tools.toolkit import (
    ToolContext,
    make_query_plans_tool,
    make_query_points_tool,
    make_query_profile_tool,
    make_query_resumes_tool,
)
from app.core.database import AsyncSessionLocal, engine

from conftest import TEST_USER_ID


@pytest.fixture()
async def ctx():
    async with AsyncSessionLocal() as db:
        yield ToolContext(db=db, user_id=TEST_USER_ID)


async def test_query_points_summary(ctx):
    tool = make_query_points_tool(ctx)
    result = await tool.ainvoke({})
    assert isinstance(result, str)
    assert "总积分" in result, f"query_points summary 异常: {result}"
    assert "排名" in result


async def test_query_plans_summary(ctx):
    tool = make_query_plans_tool(ctx)
    result = await tool.ainvoke({})
    assert isinstance(result, str)
    assert "学习规划" in result, f"query_plans summary 异常: {result}"


async def test_query_resumes_summary(ctx):
    tool = make_query_resumes_tool(ctx)
    result = await tool.ainvoke({})
    assert isinstance(result, str)
    assert "简历" in result, f"query_resumes summary 异常: {result}"


async def test_query_profile_summary(ctx):
    tool = make_query_profile_tool(ctx)
    result = await tool.ainvoke({})
    assert isinstance(result, str)
    assert "专业" in result, f"query_profile summary 异常: {result}"


async def test_query_plans_nonexistent_user(ctx):
    """边界：无数据用户应得到友好文案而非异常。"""
    empty_ctx = ToolContext(db=ctx.db, user_id=999999)
    tool = make_query_plans_tool(empty_ctx)
    result = await tool.ainvoke({})
    assert "还没有学习规划" in result


async def test_query_profile_nonexistent_user(ctx):
    empty_ctx = ToolContext(db=ctx.db, user_id=999999)
    tool = make_query_profile_tool(empty_ctx)
    result = await tool.ainvoke({})
    assert "还没有设置个人画像" in result


@pytest.fixture(scope="module", autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()
