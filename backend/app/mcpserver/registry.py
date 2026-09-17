# 智途校园 - MCP Server 注册表（骨架，本期默认不启用）
"""
MCP Server 注册表 —— 声明式配置外部 MCP server，供 mcp_tools.load_mcp_tools() 装载。

本期只交付骨架：默认注册表为空 dict，未注册任何 server 时 load_mcp_tools()
直接返回空工具列表，零启动开销。需要启用时在 MCP_SERVERS 中追加配置即可，
无需改 graph / toolkit 代码（见任务文档共享约定第 11 条）。

配置项：
- transport: "stdio"（本地子进程）或 "streamable_http"（远程 HTTP）
- stdio 形式：command + args（command 必须用 sys.executable，Windows 下勿写死 python）
- streamable_http 形式：url
"""
import sys

# ── MCP Server 注册表（默认空 —— 本期不启用任何 MCP server） ──────
MCP_SERVERS: dict[str, dict] = {}

# ── 启用示例（取消注释即可挂载数据库 MCP server 示例） ────────────
# MCP_SERVERS = {
#     "zhitu_db": {
#         "transport": "stdio",
#         "command": sys.executable,          # Windows 兼容：用当前解释器启动子进程
#         "args": ["-m", "app.mcpserver.db_mcp_server"],
#     },
# }

# ── streamable_http 形式示例 ─────────────────────────────────────
# MCP_SERVERS = {
#     "remote_tools": {
#         "transport": "streamable_http",
#         "url": "http://127.0.0.1:9000/mcp",
#     },
# }

_ = sys  # 保留 sys 引用，便于上方示例取消注释后直接使用
