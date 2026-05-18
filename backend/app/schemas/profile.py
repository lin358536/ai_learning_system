# 智途校园 - 画像相关Schema
from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    """用户画像输出"""
    id: int
    # 基础信息
    education: str = "专科"
    major: str = ""
    grade: str = ""
    upgrade_intent: bool = False
    # 职业方向
    target_industry: str = ""
    target_job: str = ""
    job_style: str = ""
    # 能力画像
    skills: list[str] | None = None
    certificates: list[str] | None = None

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """用户画像更新请求（所有字段可选）"""
    # 基础信息
    education: str | None = Field(None, description="学历: 专科/本科")
    major: str | None = Field(None, max_length=100, description="专业")
    grade: str | None = Field(None, description="年级: 大一/大二/大三/大四")
    upgrade_intent: bool | None = Field(None, description="是否有升学意愿(专升本/考研)")
    # 职业方向
    target_industry: str | None = Field(None, max_length=50, description="意向行业")
    target_job: str | None = Field(None, max_length=100, description="目标岗位")
    job_style: str | None = Field(None, description="求职倾向: 稳定型/进取型/未确定")
    # 能力画像
    skills: list[str] | None = Field(None, description="技能列表")
    certificates: list[str] | None = Field(None, description="证书列表")


class ProfileResponse(BaseModel):
    success: bool = True
    data: ProfileOut
