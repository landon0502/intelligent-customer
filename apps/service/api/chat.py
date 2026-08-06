"""对话接口 —— UIMessageStream SSE 流式对话，支持鉴权、工具调用展示和消息持久化。"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

from database.session import get_db
from schemas.user import User
from schemas.chat_schema import ChatSendRequest
from auth.security import get_current_user
from services.conversation import get_conversation_by_id
from services.message import create_message, get_recent_messages
from services.message_converter import ui_messages_to_langchain
from services.ui_message_stream import (
    StreamState,
    to_ui_message_stream_chunk,
    finish_stream,
    error_stream,
)
from app.dependencies import get_agent_async
from utils.response import error

logger = logging.getLogger("intelligent-customer.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/send")
async def chat_stream(
    req: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent=Depends(get_agent_async),
):
    """发送消息（UIMessageStream SSE 流式），自动持久化用户消息和助手回复"""
    # 验证会话归属
    conv = await get_conversation_by_id(db, req.conversation_id, current_user.id)
    if not conv:
        return error(code=40001, message="会话不存在")

    # 从请求体提取 UIMessage[] 并转换为 LangChain 历史
    # 如果前端发送了 messages，使用前端历史；否则从 DB 加载
    if req.messages:
        history_messages = ui_messages_to_langchain(req.messages)
        # 持久化用户消息（取最后一条 user 消息的文本）
        user_text = ""
        for msg in reversed(req.messages):
            if msg.get("role") == "user":
                user_text = "".join(
                    p.get("text", "")
                    for p in msg.get("parts", [])
                    if p.get("type") == "text"
                )
                break
        if user_text:
            await create_message(db, req.conversation_id, "user", user_text)
    else:
        # 兼容：如果前端未发送 messages，从 DB 加载历史
        recent = await get_recent_messages(db, req.conversation_id, limit=20)
        history_messages = []
        for msg in recent:
            if msg.role == "user":
                history_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history_messages.append(AIMessage(content=msg.content))

    # 收集完整回复用于持久化
    full_response: list[str] = []
    state = StreamState()

    async def event_generator():
        try:
            async for chunk, metadata in agent.astream(
                {"messages": history_messages},
                stream_mode="messages",
            ):
                # 收集 AI 文本内容用于持久化（排除 ToolMessage 等非 AI 内容）
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    full_response.append(chunk.content)

                # 转换为 UIMessageStream 事件
                async for event in to_ui_message_stream_chunk(chunk, state):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 发送结束事件
            async for event in finish_stream(state):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("Agent 流式输出异常: %s", e)
            async for event in error_stream(
                "AI 服务暂时不可用，请稍后重试", state
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            # 流结束后持久化助手回复
            if full_response:
                try:
                    await create_message(
                        db, req.conversation_id, "assistant", "".join(full_response)
                    )
                except Exception as e:
                    logger.error("持久化助手回复失败: %s", e)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
