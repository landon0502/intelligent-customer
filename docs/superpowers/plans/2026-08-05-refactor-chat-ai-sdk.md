---
change: refactor-chat-ai-sdk
design-doc: docs/superpowers/specs/2026-08-05-refactor-chat-ai-sdk-design.md
base-ref: 4a8073d070ef465aa259172b62744e39a6e21f31
---

# refactor-chat-ai-sdk 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端 SSE 协议从自定义事件格式替换为 AI SDK UIMessageStream 协议，前端用 `useChat` hook 替换手写 SSE 流式处理。

**Architecture:** 后端重写 `/api/chat/send` 端点，输出 AI SDK UIMessageStream SSE 格式（`data: {json}\n\n`），包含 `start`/`text-start`/`text-delta`/`text-end`/`tool-input-start`/`tool-input-available`/`tool-output-available`/`finish-step`/`finish` 事件。前端用 `useChat` + `DefaultChatTransport` 替换 `sendChatStream`，消息渲染基于 `UIMessage.parts`。

**Tech Stack:** FastAPI + sse_starlette（后端）、Next.js 16 + React 19 + AI SDK 7.x（前端）、LangChain/LangGraph（Agent）

## 全局约束

- AI SDK 版本：`ai@^7.0.37`、`@ai-sdk/react@^4.0.37`（已安装，代码中未使用）
- 后端 SSE 格式：标准 `data: {json}\n\n`，不再使用 `event:` 字段
- UIMessageStream 事件类型严格遵循 AI SDK 7.x `UIMessageChunk` 类型定义
- LangChain Agent 使用 `astream(stream_mode="messages")`，返回 `(AIMessageChunk | ToolMessage, metadata)` 元组
- 消息持久化时机不变：用户消息在流开始前持久化，助手回复在流结束后持久化
- 鉴权方式不变：Bearer token 通过 `Authorization` 请求头注入
- 会话管理不变：`conversation_id` 仍通过请求体传递

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/service/api/chat.py` | 重写 | 端点输出 UIMessageStream SSE |
| `apps/service/schemas/chat_schema.py` | 修改 | 新增 `messages`/`id`/`trigger` 字段 |
| `apps/service/services/ui_message_stream.py` | 创建 | LangChain chunk → UIMessageStream 事件转换 |
| `apps/service/services/message_converter.py` | 创建 | UIMessage[] → LangChain HistoryMessage 转换 |
| `apps/web/components/chat/chat-page.tsx` | 重构 | 用 `useChat` 替换手写 SSE |
| `apps/web/components/chat/chat-container.tsx` | 创建 | 封装 `useChat` + 会话切换逻辑 |
| `apps/web/components/chat/message-bubble.tsx` | 重写 | 基于 `UIMessage.parts` 渲染 |
| `apps/web/components/chat/tool-call-status.tsx` | 适配 | 接收 `ToolUIPart` 替代 `ToolCall[]` |
| `apps/web/components/chat/chat-input.tsx` | 适配 | 使用 `useChat` 的 `input`/`setInput` |
| `apps/web/components/chat/useServices.ts` | 简化 | 移除 `sendChat`/`createLocal*`，保留会话 CRUD |
| `apps/web/services/chat.ts` | 删除 | `sendChatStream` 由 AI SDK Transport 替代 |

---

### Task 1: 后端 UIMessage → LangChain 消息转换器 ✅

**Files:**
- Create: `apps/service/services/message_converter.py`
- Test: `apps/service/tests/test_message_converter.py`

**Interfaces:**
- Consumes: 无（独立工具模块）
- Produces: `ui_messages_to_langchain(ui_messages: list[dict]) -> list[BaseMessage]` — 供 Task 3 的 chat.py 端点调用

- [ ] **Step 1: 编写失败测试**

```python
# apps/service/tests/test_message_converter.py
import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


