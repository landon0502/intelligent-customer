"""会话相关 Pydantic 模型 —— 请求体与响应体定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class ConversationCreate(BaseModel):
    """创建会话请求"""
    title: str | None = Field(default=None, max_length=100, description="会话标题，不传则默认'新对话'")


# ========== 响应模型 ==========

class ConversationItem(BaseModel):
    """会话列表项"""
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    """创建会话响应"""
    id: int
    title: str
    status: str

    model_config = {"from_attributes": True}
