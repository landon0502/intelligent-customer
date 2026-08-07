"""订单查询与业务操作工具 —— 模拟订单系统和业务办理接口。"""

import random
import logging

from langchain_core.tools import tool

logger = logging.getLogger("intelligent-customer.agent.tools.order")


# ========== 模拟数据 ==========

_MOCK_ORDERS: dict[str, dict] = {
    "ORD-20260720": {
        "order_id": "ORD-20260720",
        "status": "已签收",
        "product": "智能音箱 Pro",
        "amount": "¥299.00",
        "signed_at": "2026-07-22 14:30",
        "address": "北京市朝阳区建国路88号",
    },
    "ORD-20260718": {
        "order_id": "ORD-20260718",
        "status": "已发货",
        "product": "无线蓝牙耳机",
        "amount": "¥159.00",
        "express_no": "SF1234567890",
        "estimated_delivery": "2026-07-31",
        "address": "上海市浦东新区陆家嘴路100号",
    },
    "ORD-20260715": {
        "order_id": "ORD-20260715",
        "status": "处理中",
        "product": "便携充电宝 20000mAh",
        "amount": "¥89.00",
        "address": "广州市天河区体育西路50号",
    },
}

_RETURN_COUNTER = 100


# ========== 工具定义 ==========


@tool
def order_query(order_id: str) -> str:
    """当用户提供订单号或询问订单状态、物流信息时使用此工具。
    输入为订单号，格式如 ORD-20260720。工具会返回该订单的详细信息。

    触发条件示例：
    - "帮我查一下订单 ORD-20260720 的状态"
    - "我的订单到哪了？订单号是 ORD-20260718"
    - "ORD-20260715 发货了吗？"
    """
    order = _MOCK_ORDERS.get(order_id)
    if order:
        lines = [f"订单号：{order['order_id']}", f"商品：{order['product']}", f"金额：{order['amount']}"]

        if order["status"] == "已签收":
            lines.append(f"状态：{order['status']}")
            lines.append(f"签收时间：{order['signed_at']}")
        elif order["status"] == "已发货":
            lines.append(f"状态：{order['status']}")
            lines.append(f"快递单号：{order['express_no']}")
            lines.append(f"预计送达：{order['estimated_delivery']}")
        else:
            lines.append(f"状态：{order['status']}")

        lines.append(f"收货地址：{order['address']}")
        return "\n".join(lines)

    return f"未找到订单 {order_id}，请确认订单号是否正确。订单号格式为 ORD-YYYYMMDD。"


@tool
def business_action(action: str, order_id: str) -> str:
    """当用户要求执行退货、修改地址等业务操作时使用此工具。
    输入为操作类型和订单号。

    支持的操作类型（action 参数）：
    - apply_return: 申请退货
    - change_address: 修改收货地址

    触发条件示例：
    - "我要退货，订单号 ORD-20260720" → action="apply_return", order_id="ORD-20260720"
    - "帮我改一下收货地址，订单 ORD-20260718" → action="change_address", order_id="ORD-20260718"
    """
    global _RETURN_COUNTER

    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return f"未找到订单 {order_id}，请确认订单号是否正确。"

    if action == "apply_return":
        if order["status"] == "已签收":
            _RETURN_COUNTER += 1
            ret_no = f"RET-2026{random.randint(1000, 9999)}"  # noqa: S311
            return (
                f"退货申请已提交：\n"
                f"退货单号：{ret_no}\n"
                f"订单号：{order_id}\n"
                f"商品：{order['product']}\n"
                f"预计退款：{order['amount']}\n"
                f"退款时间：收到退货商品后3个工作日内\n\n"
                f"请将商品寄回至：北京市朝阳区xx路xx号，使用原包装即可。"
            )
        elif order["status"] == "已发货":
            return "该订单正在配送中，请等签收后再申请退货。如需拒收请联系快递员。"
        else:
            return "该订单尚未发货，您可以直接取消订单，无需退货。"

    elif action == "change_address":
        if order["status"] == "已签收":
            return "该订单已签收，无法修改收货地址。"
        elif order["status"] == "已发货":
            return "该订单已发货，无法修改收货地址。建议联系快递公司更改配送地址。"
        else:
            return "收货地址修改功能暂未开放，请联系人工客服协助修改。"

    return f"不支持的操作类型：{action}。当前支持：apply_return（申请退货）、change_address（修改地址）。"
