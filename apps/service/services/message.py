"""消息业务逻辑 —— 查询、创建消息。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.message import Message


async def get_messages_by_conversation(
    db: AsyncSession, conversation_id: int
) -> list[Message]:
    """获取会话的所有消息，按创建时间正序"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def create_message(
    db: AsyncSession,
    conversation_id: int,
    role: str,
    content: str,
    sources: dict | None = None,
) -> Message:
    """创建一条消息记录"""
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_recent_messages(
    db: AsyncSession, conversation_id: int, limit: int = 20
) -> list[Message]:
    """获取会话最近 N 条消息（用于注入 LLM 上下文），按时间正序"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    # 反转为正序
    return list(reversed(result.scalars().all()))
