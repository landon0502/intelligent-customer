"""对话相关 Pydantic 模型 —— 请求体定义。"""

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """发送消息请求（AI SDK UIMessage 格式）"""
    conversation_id: int = Field(..., description="会话ID")
    messages: list[dict] = Field(default_factory=list, description="AI SDK UIMessage[]")
    id: str | None = Field(None, description="AI SDK chat ID")
    trigger: str | None = Field(None, description="submit-message | regenerate-message")
