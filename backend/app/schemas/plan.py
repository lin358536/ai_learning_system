# 智途校园 - 学习规划相关Schema
from datetime import date, datetime
from pydantic import BaseModel


class PlanItem(BaseModel):
    id: int
    title: str
    status: str = "draft"
    progress: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskItem(BaseModel):
    id: int
    content: str
    status: str = "pending"
    task_date: date | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PlanDetailItem(BaseModel):
    id: int
    title: str
    content: dict | list = {}
    status: str = "draft"
    tasks: list[TaskItem] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
