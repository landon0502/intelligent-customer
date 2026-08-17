"""工单接口 —— 创建（登录）、列表/详情/状态更新（admin）。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.ticket import ServiceTicket
from auth.security import get_current_user
from services.ticket import (
    TICKET_STATUS_PROCESSING,
    TICKET_STATUS_CLOSED,
    create_ticket,
    list_tickets,
    get_ticket_by_no,
    update_status,
)
from utils.response import success, error

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# PATCH 状态更新仅允许 processing/closed，open 仅作初始状态不可回退
_PATCHABLE_STATUSES = {TICKET_STATUS_PROCESSING, TICKET_STATUS_CLOSED}


class TicketCreateRequest(BaseModel):
    """创建工单请求体"""
    business_code: str
    content: str
    conversation_id: int | None = None


class TicketStatusUpdateRequest(BaseModel):
    """更新工单状态请求体"""
    status: str


class TicketItem(BaseModel):
    """工单响应模型"""
    id: int
    ticket_no: str
    user_id: int | None = None
    username: str | None = None
    conversation_id: int | None = None
    business_code: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime


async def _build_username_map(
    db: AsyncSession, tickets: list[ServiceTicket]
) -> dict[int, str]:
    """按 user_id 批量查询用户名。"""
    user_ids = {t.user_id for t in tickets if t.user_id is not None}
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u.username for u in result.scalars().all()}


def _ticket_to_item(t: ServiceTicket, usernames: dict[int, str]) -> dict:
    return TicketItem(
        id=t.id,
        ticket_no=t.ticket_no,
        user_id=t.user_id,
        username=usernames.get(t.user_id),
        conversation_id=t.conversation_id,
        business_code=t.business_code,
        content=t.content,
        status=t.status,
        created_at=t.created_at,
        updated_at=t.updated_at,
    ).model_dump()


@router.post("")
async def create_ticket_api(
    req: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交工单（登录即可）"""
    ticket = await create_ticket(
        db,
        req.business_code,
        req.content,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
    )
    return success(data=_ticket_to_item(ticket, {current_user.id: current_user.username}))


@router.get("")
async def list_tickets_api(
    status: str | None = Query(
        default=None, description="按状态筛选 open/processing/closed"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """工单列表 + 状态筛选（admin）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工单")
    tickets = await list_tickets(db, status)
    usernames = await _build_username_map(db, tickets)
    items = [_ticket_to_item(t, usernames) for t in tickets]
    return success(data=items)


@router.get("/{no}")
async def get_ticket_api(
    no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """工单详情（admin）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工单")
    ticket = await get_ticket_by_no(db, no)
    if not ticket:
        return error(code=40005, message="工单不存在")
    usernames = await _build_username_map(db, [ticket])
    return success(data=_ticket_to_item(ticket, usernames))


@router.patch("/{no}/status")
async def update_ticket_status_api(
    no: str,
    req: TicketStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新工单状态（admin），body {"status": "processing"|"closed"}"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可操作工单")
    if req.status not in _PATCHABLE_STATUSES:
        return error(code=40004, message=f"非法工单状态: {req.status}")
    try:
        ticket = await update_status(db, no, req.status)
    except ValueError as e:
        return error(code=40004, message=str(e))
    if not ticket:
        return error(code=40005, message="工单不存在")
    usernames = await _build_username_map(db, [ticket])
    return success(data=_ticket_to_item(ticket, usernames))
