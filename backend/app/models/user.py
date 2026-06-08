# 智途校园 - 用户模型
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    student_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, lazy="selectin")
    plans: Mapped[list["LearningPlan"]] = relationship(back_populates="user", lazy="selectin")
    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", lazy="selectin")
    points: Mapped[list["Point"]] = relationship(back_populates="user", lazy="selectin")

    @property
    def total_points(self) -> int:
        return sum(p.amount for p in self.points) if self.points else 0


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 基础信息
    education: Mapped[str] = mapped_column(String(10), nullable=True, default="专科")       # 专科/本科
    major: Mapped[str] = mapped_column(String(100), nullable=True, default="")             # 专业
    grade: Mapped[str] = mapped_column(String(5), nullable=True, default="")               # 大一/大二/大三/大四
    upgrade_intent: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)     # 是否有升学意愿

    # 职业方向
    target_industry: Mapped[str] = mapped_column(String(50), nullable=True, default="")    # 意向行业
    target_job: Mapped[str] = mapped_column(String(100), nullable=True, default="")        # 目标岗位
    job_style: Mapped[str] = mapped_column(String(20), nullable=True, default="")          # 稳定型/进取型/未确定

    # 能力画像（JSON数组存储）
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)                        # JSON: ["Python","SQL"]
    certificates: Mapped[str | None] = mapped_column(Text, nullable=True)                  # JSON: ["CET-4","计算机二级"]

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    user: Mapped["User"] = relationship(back_populates="profile")
