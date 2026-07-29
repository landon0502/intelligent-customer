
from fastapi import Request

# Get the agent.
def get_agent(
    request: Request
):
    return request.app.state.agent