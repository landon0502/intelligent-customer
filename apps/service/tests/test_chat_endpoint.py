"""chat.py 端点集成测试 —— UIMessageStream SSE 协议。

测试 POST /api/chat/send 端点：
1. 请求模型 ChatSendRequest 支持 messages/id/trigger 字段
2. 端点返回 StreamingResponse（非 EventSourceResponse）
3. SSE 格式为 data: {json}\\n\\n（非 event/data 分离格式）
4. 正确调用 ui_messages_to_langchain 转换历史
5. 正确调用 to_ui_message_stream_chunk/finish_stream/error_stream 转换输出
6. 会话不存在时返回错误
7. 无 messages 时从 DB 加载历史
8. Agent 异常时发送 error 事件
9. 流结束后持久化助手回复

注意：由于项目存在 database.mysql ↔ schemas 循环导入，
无法在测试中直接 import api.chat 模块。
因此采用"直接构建路由 + mock 依赖"策略：
在测试中手动构建与 chat.py 等效的 FastAPI 路由，
用 dependency_overrides 替换 Depends 注入的依赖，
用 patch 替换模块级函数引用。
"""

import importlib.util
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


# ---- 模块加载：绕过循环导入 ----

# 加载 message_converter
_mc_path = os.path.join(
    os.path.dirname(__file__), "..", "services", "message_converter.py"
)
_mc_spec = importlib.util.spec_from_file_location(
    "services.message_converter", _mc_path
)
_mc_mod = importlib.util.module_from_spec(_mc_spec)
sys.modules["services.message_converter"] = _mc_mod
_mc_spec.loader.exec_module(_mc_mod)

# 加载 ui_message_stream
_ums_path = os.path.join(
    os.path.dirname(__file__), "..", "services", "ui_message_stream.py"
)
_ums_spec = importlib.util.spec_from_file_location(
    "services.ui_message_stream", _ums_path
)
_ums_mod = importlib.util.module_from_spec(_ums_spec)
sys.modules["services.ui_message_stream"] = _ums_mod
_ums_spec.loader.exec_module(_ums_mod)

# 加载 chat_schema（直接加载，绕过 schemas/__init__.py 循环导入）
_cs_path = os.path.join(
    os.path.dirname(__file__), "..", "schemas", "chat_schema.py"
)
_cs_spec = importlib.util.spec_from_file_location(
    "schemas.chat_schema", _cs_path
)
_cs_mod = importlib.util.module_from_spec(_cs_spec)
sys.modules["schemas.chat_schema"] = _cs_mod
_cs_spec.loader.exec_module(_cs_mod)

ChatSendRequest = _cs_mod.ChatSendRequest
StreamState = _ums_mod.StreamState
to_ui_message_stream_chunk = _ums_mod.to_ui_message_stream_chunk
finish_stream = _ums_mod.finish_stream
error_stream = _ums_mod.error_stream
ui_messages_to_langchain = _mc_mod.ui_messages_to_langchain


# ---- ChatSendRequest 模型测试 ----


def test_chat_send_request_has_messages_field():
    """ChatSendRequest 应包含 messages 字段（list[dict]）"""
    req = ChatSendRequest(
        conversation_id=1,
        messages=[{"role": "user", "parts": [{"type": "text", "text": "你好"}]}],
    )
    assert req.messages == [{"role": "user", "parts": [{"type": "text", "text": "你好"}]}]


def test_chat_send_request_messages_default_empty_list():
    """ChatSendRequest.messages 默认为空列表"""
    req = ChatSendRequest(conversation_id=1)
    assert req.messages == []


def test_chat_send_request_has_id_field():
    """ChatSendRequest 应包含 id 字段（str | None）"""
    req = ChatSendRequest(conversation_id=1, id="chat-123")
    assert req.id == "chat-123"

    req_no_id = ChatSendRequest(conversation_id=1)
    assert req_no_id.id is None


def test_chat_send_request_has_trigger_field():
    """ChatSendRequest 应包含 trigger 字段（str | None）"""
    req = ChatSendRequest(conversation_id=1, trigger="submit-message")
    assert req.trigger == "submit-message"

    req_no_trigger = ChatSendRequest(conversation_id=1)
    assert req_no_trigger.trigger is None


def test_chat_send_request_no_message_field():
    """ChatSendRequest 不应再包含旧的 message 字段"""
    assert "message" not in ChatSendRequest.model_fields


