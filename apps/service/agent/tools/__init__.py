"""Agent 工具模块 —— 定义 Agent 可调用的工具。

工具列表：
- knowledge_base_query: 知识库检索，当用户询问业务规则、产品信息时触发
- order_query: 订单查询，当用户提供订单号或问物流状态时触发
- business_action: 业务操作，当用户要求执行退货、修改地址等时触发
- transfer_human: 转人工，当 Agent 判断无法处理时触发
- clarify: 追问澄清，当意图识别为"无法判断"时触发
"""

from agent.tools.knowledge import knowledge_base_query
from agent.tools.order import order_query, business_action
from agent.tools.chat import transfer_human, clarify

ALL_TOOLS = [knowledge_base_query, order_query, business_action, transfer_human, clarify]
