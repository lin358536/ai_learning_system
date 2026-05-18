# 智途校园 - 认证相关Schema
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: str | None = Field(None, description="邮箱")
    name: str | None = Field(None, max_length=50, description="姓名")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserOut(BaseModel):
    id: int
    username: str
    name: str | None = None
    email: str | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    success: bool = True
    data: dict


class UserMeResponse(BaseModel):
    success: bool = True
    data: dict
