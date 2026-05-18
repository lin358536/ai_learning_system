# 智途校园 - 工具：查询简历
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool
from app.services.resume_service import ResumeService


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