def test_user_message_text_only():
    """纯文本用户消息转换"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [
        {"role": "user", "parts": [{"type": "text", "text": "退货政策是什么"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "退货政策是什么"


def test_assistant_message_text_only():
    """纯文本助手消息转换"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [
        {"role": "assistant", "parts": [{"type": "text", "text": "退货需在7天内"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].content == "退货需在7天内"


def test_assistant_message_with_tool_invocation():
    """助手消息含 tool-invocation part（legacy 格式）"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {"type": "text", "text": "让我查一下"},
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_1",
                    "args": {"query": "退货政策"},
                    "state": "result",
                    "result": "退货需在7天内...",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    # 应产生 AIMessage + ToolMessage
    assert len(result) == 2
    assert isinstance(result[0], AIMessage)
    assert result[0].content == "让我查一下"
    assert result[0].tool_calls is not None
    assert len(result[0].tool_calls) == 1
    assert result[0].tool_calls[0]["name"] == "knowledge_base_query"
    assert isinstance(result[1], ToolMessage)
    assert result[1].tool_call_id == "call_1"


def test_assistant_message_with_dynamic_tool_part():
    """助手消息含 tool-{toolName} 动态格式 part"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-knowledge_base_query",
                    "toolCallId": "call_2",
                    "args": {"query": "退款流程"},
                    "state": "call",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].tool_calls[0]["name"] == "knowledge_base_query"


def test_empty_parts():
    """空 parts 列表不产生消息"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [{"role": "user", "parts": []}]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 0


def test_mixed_conversation():
    """完整对话序列转换"""
    from services.message_converter import ui_messages_to_langchain

    ui_messages = [
        {"role": "user", "parts": [{"type": "text", "text": "查询订单"}]},
        {"role": "assistant", "parts": [{"type": "text", "text": "好的"}]},
        {"role": "user", "parts": [{"type": "text", "text": "订单号123"}]},
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 3
    assert isinstance(result[0], HumanMessage)
    assert isinstance(result[1], AIMessage)
    assert isinstance(result[2], HumanMessage)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_message_converter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.message_converter'`

- [ ] **Step 3: 编写最小实现**

```python
# apps/service/services/message_converter.py
"""UIMessage[] → LangChain Message 列表转换器。

将 AI SDK 前端发送的 UIMessage 格式转换为 LangChain 的
HumanMessage / AIMessage / ToolMessage 列表，供 Agent 消费。
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage


def ui_messages_to_langchain(ui_messages: list[dict]) -> list[BaseMessage]:
    """将 AI SDK UIMessage[] 转换为 LangChain Message 列表。

    Args:
        ui_messages: AI SDK UIMessage 格式的消息列表，每条消息包含
            role 和 parts 字段。

    Returns:
        LangChain BaseMessage 列表，可能包含 HumanMessage、AIMessage
        和 ToolMessage。
    """
    result: list[BaseMessage] = []

    for msg in ui_messages:
        if msg["role"] == "user":
            text = "".join(
                p.get("text", "")
                for p in msg.get("parts", [])
                if p.get("type") == "text"
            )
            if text:
                result.append(HumanMessage(content=text))

        elif msg["role"] == "assistant":
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[dict] = []

            for p in msg.get("parts", []):
                part_type = p.get("type", "")

                if part_type == "text":
                    text_parts.append(p.get("text", ""))

                elif part_type == "tool-invocation":
                    # Legacy format: type="tool-invocation"
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available"):
                        tool_results.append(p)

                elif part_type.startswith("tool-"):
                    # Dynamic format: type="tool-{toolName}"
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available"):
                        tool_results.append(p)

            # 创建 AIMessage（含文本和工具调用）
            if text_parts or tool_calls:
                tc_list = [
                    {
                        "name": tc.get("toolName", tc.get("name", "")),
                        "args": tc.get("args", tc.get("input", {})),
                        "id": tc.get("toolCallId", tc.get("tool_invocation_id", "")),
                        "type": "tool_call",
                    }
                    for tc in tool_calls
                ]
                result.append(
                    AIMessage(
                        content=" ".join(text_parts) if text_parts else "",
                        tool_calls=tc_list if tc_list else None,
                    )
                )

            # 创建 ToolMessage（工具结果）
            for tr in tool_results:
                result.append(
                    ToolMessage(
                        content=str(tr.get("result", tr.get("output", ""))),
                        tool_call_id=tr.get("toolCallId", tr.get("tool_invocation_id", "")),
                        name=tr.get("toolName", tr.get("name", "")),
                    )
                )

    return result
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_message_converter.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add apps/service/services/message_converter.py apps/service/tests/test_message_converter.py
git commit -m "feat(service): add UIMessage to LangChain message converter"
```

---

### Task 2: 后端 LangChain → UIMessageStream 转换函数

**Files:**
- Create: `apps/service/services/ui_message_stream.py`
- Test: `apps/service/tests/test_ui_message_stream.py`

**Interfaces:**
- Consumes: 无（独立工具模块）
- Produces: `to_ui_message_stream_chunk(chunk, state: StreamState) -> AsyncIterator[dict]` — 供 Task 3 的 chat.py 端点调用；`StreamState` 数据类管理流状态

- [ ] **Step 1: 编写失败测试**

```python
# apps/service/tests/test_ui_message_stream.py
import pytest
from langchain_core.messages import AIMessageChunk, ToolMessage

from services.ui_message_stream import to_ui_message_stream_chunk, StreamState


@pytest.mark.asyncio
async def test_text_delta():
    """AIMessageChunk 纯文本 → text-start + text-delta + text-end"""
    chunk = AIMessageChunk(content="你好")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    # 应产生 start + text-start + text-delta + text-end
    types = [e["type"] for e in events]
    assert "text-start" in types
    assert "text-delta" in types
    assert "text-end" in types
    # text-delta 的 delta 字段
    delta_event = next(e for e in events if e["type"] == "text-delta")
    assert delta_event["delta"] == "你好"


@pytest.mark.asyncio
async def test_empty_content_no_text_events():
    """空字符串 content 不产生 text 事件"""
    chunk = AIMessageChunk(content="")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)
    types = [e["type"] for e in events]
    assert "text-delta" not in types
    assert "text-start" not in types


