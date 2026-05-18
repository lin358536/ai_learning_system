# 智途校园 - 工具基类
from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


class BaseTool(ABC):
    """工具基类 — Agent可调用的能力单元"""

    @property
    @abstractmethod
    def key(self) -> str:
        """工具唯一标识"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，供意图识别"""
        ...

    @abstractmethod
    async def execute(self, db: AsyncSession, user_id: int, **kwargs) -> Any:
        """
        执行工具逻辑。

        Args:
            db: 数据库会话
            user_id: 当前用户ID

        Returns:
            工具执行结果（dict 或 None）
        """
        ...

    def should_confirm(self) -> bool:
        """该工具的结果是否需要用户确认后才存库"""
        return False

    async def confirm(self, db: AsyncSession, user_id: int, data: dict) -> dict:
        """
        用户确认后的回调。默认不做任何操作。

        Args:
            db: 数据库会话
            user_id: 当前用户ID
            data: confirm阶段暂存的数据

        Returns:
            确认结果消息
        """
        return {"message": "已确认"}
