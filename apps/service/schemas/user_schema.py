"""用户管理相关 Pydantic 模型 —— 响应体定义。"""

from datetime import datetime

from pydantic import BaseModel


class UserItem(BaseModel):
    """用户列表/创建响应项（仅暴露 id/username/role/created_at，不含 password_hash）"""
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
