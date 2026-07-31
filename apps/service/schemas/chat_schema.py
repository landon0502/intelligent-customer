"""对话相关 Pydantic 模型 —— 请求体定义。"""

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """发送消息请求"""
    conversation_id: int = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, description="消息内容")
