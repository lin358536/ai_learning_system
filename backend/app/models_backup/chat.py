# 智途校园 - 对话历史模型
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirm_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirm_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON字符串
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
