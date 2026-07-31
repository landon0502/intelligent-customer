"""SQLAlchemy ORM 模型 —— 定义数据库表结构。

所有模型统一导入，确保 Base.metadata.create_all 能创建全部表。
"""

from schemas.user import User  # noqa: F401
from schemas.conversation import Conversation  # noqa: F401
from schemas.message import Message  # noqa: F401
from schemas.document import Document  # noqa: F401
from schemas.system_config import SystemConfig  # noqa: F401
