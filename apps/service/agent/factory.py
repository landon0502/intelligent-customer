from langchain.agents import create_agent

from models.factory import create_agent_llm
from agent.tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT


def create_customer_agent():
    """创建客服 Agent，绑定工具集和系统提示词。"""
    agent = create_agent(
        model=create_agent_llm({}),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent
