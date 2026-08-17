"""工单服务 —— 工单号生成、列表/详情查询与状态流转。"""

import logging

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.ticket import ServiceTicket

logger = logging.getLogger("intelligent-customer.ticket")

TICKET_STATUS_OPEN = "open"
TICKET_STATUS_PROCESSING = "processing"
TICKET_STATUS_CLOSED = "closed"
TICKET_STATUS_VALUES = (
    TICKET_STATUS_OPEN,
    TICKET_STATUS_PROCESSING,
    TICKET_STATUS_CLOSED,
)


def _today_prefix() -> str:
    """生成工单号当日前缀 TK-YYYYMMDD-（UTC 日期）"""
    return datetime.now(timezone.utc).strftime("TK-%Y%m%d-")


async def _next_ticket_no(db: AsyncSession, prefix: str) -> str:
    """基于当日最大工单号生成下一个工单号。"""
    result = await db.execute(
        select(func.max(ServiceTicket.ticket_no)).where(
            ServiceTicket.ticket_no.like(f"{prefix}%")
        )
    )
    max_no = result.scalar_one_or_none()
    seq = int(max_no[len(prefix):]) if max_no else 0
    return f"{prefix}{seq + 1:04d}"


async def create_ticket(
    db: AsyncSession,
    business_code: str,
    content: str,
    user_id: int | None = None,
    conversation_id: int | None = None,
) -> ServiceTicket:
    """创建工单并生成 TK-YYYYMMDD-XXXX 工单号；唯一冲突时重试一次。"""
    prefix = _today_prefix()
    for attempt in range(2):
        ticket_no = await _next_ticket_no(db, prefix)
        ticket = ServiceTicket(
            ticket_no=ticket_no,
            user_id=user_id,
            conversation_id=conversation_id,
            business_code=business_code,
            content=content,
            status=TICKET_STATUS_OPEN,
        )
        db.add(ticket)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.warning("工单号冲突重试: %s (attempt=%d)", ticket_no, attempt + 1)
            continue
        await db.refresh(ticket)
        return ticket
    raise RuntimeError("工单号生成冲突，请重试")


async def list_tickets(
    db: AsyncSession, status: str | None = None
) -> list[ServiceTicket]:
    """获取工单列表；status 可选过滤，按创建时间倒序。"""
    stmt = select(ServiceTicket).order_by(ServiceTicket.created_at.desc())
    if status:
        stmt = stmt.where(ServiceTicket.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ticket_by_no(
    db: AsyncSession, ticket_no: str
) -> ServiceTicket | None:
    """按工单号查询工单。"""
    result = await db.execute(
        select(ServiceTicket).where(ServiceTicket.ticket_no == ticket_no)
    )
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession, ticket_no: str, status: str
) -> ServiceTicket | None:
    """更新工单状态；非法状态抛 ValueError，工单不存在返回 None。"""
    if status not in TICKET_STATUS_VALUES:
        raise ValueError(f"非法工单状态: {status}")
    ticket = await get_ticket_by_no(db, ticket_no)
    if not ticket:
        return None
    ticket.status = status
    await db.commit()
    await db.refresh(ticket)
    return ticket
