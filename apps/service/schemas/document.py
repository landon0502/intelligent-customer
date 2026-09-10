"""文档 ORM 模型 —— 对应 documents 表。"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from database.mysql import Base
from pydantic import BaseModel, ConfigDict, field_validator

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        SAEnum("processing", "ready", "failed", name="doc_status"),
        nullable=False,
        default="processing",
        server_default="processing",
    )
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    chunk_count: int
    status: str
    file_type: str
    uploaded_by: int
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)
    @field_validator("id", mode="before")
    @classmethod
    def id_to_str(cls, v):
        return str(v)