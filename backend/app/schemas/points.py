# 智途校园 - 积分相关Schema
from datetime import datetime
from pydantic import BaseModel


class PointRecord(BaseModel):
    amount: int
    reason: str
    source: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RankItem(BaseModel):
    rank: int
    name: str
    points: int
