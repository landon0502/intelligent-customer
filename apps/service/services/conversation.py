"""会话业务逻辑 —— 创建、查询、删除会话。"""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.conversation import Conversation
from schemas.message import Message


async def create_conversation(
    db: AsyncSession, user_id: int, title: str | None = None
) -> Conversation:
    """创建新会话，默认标题为'新对话'"""
    conv = Conversation(
        user_id=user_id,
        title=title or "新对话",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversations_by_user(
    db: AsyncSession, user_id: int
) -> list[Conversation]:
    """获取用户的所有会话，按更新时间倒序"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation_by_id(
    db: AsyncSession, conversation_id: int, user_id: int
) -> Conversation | None:
    """获取指定会话（需属于当前用户）"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_conversation(
    db: AsyncSession, conversation_id: int, user_id: int
) -> bool:
    """删除会话及其所有消息，返回是否成功"""
    conv = await get_conversation_by_id(db, conversation_id, user_id)
    if not conv:
        return False
    await db.execute(
        delete(Message).where(Message.conversation_id == conversation_id)
    )
    await db.delete(conv)
    await db.commit()
    return True
