"""企业业务工具 —— 模拟企业业务查询与工单办理接口。"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger("intelligent-customer.agent.tools.enterprise")


# ========== 模拟数据 ==========

_MOCK_BUSINESS: dict[str, dict] = {
    "B-001": {
        "code": "B-001",
        "name": "企业开户",
        "description": "企业客户办理开户业务",
        "requirements": "需提供营业执照、法人身份证件、公章",
        "process": "提交申请 → 资质审核 → 完成开户（3 个工作日）",
    },
    "B-002": {
        "code": "B-002",
        "name": "对公转账",
        "description": "企业对公账户转账业务",
        "requirements": "需开通对公转账权限",
        "process": "填写收款方信息 → 确认金额 → 完成转账",
    },
    "B-003": {
        "code": "B-003",
        "name": "电子发票申领",
        "description": "企业电子发票申领业务",
        "requirements": "已完成企业实名认证",
        "process": "提交开票信息 → 审核 → 开具电子发票（1 个工作日）",
    },
}

_TICKET_COUNTER = 100


# ========== 工具定义 ==========


@tool
def enterprise_query(service_code: str) -> str:
    """当用户提供业务编号或询问企业业务流程、办理条件时使用此工具。
    输入为业务编号，格式如 B-001。工具会返回该业务的办理说明。"""
    biz = _MOCK_BUSINESS.get(service_code.upper())
    if not biz:
        available = "、".join(b["name"] for b in _MOCK_BUSINESS.values())
        return f"未找到业务编号 {service_code} 对应的业务。当前可办理业务：{available}。"
    return (
        f"【{biz['name']}】\n"
        f"业务说明：{biz['description']}\n"
        f"办理条件：{biz['requirements']}\n"
        f"办理流程：{biz['process']}"
    )


@tool
def ticket_submit(business_code: str, customer_name: str, description: str) -> str:
    """当用户要求办理企业业务、提交申请时使用此工具。
    输入业务编号、客户名称和办理说明，工具会创建一张办理工单。"""
    global _TICKET_COUNTER
    _TICKET_COUNTER += 1
    ticket_id = f"TK-{_TICKET_COUNTER}"
    logger.info(
        "创建工单: %s, 业务=%s, 客户=%s", ticket_id, business_code, customer_name
    )
    return (
        f"您的办理工单已创建，工单号 {ticket_id}，业务 {business_code}。"
        f"请留意后续办理进度通知。"
    )


@tool
def ticket_status(ticket_id: str) -> str:
    """当用户询问办理进度、工单状态时使用此工具。
    输入工单号，格式如 TK-101，工具会返回该工单的当前状态。"""
    return (
        f"工单 {ticket_id} 当前状态：审核中。预计办理完成时间：3 个工作日内。"
        f"如需进一步处理请联系人工客服。"
    )
