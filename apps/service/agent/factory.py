from langchain.agents import create_agent
from models import factory


def create_customer_agent():
    agent = create_agent(
        model=factory.create_llm(),
        tools=[],
    )
    return agent