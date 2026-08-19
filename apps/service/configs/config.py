"""
全局配置模块 —— 统一管理所有环境变量和应用常量。
通过环境变量注入，支持开发/生产环境切换。
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class Settings:
    # ========== 应用基础 ==========
    APP_NAME: str = "intelligent-customer"
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

    # ========== 日志 ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ========== 并发控制 ==========
    # 同时进行的 SSE 对话流上限：限制涌入量避免本地 MPS 推理/DB 连接过载
    CHAT_CONCURRENCY: int = int(os.getenv("CHAT_CONCURRENCY", "15"))

    # ========== JWT ==========
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

    # ========== Chroma ==========
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "knowledge_base")

    # ========== RAG ==========
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
    RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "512"))
    RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "64"))
    RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.3"))

    # ========== Admin ==========
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")


# 全局单例
settings = Settings()


def validate_security_defaults() -> None:
    """校验安全默认值：弱 JWT_SECRET / ADMIN_PASSWORD 命中时仅告警，不阻塞启动。"""
    logger = logging.getLogger("intelligent-customer.security")
    if settings.JWT_SECRET == "change-me-in-production":
        logger.warning(
            "安全告警: JWT_SECRET 仍为默认弱值 change-me-in-production，"
            "请在 .env 中配置强随机密钥"
        )
    if settings.ADMIN_PASSWORD == "admin123456":
        logger.warning(
            "安全告警: ADMIN_PASSWORD 仍为默认弱值 admin123456，请在 .env 中配置强密码"
        )
