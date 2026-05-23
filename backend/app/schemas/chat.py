# 智途校园 - 对话相关Schema
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="用户消息")
    conversation_id: str | None = Field(None, description="会话ID（UUID），首次对话不传则后端生成，后续必须携带以持续对话")


class ConfirmRequest(BaseModel):
    confirm_id: str = Field(..., description="待确认项ID")
    action: str = Field(..., description="操作: confirm/regenerate/cancel")


class ChatMessageItem(BaseModel):
    id: int
    role: str
    content: str
    intent: str | None = None
    conversation_id: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConversationItem(BaseModel):
    """会话列表项"""
    conversation_id: str
    title: str = ""  # 取会话第一条用户消息前30字
    last_message_at: datetime | None = None
    message_count: int = 0
    intent: str | None = None  # 最后一条助手消息的intent

    model_config = {"from_attributes": True}
