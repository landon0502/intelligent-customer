"""对话接口 —— SSE 流式对话，支持鉴权、工具调用展示和消息持久化。"""

import json
import logging

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from database.session import get_db
from schemas.user import User
from schemas.chat_schema import ChatSendRequest
from auth.security import get_current_user
from services.conversation import get_conversation_by_id
from services.message import create_message, get_recent_messages
from app.dependencies import get_agent_async
from utils.response import success, error

logger = logging.getLogger("intelligent-customer.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/send")
async def chat_stream(
    req: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent=Depends(get_agent_async),
):
    """发送消息（SSE 流式），自动持久化用户消息和助手回复"""
    # 验证会话归属
    conv = await get_conversation_by_id(db, req.conversation_id, current_user.id)
    if not conv:
        return error(code=40001, message="会话不存在")

    # 持久化用户消息
    await create_message(db, req.conversation_id, "user", req.message)

    # 加载最近对话历史注入上下文
    recent = await get_recent_messages(db, req.conversation_id, limit=20)
    history_messages = []
    for msg in recent:
        if msg.role == "user":
            history_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history_messages.append(AIMessage(content=msg.content))

    # 收集完整回复用于持久化
    full_response = []

    async def event_generator():
        try:
            async for chunk, metadata in agent.astream(
                {"messages": history_messages},
                stream_mode="messages",
            ):
                # 1. 文本内容 —— 逐字推送
                if chunk.content:
                    full_response.append(chunk.content)
                    yield {
                        "event": "message",
                        "data": chunk.content,
                    }

                # 2. LLM 发起工具调用 —— 推送 tool_call 事件
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        yield {
                            "event": "tool_call",
                            "data": json.dumps(
                                {
                                    "name": tc["name"],
                                    "args": tc["args"],
                                    "id": tc["id"],
                                },
                                ensure_ascii=False,
                            ),
                        }

                # 3. 工具执行结果 —— 推送 tool_result 事件
                if isinstance(chunk, ToolMessage):
                    yield {
                        "event": "tool_result",
                        "data": json.dumps(
                            {
                                "name": chunk.name,
                                "content": chunk.content,
                                "tool_call_id": chunk.tool_call_id,
                            },
                            ensure_ascii=False,
                        ),
                    }

        except Exception as e:
            logger.error("Agent 流式输出异常: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"message": "AI 服务暂时不可用，请稍后重试"}, ensure_ascii=False),
            }
        finally:
            # 流结束后持久化助手回复
            if full_response:
                try:
                    await create_message(
                        db, req.conversation_id, "assistant", "".join(full_response)
                    )
                except Exception as e:
                    logger.error("持久化助手回复失败: %s", e)

            # 发送结束标记
            yield {
                "event": "done",
                "data": "[DONE]",
            }

    return EventSourceResponse(event_generator())