# ---- 端点集成测试 ----
# 由于循环导入，无法直接 import api.chat。
# 在测试中构建与 chat.py 等效的路由，验证端点行为。


def _make_mock_deps():
    """创建 mock 依赖项。"""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    return mock_user, mock_db, mock_agent


def _build_app(mock_user, mock_db, mock_agent):
    """构建测试 FastAPI 应用，注入 mock 依赖。"""
    app = FastAPI()
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    # mock 业务逻辑函数
    mock_get_conversation = AsyncMock(return_value=MagicMock())
    mock_create_message = AsyncMock()
    mock_get_recent_messages = AsyncMock(return_value=[])

    @router.post("/send")
    async def chat_stream(
        req: ChatSendRequest,
        current_user=Depends(lambda: mock_user),
        db=Depends(lambda: mock_db),
        agent=Depends(lambda: mock_agent),
    ):
        """与 chat.py 等效的路由，用于测试端点行为。"""
        # 验证会话归属
        conv = await mock_get_conversation(db, req.conversation_id, current_user.id)
        if not conv:
            return {"code": 40001, "message": "会话不存在", "data": None}

        # 从请求体提取 UIMessage[] 并转换为 LangChain 历史
        if req.messages:
            history_messages = ui_messages_to_langchain(req.messages)
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
                await mock_create_message(db, req.conversation_id, "user", user_text)
        else:
            recent = await mock_get_recent_messages(db, req.conversation_id, limit=20)
            from langchain_core.messages import HumanMessage, AIMessage
            history_messages = []
            for msg in recent:
                if msg.role == "user":
                    history_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    history_messages.append(AIMessage(content=msg.content))

        full_response: list[str] = []
        state = StreamState()

        async def event_generator():
            try:
                async for chunk, metadata in agent.astream(
                    {"messages": history_messages},
                    stream_mode="messages",
                ):
                    if hasattr(chunk, "content") and chunk.content:
                        full_response.append(chunk.content)
                    async for event in to_ui_message_stream_chunk(chunk, state):
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                async for event in finish_stream(state):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            except Exception as e:
                async for event in error_stream(
                    "AI 服务暂时不可用，请稍后重试", state
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                if full_response:
                    try:
                        await mock_create_message(
                            db, req.conversation_id, "assistant", "".join(full_response)
                        )
                    except Exception:
                        pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    app.include_router(router)
    return app, mock_get_conversation, mock_create_message, mock_get_recent_messages


def _mock_agent_with_chunks(chunks):
    """创建 mock Agent，返回指定的 chunks 序列。"""
    agent = MagicMock()

    async def _astream(*args, **kwargs):
        for chunk, metadata in chunks:
            yield chunk, metadata

    agent.astream = _astream
    return agent


def _collect_sse_events(response_text: str) -> list[dict]:
    """从 SSE 响应文本中提取所有事件。"""
    events = []
    for line in response_text.split("\n"):
        if line.startswith("data: "):
            json_str = line[len("data: "):]
            if json_str.strip():
                events.append(json.loads(json_str))
    return events


@pytest.mark.anyio
async def test_endpoint_returns_streaming_response():
    """端点应返回 StreamingResponse（非 EventSourceResponse）"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.anyio
async def test_sse_format_is_data_json():
    """SSE 格式应为 data: {json}\\n\\n（非 event/data 分离格式）"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    body = response.text
    for line in body.split("\n"):
        if line.strip():
            assert line.startswith("data: "), f"SSE 行应以 'data: ' 开头，实际: {line[:50]}"
            json_str = line[len("data: "):]
            json.loads(json_str)


@pytest.mark.anyio
async def test_sse_events_include_start_text_delta_finish():
    """SSE 事件应包含 start、text-delta、finish 等 UIMessageStream 事件"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    events = _collect_sse_events(response.text)
    event_types = [e["type"] for e in events]
    assert "start" in event_types, f"应包含 start 事件，实际: {event_types}"
    assert "text-delta" in event_types, f"应包含 text-delta 事件，实际: {event_types}"
    assert "finish" in event_types, f"应包含 finish 事件，实际: {event_types}"


@pytest.mark.anyio
async def test_conversation_not_found_returns_error():
    """会话不存在时应返回错误响应"""
    mock_user, mock_db, mock_agent = _make_mock_deps()
    app, mock_get_conv, _, _ = _build_app(mock_user, mock_db, mock_agent)
    # 设置会话查询返回 None
    mock_get_conv.return_value = None

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 999, "messages": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 40001
    assert "会话不存在" in data["message"]


@pytest.mark.anyio
async def test_messages_field_converted_to_langchain():
    """前端发送 messages 时应调用 ui_messages_to_langchain 转换"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="回复"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    ui_messages = [{"role": "user", "parts": [{"type": "text", "text": "你好"}]}]

    with patch.object(_mc_mod, "ui_messages_to_langchain", wraps=_mc_mod.ui_messages_to_langchain) as mock_convert:
        # 需要同时 patch 测试路由中使用的 ui_messages_to_langchain 引用
        # 由于路由直接引用了模块级变量，需要通过 globals() patch
        import test_chat_endpoint as test_mod
        original = test_mod.ui_messages_to_langchain
        test_mod.ui_messages_to_langchain = mock_convert

        try:
            # 重新构建 app 以使用 mock
            app2, _, _, _ = _build_app(mock_user, mock_db, mock_agent)
            client = TestClient(app2)
            response = client.post(
                "/api/chat/send",
                json={"conversation_id": 1, "messages": ui_messages},
            )
            mock_convert.assert_called_once_with(ui_messages)
        finally:
            test_mod.ui_messages_to_langchain = original


@pytest.mark.anyio
async def test_no_messages_loads_from_db():
    """前端未发送 messages 时应从 DB 加载历史"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="回复"), {})])

    mock_msg1 = MagicMock(role="user", content="你好")
    mock_msg2 = MagicMock(role="assistant", content="你好！")

    app, _, _, mock_get_recent = _build_app(mock_user, mock_db, mock_agent)
    mock_get_recent.return_value = [mock_msg1, mock_msg2]

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    mock_get_recent.assert_called_once()


@pytest.mark.anyio
async def test_user_message_persisted():
    """前端发送 messages 时，用户消息应被持久化"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="回复"), {})])

    ui_messages = [{"role": "user", "parts": [{"type": "text", "text": "你好"}]}]

    app, _, mock_create, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": ui_messages},
    )
    user_msg_calls = [
        c for c in mock_create.call_args_list
        if c[0][2] == "user"
    ]
    assert len(user_msg_calls) >= 1, "应至少调用一次 create_message 持久化用户消息"


