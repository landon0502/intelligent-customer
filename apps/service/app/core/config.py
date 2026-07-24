"""
全局配置模块 —— 统一管理所有环境变量和应用常量。
通过环境变量注入，支持开发/生产环境切换。
"""

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class Settings:
    # ========== 应用基础 ==========
    APP_NAME: str = "ai-service"
    APP_HOST: str = os.getenv("APP_HOST")
    APP_PORT: int = int(os.getenv("APP_PORT"))
    DEBUG: bool = os.getenv("DEBUG").lower() == "true"

    # ========== CORS ==========
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(
        ","
    )

    # ========== MySQL（SQLAlchemy async） ==========
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "00000000")
    DB_NAME: str = os.getenv("DB_NAME", "ling_diary")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    # ========== Redis ==========
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD") or None
    REDIS_POOL_MAX: int = int(os.getenv("REDIS_POOL_MAX", "20"))

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ========== 大模型 ==========
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    ZAI_API_KEY: str = os.getenv("ZAI_API_KEY", "")
    ZAI_BASE_URL: str = os.getenv(
        "ZAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"
    )

    # ========== 日志 ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# 全局单例
settings = Settings()
