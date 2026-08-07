"""Agent 工厂函数 — 创建客服 Agent 实例。

纯函数，接受注入的 LLM 实例。由 ComponentRegistry 调用。
"""

from langchain.agents import create_agent
from langchain.messages import SystemMessage
from agent.tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT


def create_customer_agent(agent_llm, tools=None, system_prompt=None):
    """创建客服 Agent，绑定工具集和系统提示词。

    Args:
        agent_llm: BaseChatModel 实例（由 Registry 注入）
        tools: 工具列表，默认使用 ALL_TOOLS
        system_prompt: 系统提示词，默认使用 SYSTEM_PROMPT

    Returns:
        Agent 实例
    """
    return create_agent(
        model=agent_llm,
        tools=tools or ALL_TOOLS,
        system_prompt=SystemMessage(content=system_prompt or SYSTEM_PROMPT),
    )
