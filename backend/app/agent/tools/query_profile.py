# 智途校园 - 工具：查询个人画像
import json
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.profile_service import ProfileService

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool
    from app.agent.tools.toolkit import ToolContext


class QueryProfileTool(BaseTool):
    """查询用户个人画像"""

    @property
    def key(self) -> str:
        return "query_profile"

    @property
    def name(self) -> str:
        return "查询个人画像"

    @property
    def description(self) -> str:
        return "查看画像、我的信息、个人信息、我是什么专业"

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        profile_service = ProfileService()
        profile = await profile_service.get_profile(db, user_id)

        if profile is None:
            return {"summary": "还没有设置个人画像，请先完善你的信息（专业、目标岗位等）。"}

        skills = json.loads(profile.skills) if isinstance(profile.skills, str) else (profile.skills or [])

        return {
            "summary": (
                f"你的个人信息：\n"
                f"- 专业: {profile.major}\n"
                f"- 目标岗位: {profile.target_job}\n"
                f"- 技能: {', '.join(skills) if skills else '暂无'}\n"
                f"- 学历: {profile.education}\n"
                f"- 年级: {profile.grade or '未知'}\n"
                f"- 升学意向: {'有' if profile.upgrade_intent else '无'}"
            ),
        }


# ── LangChain StructuredTool 工厂（Agent 重构新增，旧类原样保留） ──

class QueryProfileArgs(BaseModel):
    """query_profile 入参（无参数，查询当前用户画像）"""


def make_tool(ctx: "ToolContext") -> "StructuredTool":
    """构造绑定 ToolContext 的 LangChain 工具（复用旧 QueryProfileTool 的业务逻辑与 summary 文案）。"""
    from langchain_core.tools import StructuredTool

    async def _arun() -> str:
        tool = QueryProfileTool()
        result = await tool.execute(ctx.db, ctx.user_id)
        return str(result.get("summary", ""))

    return StructuredTool(
        name="query_profile",
        description="查询当前用户的个人画像（专业、目标岗位、技能、学历等）。无需参数。",
        func=None,
        coroutine=_arun,
        args_schema=QueryProfileArgs,
    )