@pytest.mark.asyncio
async def test_tool_calls_complete():
    """AIMessageChunk 含完整 tool_calls → tool-input-start + tool-input-available"""
    chunk = AIMessageChunk(
        content="",
        tool_calls=[
            {"name": "knowledge_base_query", "args": {"query": "退货"}, "id": "call_1", "type": "tool_call"}
        ],
    )
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    types = [e["type"] for e in events]
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    available = next(e for e in events if e["type"] == "tool-input-available")
    assert available["toolName"] == "knowledge_base_query"
    assert available["toolCallId"] == "call_1"
    assert available["input"] == {"query": "退货"}


@pytest.mark.asyncio
async def test_tool_call_chunks_incremental():
    """AIMessageChunk 含 tool_call_chunks（增量）→ tool-input-start + tool-input-delta"""
    chunk = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "knowledge_base_query", "args": '{"quer', "id": "call_2", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    types = [e["type"] for e in events]
    assert "tool-input-start" in types
    assert "tool-input-delta" in types
    delta = next(e for e in events if e["type"] == "tool-input-delta")
    assert delta["inputTextDelta"] == '{"quer'


@pytest.mark.asyncio
async def test_tool_message():
    """ToolMessage → tool-output-available"""
    chunk = ToolMessage(content="退货需在7天内", tool_call_id="call_1", name="knowledge_base_query")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    assert len(events) == 1
    assert events[0]["type"] == "tool-output-available"
    assert events[0]["toolCallId"] == "call_1"
    assert events[0]["output"] == "退货需在7天内"


@pytest.mark.asyncio
async def test_text_then_tool_call_same_chunk():
    """同一 chunk 同时有文本和工具调用：先关闭文本块再发工具事件"""
    chunk = AIMessageChunk(
        content="让我查一下",
        tool_calls=[
            {"name": "order_query", "args": {"order_id": "123"}, "id": "call_3", "type": "tool_call"}
        ],
    )
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    types = [e["type"] for e in events]
    # 文本事件应在工具事件之前
    text_end_idx = next(i for i, e in enumerate(events) if e["type"] == "text-end")
    tool_start_idx = next(i for i, e in enumerate(events) if e["type"] == "tool-input-start")
    assert text_end_idx < tool_start_idx


@pytest.mark.asyncio
async def test_tool_call_no_duplicate_start():
    """同一 tool_call_id 的 tool-input-start 只发一次"""
    chunk1 = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": '{"q', "id": "call_4", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    chunk2 = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": 'uery"}', "id": "call_4", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    state = StreamState(message_id="msg-1")

    all_events = []
    for chunk in [chunk1, chunk2]:
        async for event in to_ui_message_stream_chunk(chunk, state):
            all_events.append(event)

    start_count = sum(1 for e in all_events if e["type"] == "tool-input-start" and e.get("toolCallId") == "call_4")
    assert start_count == 1  # 只发一次 start
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_ui_message_stream.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.ui_message_stream'`

- [ ] **Step 3: 编写最小实现**

