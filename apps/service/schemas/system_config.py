"""系统配置 ORM 模型 —— 对应 system_configs 表。"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.mysql import Base


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="配置键")
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general", comment="配置分类")
    description: Mapped[str] = mapped_column(String(255), nullable=True, comment="配置说明")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
