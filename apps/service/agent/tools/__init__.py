"""Agent 工具模块 —— 定义 Agent 可调用的工具。

工具列表：
- knowledge_base_query: 知识库检索，当用户询问业务流程、办理条件、服务规范时触发
- enterprise_query: 企业业务查询，当用户提供业务编号或询问办理条件时触发
- ticket_submit: 工单提交，当用户要求办理企业业务时触发
- ticket_status: 工单状态查询，当用户询问办理进度时触发
- transfer_human: 转人工，当 Agent 判断无法处理时触发
- clarify: 追问澄清，当意图识别为"无法判断"时触发
"""

from agent.tools.knowledge import knowledge_base_query
from agent.tools.enterprise import enterprise_query, ticket_submit, ticket_status
from agent.tools.chat import transfer_human, clarify

ALL_TOOLS = [
    knowledge_base_query,
    enterprise_query,
    ticket_submit,
    ticket_status,
    transfer_human,
    clarify,
]