```python
# apps/service/services/ui_message_stream.py
"""LangChain Agent chunk → AI SDK UIMessageStream 事件转换。

将 LangChain Agent 的 astream(stream_mode="messages") 输出
转换为 AI SDK UIMessageStream 协议事件，供前端 useChat 消费。

UIMessageStream 事件类型：
- start: 流开始，携带 messageId
- text-start / text-delta / text-end: 文本流
- tool-input-start / tool-input-delta / tool-input-available: 工具调用
- tool-output-available: 工具结果
- start-step / finish-step: 步骤边界
- finish: 流结束
- error: 错误
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from langchain_core.messages import AIMessageChunk, ToolMessage

logger = logging.getLogger("intelligent-customer.ui_message_stream")


@dataclass
class StreamState:
    """UIMessageStream 转换状态，跨 chunk 维护。"""
    message_id: str = ""
    text_id: str = ""
    started_tool_calls: set = field(default_factory=set)
    step_started: bool = False
    stream_started: bool = False


def _new_id() -> str:
    return str(uuid.uuid4())


async def to_ui_message_stream_chunk(chunk, state: StreamState) -> AsyncIterator[dict]:
    """将单个 LangChain chunk 转换为 UIMessageStream 事件序列。

    Args:
        chunk: LangChain Agent 输出的 AIMessageChunk 或 ToolMessage
        state: 流状态，跨 chunk 维护

    Yields:
        UIMessageStream 事件字典，序列化为 SSE data 行
    """
    # 首次 chunk 发送 start 事件
    if not state.stream_started:
        state.stream_started = True
        if not state.message_id:
            state.message_id = _new_id()
        yield {"type": "start", "messageId": state.message_id}

    # 每个新步骤需要 start-step
    if not state.step_started:
        state.step_started = True
        yield {"type": "start-step"}

    # === ToolMessage: 工具结果 ===
    if isinstance(chunk, ToolMessage):
        yield {
            "type": "tool-output-available",
            "toolCallId": chunk.tool_call_id,
            "output": chunk.content,
        }
        # 工具结果后通常有新文本，关闭当前步骤
        yield {"type": "finish-step"}
        state.step_started = False
        state.text_id = ""
        return

    # === AIMessageChunk ===
    if not isinstance(chunk, AIMessageChunk):
        return

    # 1. 处理文本内容
    has_text = bool(chunk.content and chunk.content.strip() != "")
    has_tool_calls = bool(getattr(chunk, "tool_calls", None))
    has_tool_call_chunks = bool(getattr(chunk, "tool_call_chunks", None))

    if has_text:
        if not state.text_id:
            state.text_id = _new_id()
            yield {"type": "text-start", "id": state.text_id}
        yield {"type": "text-delta", "id": state.text_id, "delta": chunk.content}

        # 如果同时有工具调用，先关闭文本块
        if has_tool_calls or has_tool_call_chunks:
            yield {"type": "text-end", "id": state.text_id}
            state.text_id = ""

    # 2. 处理完整工具调用（tool_calls）
    if has_tool_calls:
        for tc in chunk.tool_calls:
            tc_id = tc.get("id", _new_id())
            if tc_id not in state.started_tool_calls:
                state.started_tool_calls.add(tc_id)
                yield {
                    "type": "tool-input-start",
                    "toolCallId": tc_id,
                    "toolName": tc.get("name", ""),
                }
            yield {
                "type": "tool-input-available",
                "toolCallId": tc_id,
                "toolName": tc.get("name", ""),
                "input": tc.get("args", {}),
            }

    # 3. 处理增量工具调用（tool_call_chunks）
    if has_tool_call_chunks and not has_tool_calls:
        for tcc in chunk.tool_call_chunks:
            if tcc is None:
                continue
            tc_id = tcc.get("id", "")
            if not tc_id:
                continue
            if tc_id not in state.started_tool_calls:
                state.started_tool_calls.add(tc_id)
                yield {
                    "type": "tool-input-start",
                    "toolCallId": tc_id,
                    "toolName": tcc.get("name", ""),
                }
            yield {
                "type": "tool-input-delta",
                "toolCallId": tc_id,
                "inputTextDelta": tcc.get("args", ""),
            }


async def finish_stream(state: StreamState, full_response: list[str]) -> AsyncIterator[dict]:
    """发送流结束事件序列。

    Args:
        state: 流状态
        full_response: 收集的完整文本回复

    Yields:
        finish-step + finish 事件
    """
    # 关闭未关闭的文本块
    if state.text_id:
        yield {"type": "text-end", "id": state.text_id}
        state.text_id = ""

    # 关闭未关闭的步骤
    if state.step_started:
        yield {"type": "finish-step"}

    yield {"type": "finish"}


async def error_stream(error_message: str, state: StreamState) -> AsyncIterator[dict]:
    """发送错误事件。

    Args:
        error_message: 错误消息文本
        state: 流状态

    Yields:
        error 事件
    """
    yield {"type": "error", "errorText": error_message}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_ui_message_stream.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add apps/service/services/ui_message_stream.py apps/service/tests/test_ui_message_stream.py
git commit -m "feat(service): add LangChain to UIMessageStream converter"
```

---

### Task 3: 后端 chat.py 端点重写

**Files:**
- Modify: `apps/service/api/chat.py`
- Modify: `apps/service/schemas/chat_schema.py`

**Interfaces:**
- Consumes: `ui_messages_to_langchain` from Task 1；`to_ui_message_stream_chunk`/`finish_stream`/`error_stream`/`StreamState` from Task 2
- Produces: `POST /api/chat/send` 端点输出 UIMessageStream SSE 格式

- [ ] **Step 1: 更新请求模型**

在 `apps/service/schemas/chat_schema.py` 中更新 `ChatSendRequest`：

