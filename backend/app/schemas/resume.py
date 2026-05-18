# 智途校园 - 简历相关Schema
from datetime import datetime
from pydantic import BaseModel


class ResumeItem(BaseModel):
    id: int
    title: str = "我的简历"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResumeDetailItem(BaseModel):
    id: int
    title: str = "我的简历"
    content: dict | list = {}
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
