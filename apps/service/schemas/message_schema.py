"""消息相关 Pydantic 模型 —— 请求体与响应体定义。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ========== 响应模型 ==========

class MessageItem(BaseModel):
    """消息列表项"""
    id: int
    role: str
    content: str
    sources: dict | list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
