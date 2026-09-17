# 智途校园 - MCP 数据库工具 server 示例（默认不注册、不启用）
"""
可选的 FastMCP 数据库工具示例。

用法（手动启用）：
1. 在 app/mcpserver/registry.py 中取消 zhitu_db 注册项的注释；
2. 重启后端，load_mcp_tools() 会以 stdio 子进程方式拉起本模块（python -m app.mcpserver.db_mcp_server）。

注意：本模块作为独立子进程运行，与 FastAPI 主进程无共享状态。
"""
import sys

from app.core.database import AsyncSessionLocal
from app.services.points_service import PointsService
from app.services.plan_service import PlanService


def _build_mcp():
    """构建 FastMCP 实例（延迟导入，mcp 未安装时不影响主应用）。"""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("zhitu-db")

    @mcp.tool()
    async def query_points(user_id: int) -> str:
        """查询指定用户的积分总数与排名"""
        async with AsyncSessionLocal() as db:
            service = PointsService()
            data = await service.get_user_points(db, user_id)
        return f"总积分 {data['total']} 分，排名第 {data['rank']} 名（共 {data['total_users']} 人）"

    @mcp.tool()
    async def query_plans(user_id: int) -> str:
        """查询指定用户的学习规划列表摘要"""
        async with AsyncSessionLocal() as db:
            service = PlanService()
            plans = await service.get_plans(db, user_id)
        if not plans:
            return "该用户暂无学习规划"
        lines = [f"- 《{p['title']}》进度 {p['progress']}%" for p in plans]
        return "\n".join(lines)

    return mcp


if __name__ == "__main__":
    # 以 stdio transport 启动（由 MCP 客户端拉起，勿直接运行调试）
    _build_mcp().run(transport="stdio")
    sys.exit(0)
