# 智途校园 - MCP 工具装载（骨架）
"""
读 MCP Server 注册表 → 经 langchain-mcp-adapters 的 MultiServerMCPClient 转 BaseTool。

约定：
- 注册表为空（本期默认）→ 直接返回 []，零启动开销（<10ms）；
- langchain-mcp-adapters 的 MultiServerMCPClient API 在 0.1.x 与 0.4.x 间有差异
  （构造参数式 vs connect_to_server 方法式），此处做薄封装隔离版本差异；
- stdio 命令必须用 sys.executable（Windows 兼容）。
"""
import sys

from langchain_core.tools import BaseTool

from app.mcpserver.registry import MCP_SERVERS


async def load_mcp_tools() -> list[BaseTool]:
    """
    装载 MCP 工具。注册表为空时立即返回空列表，无任何网络/子进程开销。

    Returns:
        MCP server 暴露的工具列表；未安装桥接包或连接失败时返回 []
        （MCP 是可选能力，绝不阻塞主链路）。
    """
    if not MCP_SERVERS:
        return []

    print(f"[zhitu][mcp] 注册表非空，尝试装载 MCP 工具: {list(MCP_SERVERS.keys())}")

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as e:
        print(f"[zhitu][mcp] langchain-mcp-adapters 未安装或导入失败: {e}")
        return []

    # 组装客户端配置（stdio 命令统一替换为当前解释器，Windows 勿写死 python）
    client_config: dict[str, dict] = {}
    for name, cfg in MCP_SERVERS.items():
        transport = cfg.get("transport", "stdio")
        entry = dict(cfg)
        entry.pop("transport", None)
        if transport == "stdio" and "command" in entry and entry.get("use_current_python", True):
            entry["command"] = sys.executable
        client_config[name] = {"transport": transport, **entry}

    try:
        # 版本差异薄封装：0.1.x 支持构造参数式初始化
        if hasattr(MultiServerMCPClient, "connect_to_server"):
            async with MultiServerMCPClient() as client:
                for name, cfg in client_config.items():
                    await client.connect_to_server(name=name, **cfg)
                return list(client.get_tools())
        else:
            client = MultiServerMCPClient(client_config)
            return list(await client.get_tools())
    except Exception as e:
        print(f"[zhitu][mcp] MCP 工具装载失败（忽略，返回空列表）: {type(e).__name__}: {e}")
        return []
