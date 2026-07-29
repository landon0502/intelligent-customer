from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from app.dependencies import get_agent
from utils.response import success

router = APIRouter(
    prefix="/api/agent",
)

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat(req: ChatRequest, agent = Depends(get_agent)):
    res = agent.invoke({
        "messages": [HumanMessage(content=req.message)]
    })
    return success(data=res)

@router.post("/chat-stream")
async def chat_stream(req: ChatRequest, agent = Depends(get_agent)):
    async def event_generator():
        async for chunk in agent.astream(
            {
                "messages": [HumanMessage(content=req.message)]
            },
            stream_mode="messages"
        ):
            token, metadata = chunk
            if token.content:
                yield {
                    "event": "message",
                    "data": token.content
                }

    return EventSourceResponse(
        event_generator()
    )
