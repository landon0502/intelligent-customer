"""企业业务工具 —— 查询 enterprise_biz 表，提交/查询工单（service_tickets 表）。"""

import logging

from langchain_core.tools import tool

from database.session import async_session_factory

logger = logging.getLogger("intelligent-customer.agent.tools.enterprise")


@tool
async def enterprise_query(service_code: str) -> str:
    """当用户提供业务编号或询问企业业务流程、办理条件时使用此工具。
    输入为业务编号，格式如 B-001。工具会返回该业务的办理说明。"""
    from services.enterprise import get_business_by_code, list_businesses

    async with async_session_factory() as session:
        biz = await get_business_by_code(session, service_code.upper())
        if not biz:
            businesses = await list_businesses(session)
            available = "、".join(b.name for b in businesses)
            return f"未找到业务编号 {service_code} 对应的业务。当前可办理业务：{available}。"
        return (
            f"【{biz.name}】\n"
            f"业务说明：{biz.description}\n"
            f"办理条件：{biz.requirements}\n"
            f"办理流程：{biz.process}"
        )


@tool
async def ticket_submit(business_code: str, customer_name: str, description: str) -> str:
    """当用户要求办理企业业务、提交申请时使用此工具。
    输入业务编号、客户名称和办理说明，工具会创建一张办理工单。"""
    from services.ticket import create_ticket
    from agent.tools.context import get_current_user_id, get_current_conversation_id

    async with async_session_factory() as session:
        ticket = await create_ticket(
            session,
            business_code=business_code,
            content=description,
            user_id=get_current_user_id(),
            conversation_id=get_current_conversation_id(),
        )
    logger.info(
        "创建工单: %s, 业务=%s, 客户=%s", ticket.ticket_no, business_code, customer_name
    )
    return (
        f"您的办理工单已创建，工单号 {ticket.ticket_no}，业务 {business_code}。"
        f"请留意后续办理进度通知。"
    )


@tool
async def ticket_status(ticket_id: str) -> str:
    """当用户询问办理进度、工单状态时使用此工具。
    输入工单号，格式如 TK-20260817-0001，工具会返回该工单的真实状态。"""
    from services.ticket import get_ticket_by_no

    async with async_session_factory() as session:
        ticket = await get_ticket_by_no(session, ticket_id)
    if not ticket:
        return f"未找到工单 {ticket_id}，请核对工单号。"
    return (
        f"工单 {ticket.ticket_no} 当前状态：{ticket.status}。"
        f"如需进一步处理请联系人工客服。"
    )
