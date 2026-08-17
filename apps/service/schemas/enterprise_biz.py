"""企业业务 ORM 模型 —— 对应 enterprise_biz 表。"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.mysql import Base


class EnterpriseBiz(Base):
    __tablename__ = "enterprise_biz"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False)
    process: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="biz_status"),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "active")
        super().__init__(**kwargs)
