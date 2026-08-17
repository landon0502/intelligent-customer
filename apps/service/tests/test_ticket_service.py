"""工单模型冒烟测试 + 服务层测试 —— AsyncMock db session / patch 服务函数。"""

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from schemas.ticket import ServiceTicket
from services.ticket import (
    create_ticket,
    list_tickets,
    get_ticket_by_no,
    update_status,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_PROCESSING,
    TICKET_STATUS_CLOSED,
)


def _today_prefix() -> str:
    return datetime.now(timezone.utc).strftime("TK-%Y%m%d-")


def _make_model_ticket(ticket_no: str = "T-202608170001", **kwargs):
    defaults = dict(
        user_id=1,
        conversation_id=1,
        business_code="B-001",
        content="申请企业开户",
    )
    defaults.update(kwargs)
    return ServiceTicket(ticket_no=ticket_no, **defaults)


def _make_ticket(ticket_no: str = "TK-20260817-0001", status: str = "open"):
    return ServiceTicket(
        ticket_no=ticket_no,
        user_id=1,
        conversation_id=None,
        business_code="B-001",
        content="办理企业开户",
        status=status,
    )


# ========== 模型 ==========

def test_service_ticket_tablename():
    assert ServiceTicket.__tablename__ == "service_tickets"


def test_service_ticket_defaults():
    ticket = _make_model_ticket()
    # status 经 __init__+setdefault 在构造期生效（对齐 user/enterprise_biz 惯例）
    assert ticket.status == "open"
    assert ticket.id is None
    assert ticket.ticket_no == "T-202608170001"
    assert ticket.user_id == 1
    assert ticket.conversation_id == 1
    assert ticket.business_code == "B-001"
    assert ticket.content == "申请企业开户"


def test_service_ticket_explicit_status():
    ticket = _make_model_ticket(ticket_no="T-202608170002", status="processing")
    assert ticket.status == "processing"


# ========== 服务层 ==========

@pytest.mark.anyio
async def test_create_ticket_generates_valid_ticket_no():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "办理企业开户", user_id=1)
    assert re.match(r"^TK-\d{8}-\d{4}$", ticket.ticket_no)
    assert ticket.status == TICKET_STATUS_OPEN
    assert ticket.user_id == 1
    assert ticket.business_code == "B-001"


@pytest.mark.anyio
async def test_create_ticket_sequence_increments():
    prefix = _today_prefix()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=f"{prefix}0003"))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "test")
    assert ticket.ticket_no == f"{prefix}0004"


@pytest.mark.anyio
async def test_create_ticket_retries_on_integrity_error():
    prefix = _today_prefix()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=f"{prefix}0001"))
    )
    db.add = MagicMock()
    db.commit = AsyncMock(
        side_effect=[IntegrityError("INSERT", {}, Exception("dup")), None]
    )
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "test")
    assert ticket.ticket_no == f"{prefix}0002"
    assert db.commit.await_count == 2
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_create_ticket_raises_runtime_error_when_retries_exhausted():
    prefix = _today_prefix()
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("dup")))
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    with patch(
        "services.ticket._next_ticket_no",
        new=AsyncMock(return_value=f"{prefix}0001"),
    ):
        with pytest.raises(RuntimeError):
            await create_ticket(db, "B-001", "test")
    # 两次 attempt 均冲突：commit 与 rollback 各执行两次后抛 RuntimeError
    assert db.commit.await_count == 2
    assert db.rollback.await_count == 2


@pytest.mark.anyio
async def test_list_tickets_no_filter():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_ticket("TK-20260817-0002"),
        _make_ticket("TK-20260817-0001"),
    ]
    db.execute = AsyncMock(return_value=result)
    tickets = await list_tickets(db)
    assert len(tickets) == 2
    assert tickets[0].ticket_no == "TK-20260817-0002"
    # 无 status 时不加过滤条件；按创建时间倒序
    stmt = db.execute.await_args.args[0]
    assert stmt.whereclause is None
    assert "service_tickets.created_at DESC" in str(stmt.compile())


@pytest.mark.anyio
async def test_list_tickets_with_status_filter():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_ticket("TK-20260817-0001", status="processing")
    ]
    db.execute = AsyncMock(return_value=result)
    tickets = await list_tickets(db, TICKET_STATUS_PROCESSING)
    assert len(tickets) == 1
    assert tickets[0].status == TICKET_STATUS_PROCESSING
    # 断言 status 过滤条件真实构造并传入正确枚举值；按创建时间倒序
    stmt = db.execute.await_args.args[0]
    assert stmt.whereclause is not None
    assert "service_tickets.status" in str(stmt.whereclause)
    assert stmt.compile().params.get("status_1") == TICKET_STATUS_PROCESSING
    assert "service_tickets.created_at DESC" in str(stmt.compile())


@pytest.mark.anyio
async def test_get_ticket_by_no_hit():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_ticket("TK-20260817-0001")))
    )
    ticket = await get_ticket_by_no(db, "TK-20260817-0001")
    assert ticket is not None
    assert ticket.ticket_no == "TK-20260817-0001"


@pytest.mark.anyio
async def test_get_ticket_by_no_miss():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    ticket = await get_ticket_by_no(db, "TK-99999999-9999")
    assert ticket is None


@pytest.mark.anyio
async def test_update_status_valid_transition():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_ticket("TK-20260817-0001", status="open")))
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await update_status(db, "TK-20260817-0001", TICKET_STATUS_PROCESSING)
    assert ticket is not None
    assert ticket.status == TICKET_STATUS_PROCESSING


@pytest.mark.anyio
async def test_update_status_invalid_value_raises():
    db = AsyncMock()
    with pytest.raises(ValueError):
        await update_status(db, "TK-20260817-0001", "invalid-status")


@pytest.mark.anyio
async def test_update_status_not_found_returns_none():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    ticket = await update_status(db, "TK-99999999-9999", TICKET_STATUS_CLOSED)
    assert ticket is None
