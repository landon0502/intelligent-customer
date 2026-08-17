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


def filter_tools(tool_states: dict[str, str]) -> list:
    """从 ALL_TOOLS 过滤出启用工具（缺失状态按 enabled 处理）。"""
    return [t for t in ALL_TOOLS if tool_states.get(t.name, "enabled") == "enabled"]