```python
"""对话相关 Pydantic 模型 —— 请求体定义。"""

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """发送消息请求（AI SDK UIMessage 格式）"""
    conversation_id: int = Field(..., description="会话ID")
    messages: list[dict] = Field(default_factory=list, description="AI SDK UIMessage[]")
    id: str | None = Field(None, description="AI SDK chat ID")
    trigger: str | None = Field(None, description="submit-message | regenerate-message")
```

- [ ] **Step 2: 重写 chat.py 端点**

```python
"""对话接口 —— UIMessageStream SSE 流式对话，支持鉴权、工具调用展示和消息持久化。"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
        from langchain_core.messages import HumanMessage, AIMessage
        history_messages = []
        for msg in recent:
            if msg.role == "user":
                history_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history_messages.append(AIMessage(content=msg.content))
        # 最后一条是用户消息，也需要持久化（如果尚未持久化）
        # DB 加载的历史已持久化，无需重复

    # 收集完整回复用于持久化
    full_response: list[str] = []
    state = StreamState()

    async def event_generator():
        try:
            async for chunk, metadata in agent.astream(
                {"messages": history_messages},
                stream_mode="messages",
            ):
                # 收集文本内容用于持久化
                if hasattr(chunk, "content") and chunk.content:
                    full_response.append(chunk.content)

                # 转换为 UIMessageStream 事件
                async for event in to_ui_message_stream_chunk(chunk, state):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 发送结束事件
            async for event in finish_stream(state, full_response):
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
```

- [ ] **Step 3: 手动验证后端 SSE 输出格式**

启动后端服务，用 curl 发送请求，确认输出格式：

```bash
curl -N -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"conversation_id": 1, "messages": [{"role": "user", "parts": [{"type": "text", "text": "你好"}]}], "trigger": "submit-message"}'
```

Expected: SSE 输出包含 `data: {"type":"start",...}`、`data: {"type":"text-delta",...}`、`data: {"type":"finish"}` 等事件

- [ ] **Step 4: 提交**

```bash
git add apps/service/api/chat.py apps/service/schemas/chat_schema.py
git commit -m "feat(service): rewrite chat endpoint to output UIMessageStream protocol"
```

---

### Task 4: 前端 ChatContainer + useChat 集成

**Files:**
- Create: `apps/web/components/chat/chat-container.tsx`
- Modify: `apps/web/components/chat/useServices.ts`

**Interfaces:**
- Consumes: `useChatServices` 的 `loadMessages`、`createSession`、`removeSession`、`conversationsControl`；AI SDK `useChat` + `DefaultChatTransport`
- Produces: `ChatContainer` 组件（接收 `conversationId`，封装 `useChat`）；简化后的 `useChatServices`（移除 `sendChat`/`createLocal*`）

- [ ] **Step 1: 简化 useServices.ts**

移除 `sendChat`、`createLocalUserMessage`、`createLocalAssistantMessage` 及相关导入，保留会话 CRUD：

```typescript
// apps/web/components/chat/useServices.ts
import { useRequest } from "ahooks";
import { useMemo } from "react";
import {
  getConversationsApi,
  createConversationApi,
  deleteConversationApi,
  getConversationMessagesApi,
  type Conversation,
  type Message,
} from "@/services/conversation";

// ========== 展示类型 ==========

export interface DisplaySession {
  id: number;
  title: string;
  time: string;
}

// ========== 工具函数 ==========

function formatDateTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

/** 将后端 Conversation 转换为 DisplaySession */
function toDisplaySession(c: Conversation): DisplaySession {
  return {
    id: c.id,
    title: c.title,
    time: formatDateTime(c.updated_at),
  };
}

/** 将后端 Message 转换为 UIMessage 格式 */
export function toUIMessage(msg: Message) {
  return {
    id: `db-${msg.id}`,
    role: msg.role as "user" | "assistant",
    parts: [{ type: "text" as const, text: msg.content }],
    createdAt: new Date(msg.created_at),
  };
}

// ========== useServices ==========

export default function useChatServices() {
  // 获取会话列表
  const conversationsControl = useRequest(getConversationsApi, { manual: true });
  const { data: convData } = conversationsControl;
  const sessions = useMemo(() => (convData?.data ?? []).map(toDisplaySession), [convData]);

  // 获取会话消息
  const messagesControl = useRequest(getConversationMessagesApi, { manual: true });

  // 创建会话
  const createControl = useRequest(createConversationApi, { manual: true });

  // 删除会话
  const deleteControl = useRequest(deleteConversationApi, { manual: true });

  /** 创建新会话并返回 DisplaySession */
  async function createSession(title: string): Promise<DisplaySession | null> {
    try {
      const res = await createControl.runAsync(title);
      const newConv = res.data;
      return {
        id: newConv.id,
        title: newConv.title,
        time: formatDateTime(new Date().toISOString()),
      };
    } catch {
      return null;
    }
  }

  /** 删除会话 */
  async function removeSession(conversationId: number): Promise<boolean> {
    try {
      await deleteControl.runAsync(conversationId);
      return true;
    } catch {
      return false;
    }
  }

  /** 加载会话消息（UIMessage 格式） */
  async function loadMessages(conversationId: number) {
    try {
      const res = await messagesControl.runAsync(conversationId);
      return res.data.map(toUIMessage);
    } catch {
      return [];
    }
  }

  return {
    conversationsControl,
    sessions,
    loadMessages,
    createSession,
    removeSession,
  };
}
```

