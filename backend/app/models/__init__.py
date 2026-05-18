# 智途校园 - 数据模型注册
from app.models.user import User, UserProfile
from app.models.plan import LearningPlan, DailyTask
from app.models.resume import Resume
from app.models.points import Point
from app.models.chat import ChatMessage

__all__ = [
    "User",
    "UserProfile",
    "LearningPlan",
    "DailyTask",
    "Resume",
    "Point",
    "ChatMessage",
]
