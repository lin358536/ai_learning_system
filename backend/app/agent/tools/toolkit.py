# 智途校园 - LangChain 工具层（ToolContext + 工厂注册表）
"""
新的 LangChain 工具装配层，与旧 agent/tools/base.py + registry.py 并存：
- 旧体系（BaseTool/ToolRegistry）服务于 Coze 回退路径，零改动；
- 新体系：ToolContext 携带请求级依赖（db/user_id），经工厂闭包绑定到
  StructuredTool，绝不进入 AgentState（保证 state 可序列化）。
"""
from dataclasses import dataclass
from typing import Callable

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

# 各工具的 make_tool(ctx) 工厂（旧工具文件末尾追加，复用旧类 execute() 业务逻辑）
from app.agent.tools.query_plans import make_tool as _make_query_plans
from app.agent.tools.query_resumes import make_tool as _make_query_resumes
from app.agent.tools.query_profile import make_tool as _make_query_profile
from app.agent.tools.query_points import make_tool as _make_query_points


@dataclass
class ToolContext:
    """请求级依赖容器 —— db 与 user_id 一律经此在图工厂闭包中注入，不进 AgentState。"""

    db: AsyncSession
    user_id: int


def make_query_plans_tool(ctx: ToolContext) -> BaseTool:
    """构造 query_plans 工具（绑定 ToolContext）。"""
    return _make_query_plans(ctx)


def make_query_resumes_tool(ctx: ToolContext) -> BaseTool:
    """构造 query_resumes 工具（绑定 ToolContext）。"""
    return _make_query_resumes(ctx)


def make_query_profile_tool(ctx: ToolContext) -> BaseTool:
    """构造 query_profile 工具（绑定 ToolContext）。"""
    return _make_query_profile(ctx)


def make_query_points_tool(ctx: ToolContext) -> BaseTool:
    """构造 query_points 工具（绑定 ToolContext）。"""
    return _make_query_points(ctx)


# 新工具注册表：工具名 → 工厂函数（SkillEngine.get_tools 按名取用）
TOOL_FACTORIES: dict[str, Callable[[ToolContext], BaseTool]] = {
    "query_plans": make_query_plans_tool,
    "query_resumes": make_query_resumes_tool,
    "query_profile": make_query_profile_tool,
    "query_points": make_query_points_tool,
}