- [ ] **Step 2: 创建 ChatContainer 组件**

```typescript
// apps/web/components/chat/chat-container.tsx
"use client";

import { useState, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import type { UIMessage } from "ai";
import useChatServices, { toUIMessage } from "./useServices";
import { MessageArea } from "./message-area";
import { ChatInput } from "./chat-input";
import { tokenManager } from "@/lib/fetch/token-manager";

interface ChatContainerProps {
  conversationId: number;
}

export function ChatContainer({ conversationId }: ChatContainerProps) {
  const { loadMessages } = useChatServices();
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | null>(null);

  // 首次加载历史消息
  useEffect(() => {
    let cancelled = false;
    loadMessages(conversationId).then((msgs) => {
      if (!cancelled) {
        setInitialMessages(msgs.length > 0 ? msgs : []);
      }
    });
    return () => { cancelled = true; };
  }, [conversationId]);

  if (initialMessages === null) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return <ChatInner conversationId={conversationId} initialMessages={initialMessages} />;
}

function ChatInner({
  conversationId,
  initialMessages,
}: {
  conversationId: number;
  initialMessages: UIMessage[];
}) {
  const chat = useChat({
    id: `chat-${conversationId}`,
    initialMessages,
    sendAutomatically: true,
  });

  // 自定义 fetch 注入鉴权头和 conversation_id
  const customFetch: typeof globalThis.fetch = async (input, init) => {
    const token = tokenManager.getToken();
    const headers = new Headers(init?.headers);
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    // 注入 conversation_id 到 body
    const body = init?.body ? JSON.parse(String(init.body)) : {};
    body.conversation_id = conversationId;
    return globalThis.fetch(input, {
      ...init,
      headers,
      body: JSON.stringify(body),
    });
  };

  const isStreaming = chat.status === "streaming" || chat.status === "submitted";

  return (
    <>
      <MessageArea messages={chat.messages} />
      <ChatInput
        input={chat.input}
        setInput={chat.setInput}
        sendMessage={chat.sendMessage}
        status={chat.status}
        stop={chat.stop}
      />
    </>
  );
}
```

- [ ] **Step 3: 重构 chat-page.tsx**

```typescript
// apps/web/components/chat/chat-page.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import useChatServices, { type DisplaySession } from "./useServices";
import { SessionList } from "./session-list";
import { ChatContainer } from "./chat-container";

export function ChatPage() {
  const t = useTranslations("chat");
  const {
    conversationsControl,
    sessions,
    createSession,
    removeSession,
  } = useChatServices();

  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // 页面加载时获取会话列表
  useEffect(() => {
    conversationsControl.run();
  }, []);

  // 会话列表加载完成时自动选中第一个
  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      setCurrentSessionId(sessions[0]!.id);
    }
  }, [sessions]);

  const handleSelectSession = useCallback((id: number) => {
    setCurrentSessionId(id);
  }, []);

  const handleNewSession = useCallback(async () => {
    const newSession = await createSession(t("newSession"));
    if (!newSession) return;
    setCurrentSessionId(newSession.id);
  }, [t, createSession]);

  const handleDeleteSession = useCallback(
    async (id: number) => {
      const ok = await removeSession(id);
      if (!ok) return;
      setCurrentSessionId((prev) => {
        // 找到下一个会话
        const idx = sessions.findIndex((s) => s.id === id);
        const remaining = sessions.filter((s) => s.id !== id);
        if (prev === id) {
          return remaining[Math.min(idx, remaining.length - 1)]?.id ?? null;
        }
        return prev;
      });
    },
    [sessions, removeSession],
  );

  if (conversationsControl.loading) {
    return (
      <div className="flex h-full items-center justify-center" style={{ height: "calc(100% + 3rem)" }}>
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  return (
    <div className="flex h-full -m-6" style={{ height: "calc(100% + 3rem)" }}>
      <SessionList
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="flex-1 flex flex-col">
        {currentSessionId ? (
          <ChatContainer key={currentSessionId} conversationId={currentSessionId} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">{t("selectSession")}</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 验证前端编译通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 编译成功，无类型错误

- [ ] **Step 5: 提交**

```bash
git add apps/web/components/chat/chat-container.tsx apps/web/components/chat/chat-page.tsx apps/web/components/chat/useServices.ts
git commit -m "feat(web): integrate useChat hook with ChatContainer component"
```

---

### Task 5: 前端 MessageBubble 基于 UIMessage.parts 重写

**Files:**
- Modify: `apps/web/components/chat/message-bubble.tsx`

**Interfaces:**
- Consumes: `UIMessage` from `ai`；`ToolCallStatus` from Task 6
- Produces: `MessageBubble` 组件接收 `UIMessage` 替代 `DisplayMessage`

- [ ] **Step 1: 重写 message-bubble.tsx**

```typescript
// apps/web/components/chat/message-bubble.tsx
"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { UIMessage } from "ai";
import { ToolCallStatus } from "./tool-call-status";

