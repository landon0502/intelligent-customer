"""对话辅助工具 —— 转人工和追问澄清。"""

import logging

from langchain_core.tools import tool

from database.session import async_session_factory

logger = logging.getLogger("intelligent-customer.agent.tools.chat")


@tool
async def transfer_human() -> str:
    """当你判断无法处理用户的问题，或需要人工介入时使用此工具。
    调用后会生成一条转人工工单（business_code=HUMAN）。

    触发条件：
    - 连续两次无法确定用户意图
    - 用户明确要求人工服务
    - 问题超出你的处理能力范围
    - 涉及投诉、纠纷等需要人工判断的场景
    """
    from services.ticket import create_ticket
    from agent.tools.context import get_current_user_id, get_current_conversation_id

    async with async_session_factory() as session:
        ticket = await create_ticket(
            session,
            business_code="HUMAN",
            content="用户请求转人工客服",
            user_id=get_current_user_id(),
            conversation_id=get_current_conversation_id(),
        )
    logger.info("生成转人工工单: %s", ticket.ticket_no)
    return (
        f"已为您转接人工客服，请稍候。工单号 {ticket.ticket_no}，"
        f"人工客服将在1-2分钟内为您服务，感谢您的耐心等待。"
    )


@tool
def clarify(question: str) -> str:
    """当用户意图不明确，需要追问澄清时使用此工具。
    输入为你要向用户提出的澄清问题。

    触发条件：
    - 用户的问题模糊，无法判断需要哪个工具
    - 用户提供的业务编号或工单号不完整
    - 用户的需求可以有多种理解

    使用示例：
    - clarify(question="请问您是想查询办理进度还是提交新工单？")
    - clarify(question="请提供完整的业务编号或工单号，格式如 B-001 或 TK-20260817-0001。")
    """
    return question
