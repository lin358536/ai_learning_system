# 智途校园 - 工具注册中心
from app.agent.tools.base import BaseTool


class ToolRegistry:
    """工具注册中心 — 管理Agent可调用的所有工具"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.key] = tool

    def get(self, key: str) -> BaseTool | None:
        return self._tools.get(key)

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_tool_descriptions(self) -> str:
        """返回所有工具描述，供意图识别使用"""
        lines = []
        for tool in self._tools.values():
            confirm_mark = " [需确认]" if tool.should_confirm() else ""
            lines.append(f"- {tool.key}: {tool.name} — {tool.description}{confirm_mark}")
        return "\n".join(lines)

    def get_by_description_match(self, message: str) -> "BaseTool | None":
        """模糊匹配工具描述，返回最匹配的工具"""
        message = message.lower()
        best_tool = None
        best_score = 0
        for tool in self._tools.values():
            desc_words = tool.description.lower().replace("、", " ").replace("，", " ").split()
            score = sum(1 for word in desc_words if word and word in message)
            if score > best_score:
                best_score = score
                best_tool = tool
        return best_tool if best_score > 0 else None


# 全局实例
tool_registry = ToolRegistry()