const markdownComponents = {
  table: ({ children }: { children?: React.ReactNode }) => (
    <table className="my-2 w-full border-collapse text-sm">{children}</table>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border bg-muted px-2 py-1 text-left">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border px-2 py-1">{children}</td>
  ),
  code: ({
    children,
    className,
  }: {
    children?: React.ReactNode;
    className?: string;
  }) => (
    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{children}</code>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="my-2 border-l-3 border-muted-foreground/30 pl-3 text-muted-foreground">
      {children}
    </blockquote>
  ),
};

interface MessageBubbleProps {
  message: UIMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2.5 text-primary-foreground">
          {message.parts
            .filter((p): p is Extract<typeof p, { type: "text" }> => p.type === "text")
            .map((p, i) => (
              <p key={i}>{p.text}</p>
            ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] rounded-xl rounded-bl-sm border bg-background px-3.5 py-2.5">
        {message.parts.map((part, i) => {
          if (part.type === "text") {
            return (
              <ReactMarkdown
                key={i}
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {part.text}
              </ReactMarkdown>
            );
          }

          if (part.type.startsWith("tool-")) {
            return <ToolCallStatus key={i} toolPart={part} />;
          }

          return null;
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 更新 MessageArea 组件的 props 类型**

检查 `message-area.tsx` 是否需要更新 `MessageBubble` 的 props 类型。如果 `MessageArea` 传递 `DisplayMessage` 给 `MessageBubble`，需要改为传递 `UIMessage`：

```bash
grep -n "MessageBubble\|DisplayMessage" apps/web/components/chat/message-area.tsx
```

根据结果更新 `MessageArea` 接收 `UIMessage[]` 并传递给 `MessageBubble`。

- [ ] **Step 3: 验证编译通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 编译成功

- [ ] **Step 4: 提交**

```bash
git add apps/web/components/chat/message-bubble.tsx apps/web/components/chat/message-area.tsx
git commit -m "feat(web): rewrite MessageBubble to render based on UIMessage.parts"
```

---

### Task 6: 前端 ToolCallStatus 适配 ToolUIPart

**Files:**
- Modify: `apps/web/components/chat/tool-call-status.tsx`

**Interfaces:**
- Consumes: AI SDK `ToolUIPart` 类型（`type` 以 `tool-` 开头的 part）
- Produces: `ToolCallStatus` 组件接收 `toolPart` prop 替代 `toolCalls: ToolCall[]`

- [ ] **Step 1: 重写 tool-call-status.tsx**

```typescript
// apps/web/components/chat/tool-call-status.tsx
"use client";

interface ToolCallStatusProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  toolPart: any; // ToolUIPart — AI SDK 动态工具 part
}

function formatToolResult(result: unknown): string {
  if (typeof result === "string") {
    return result.length > 60 ? result.slice(0, 60) + "..." : result;
  }
  const str = JSON.stringify(result);
  return str.length > 60 ? str.slice(0, 60) + "..." : str;
}

export function ToolCallStatus({ toolPart }: ToolCallStatusProps) {
  const isCalling = toolPart.state === "call" || toolPart.state === "partial-call";
  const isDone = toolPart.state === "result";

  const toolName = toolPart.toolName ?? toolPart.type.replace("tool-", "");

  return (
    <div className="mt-2 space-y-1.5">
      {isCalling && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3.5 py-2 text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
          <span className="text-black">
            🔧 调用工具：{toolName}(...)
          </span>
        </div>
      )}
      {isDone && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3.5 py-2 text-sm">
          <span className="text-green-600">✓</span>
          <span className="text-black">{formatToolResult(toolPart.result)}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证编译通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 编译成功

- [ ] **Step 3: 提交**

```bash
git add apps/web/components/chat/tool-call-status.tsx
git commit -m "feat(web): adapt ToolCallStatus to accept ToolUIPart from AI SDK"
```

---

### Task 7: 前端 ChatInput 适配 useChat 接口

**Files:**
- Modify: `apps/web/components/chat/chat-input.tsx`

**Interfaces:**
- Consumes: `useChat` 的 `input`/`setInput`/`sendMessage`/`status`/`stop`
- Produces: `ChatInput` 组件接收新 props 接口

- [ ] **Step 1: 重写 chat-input.tsx**

```typescript
// apps/web/components/chat/chat-input.tsx
"use client";

import { useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Send, Square } from "lucide-react";

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  sendMessage: (message: string) => void;
  status: string;
  stop: () => void;
}

export function ChatInput({ input, setInput, sendMessage, status, stop }: ChatInputProps) {
  const t = useTranslations("chat");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isStreaming = status === "streaming" || status === "submitted";

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = Math.min(Math.max(el.scrollHeight, 40), 120) + "px";
    },
    [setInput],
  );

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    sendMessage(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px";
    }
  }, [input, isStreaming, sendMessage, setInput]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="border-t p-4">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          disabled={isStreaming}
          rows={1}
          className="scrollbar-hide flex-1 resize-none rounded-lg border bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:opacity-50"
          style={{ height: "40px" }}
        />
        {isStreaming ? (
          <button
            onClick={stop}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90"
            aria-label="停止"
          >
            <Square className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
            aria-label={t("send")}
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证编译通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 编译成功

- [ ] **Step 3: 提交**

```bash
git add apps/web/components/chat/chat-input.tsx
git commit -m "feat(web): adapt ChatInput to useChat input/setInput/sendMessage interface"
```

---

### Task 8: 删除废弃文件与清理

**Files:**
- Delete: `apps/web/services/chat.ts`
- Modify: `apps/web/components/chat/session-list.tsx`（移除 `DisplayMessage` 相关类型，如果有的话）

**Interfaces:**
- Consumes: 无
- Produces: 清理后的代码库，无残留引用

- [ ] **Step 1: 检查 chat.ts 的所有引用**

```bash
grep -rn "from.*services/chat\|from.*@/services/chat" apps/web/ --include="*.ts" --include="*.tsx"
```

确认 `services/chat.ts` 不再被任何文件引用。如果 `useServices.ts` 仍引用它，确认已在 Task 4 中移除。

- [ ] **Step 2: 检查 session-list.tsx 的类型依赖**

```bash
grep -n "DisplayMessage\|ToolCall" apps/web/components/chat/session-list.tsx
```

如果 `session-list.tsx` 导出了 `DisplayMessage` 类型，需要移除或更新（`MessageBubble` 现在使用 `UIMessage`）。

- [ ] **Step 3: 删除 chat.ts**

```bash
rm apps/web/services/chat.ts
```

- [ ] **Step 4: 更新 session-list.tsx 类型**

移除 `session-list.tsx` 中对 `DisplayMessage` 的导出（如果存在），因为 `MessageBubble` 现在接收 `UIMessage`。`SessionList` 组件只需要 `DisplaySession` 的 `id`/`title`/`time` 字段，不需要 `messages`。

- [ ] **Step 5: 验证编译通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 编译成功，无未解析引用

- [ ] **Step 6: 提交**

```bash
git add -A apps/web/services/chat.ts apps/web/components/chat/session-list.tsx
git commit -m "chore(web): remove deprecated chat.ts and clean up DisplayMessage references"
```

---

### Task 9: 端到端验证

**Files:**
- 无新文件（验证现有实现）

**Interfaces:**
- Consumes: 所有前序 Task 的产物
- Produces: 验证报告

- [ ] **Step 1: 启动后端服务**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && docker compose up -d
```

- [ ] **Step 2: 启动前端开发服务器**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm dev
```

- [ ] **Step 3: 验证流式 Markdown 渲染**

在浏览器中打开聊天页面，发送包含加粗、代码块、表格、列表的消息，确认流式过程中正确渲染。

- [ ] **Step 4: 验证工具调用状态**

触发知识库检索等工具，确认调用中（黄色旋转动画）和完成（绿色勾号）状态正确显示。

- [ ] **Step 5: 验证会话切换**

切换会话后历史消息正确加载，新消息正常发送和流式接收。

- [ ] **Step 6: 验证鉴权**

确认 Bearer token 正确注入请求头（检查浏览器 Network 面板）。

- [ ] **Step 7: 验证停止功能**

流式过程中点击停止按钮，确认流正确中断。

- [ ] **Step 8: 提交验证记录**

```bash
git commit --allow-empty -m "chore: e2e verification passed for refactor-chat-ai-sdk"
```
