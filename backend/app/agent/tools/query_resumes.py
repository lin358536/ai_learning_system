# 智途校园 - 工具：查询简历
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.resume_service import ResumeService

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool
    from app.agent.tools.toolkit import ToolContext


class QueryResumesTool(BaseTool):
    """查询用户的简历列表"""

    @property
    def key(self) -> str:
        return "query_resumes"

    @property
    def name(self) -> str:
        return "查询简历"

    @property
    def description(self) -> str:
        return "查看简历、我的简历、简历列表"

    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> dict:
        resume_service = ResumeService()
        resumes = await resume_service.get_resumes(db, user_id)

        if not resumes:
            return {"summary": "你还没有简历，告诉我你的目标岗位，我可以帮你生成一份。"}

        lines = []
        for r in resumes:
            lines.append(f"- 《{r['title']}》（创建于 {r['created_at'][:10] if r['created_at'] else '未知'}）")

        return {
            "summary": f"你有 {len(resumes)} 份简历：\n" + "\n".join(lines),
            "resumes": resumes,
        }


# ── LangChain StructuredTool 工厂（Agent 重构新增，旧类原样保留） ──

class QueryResumesArgs(BaseModel):
    """query_resumes 入参（无参数，查询当前用户全部简历）"""


def make_tool(ctx: "ToolContext") -> "StructuredTool":
    """构造绑定 ToolContext 的 LangChain 工具（复用旧 QueryResumesTool 的业务逻辑与 summary 文案）。"""
    from langchain_core.tools import StructuredTool

    async def _arun() -> str:
        tool = QueryResumesTool()
        result = await tool.execute(ctx.db, ctx.user_id)
        return str(result.get("summary", ""))

    return StructuredTool(
        name="query_resumes",
        description="查询当前用户的简历列表。无需参数。",
        func=None,
        coroutine=_arun,
        args_schema=QueryResumesArgs,
    )
