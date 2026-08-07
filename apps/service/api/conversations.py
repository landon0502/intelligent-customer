"""会话管理接口 —— 创建、列表、消息查询、删除。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.conversation_schema import ConversationCreate, ConversationItem, ConversationDetail
from schemas.message_schema import MessageItem
from auth.security import get_current_user
from services.conversation import (
    create_conversation,
    get_conversations_by_user,
    get_conversation_by_id,
    delete_conversation,
)
from services.message import get_messages_by_conversation
from utils.response import success, error

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的会话列表"""
    convs = await get_conversations_by_user(db, current_user.id)
    items = [ConversationItem.model_validate(c) for c in convs]
    return success(data=items)


@router.post("")
async def create_new_conversation(
    req: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    conv = await create_conversation(db, current_user.id, req.title)
    return success(data=ConversationDetail.model_validate(conv))


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的消息列表"""
    conv = await get_conversation_by_id(db, conversation_id, current_user.id)
    if not conv:
        return error(code=40001, message="会话不存在")
    messages = await get_messages_by_conversation(db, conversation_id)
    items = [MessageItem.model_validate(m) for m in messages]
    return success(data=items)


@router.delete("/{conversation_id}")
async def delete_conversation_by_id(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话及其消息"""
    deleted = await delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        return error(code=40001, message="会话不存在")
    return success(data={"success": True})
