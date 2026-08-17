"""工单 ORM 模型冒烟测试 —— 本任务只验证模型层；服务层用例由 Task 2.2 追加。"""

from schemas.ticket import ServiceTicket


def _make_ticket(ticket_no: str = "T-202608170001", **kwargs):
    defaults = dict(
        user_id=1,
        conversation_id=1,
        business_code="B-001",
        content="申请企业开户",
    )
    defaults.update(kwargs)
    return ServiceTicket(ticket_no=ticket_no, **defaults)


# ========== 模型 ==========

def test_service_ticket_tablename():
    assert ServiceTicket.__tablename__ == "service_tickets"


def test_service_ticket_defaults():
    ticket = _make_ticket()
    # status 经 __init__+setdefault 在构造期生效（对齐 user/enterprise_biz 惯例）
    assert ticket.status == "open"
    assert ticket.id is None
    assert ticket.ticket_no == "T-202608170001"
    assert ticket.user_id == 1
    assert ticket.conversation_id == 1
    assert ticket.business_code == "B-001"
    assert ticket.content == "申请企业开户"


def test_service_ticket_explicit_status():
    ticket = _make_ticket(ticket_no="T-202608170002", status="processing")
    assert ticket.status == "processing"
