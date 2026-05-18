# 智途校园 - 技能基类
from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """技能基类 — 定义AI在不同场景下的行为策略"""

    @property
    @abstractmethod
    def key(self) -> str:
        """技能唯一标识"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        ...

    @abstractmethod
    def system_prompt(self) -> str:
        """该技能使用的系统提示词"""
        ...

    @property
    def description(self) -> str:
        """技能描述，用于意图识别"""
        return ""