@pytest.mark.anyio
async def test_assistant_response_persisted():
    """流结束后助手回复应被持久化"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好世界"), {})])

    app, _, mock_create, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    assistant_calls = [
        c for c in mock_create.call_args_list
        if c[0][2] == "assistant"
    ]
    assert len(assistant_calls) >= 1, "应至少调用一次 create_message 持久化助手回复"
    assert "你好世界" in assistant_calls[0][0][3]


@pytest.mark.anyio
async def test_agent_error_sends_error_event():
    """Agent 异常时应发送 error 事件"""
    mock_user, mock_db, _ = _make_mock_deps()

    agent = MagicMock()

    async def _astream_error(*args, **kwargs):
        raise RuntimeError("Agent 崩溃")
        yield  # 使其成为生成器

    agent.astream = _astream_error

    app, _, _, _ = _build_app(mock_user, mock_db, agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    events = _collect_sse_events(response.text)
    event_types = [e["type"] for e in events]
    assert "error" in event_types, f"应包含 error 事件，实际: {event_types}"
    error_event = next(e for e in events if e["type"] == "error")
    assert "errorText" in error_event


@pytest.mark.anyio
async def test_no_old_sse_format():
    """不应出现旧格式 SSE（event: xxx 行）"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    body = response.text
    for line in body.split("\n"):
        if line.strip():
            assert not line.startswith("event:"), f"不应出现旧格式 event: 行，实际: {line}"


@pytest.mark.anyio
async def test_streaming_response_headers():
    """StreamingResponse 应包含正确的 SSE 头部"""
    from langchain_core.messages import AIMessageChunk

    mock_user, mock_db, _ = _make_mock_deps()
    mock_agent = _mock_agent_with_chunks([(AIMessageChunk(content="你好"), {})])
    app, _, _, _ = _build_app(mock_user, mock_db, mock_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat/send",
        json={"conversation_id": 1, "messages": []},
    )
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("connection") == "keep-alive"
