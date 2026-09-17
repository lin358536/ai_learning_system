# 智途校园 — 环境变量配置
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """全局配置，从 .env 文件读取"""

    # 数据库
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "ai_learning_system"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 168

    # 扣子Coze
    COZE_PAT: str = ""
    COZE_BOT_ID: str = ""

    # 通义千问（备用，已迁移至Coze）
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen3.5-flash"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # DeepSeek（本地 LangChain Agent 默认 LLM）
    DEEPSEEK_API_KEY: str = ""                       # key 留空待用户填写，禁止硬编码
    DEEPSEEK_MODEL: str = "deepseek-flash"           # 模型名可配置，平台 ID 不同时改 .env 即可（默认须为平台合法 ID）
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # Agent 通道开关：langgraph（本地智能体） | coze（扣子远程智能体）
    AGENT_BACKEND: str = "langgraph"
    AGENT_MAX_ITER: int = 8                          # LangGraph 工具循环最大轮数（防死循环）
    PROMPT_HOT_RELOAD: bool = True                   # 技能 YAML prompt 热加载

    # LLM 采样参数
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # 邮件
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
