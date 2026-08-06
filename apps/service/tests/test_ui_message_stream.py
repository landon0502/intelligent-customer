"""LangChain Agent chunk → AI SDK UIMessageStream 事件转换测试。"""

import importlib.util
import os
import sys

import pytest
from langchain_core.messages import AIMessageChunk, ToolMessage


# 直接加载 ui_message_stream 模块，绕过 services/__init__.py 的循环导入
_module_path = os.path.join(
    os.path.dirname(__file__), "..", "services", "ui_message_stream.py"
)
_spec = importlib.util.spec_from_file_location(
    "services.ui_message_stream", _module_path
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["services.ui_message_stream"] = _mod
_spec.loader.exec_module(_mod)

to_ui_message_stream_chunk = _mod.to_ui_message_stream_chunk
StreamState = _mod.StreamState
finish_stream = _mod.finish_stream
error_stream = _mod.error_stream


# ---- 核心转换测试 ----


@pytest.mark.anyio
async def test_text_delta():
    """AIMessageChunk 纯文本 → text-start + text-delta（text-end 由 finish_stream 发送）"""
    chunk = AIMessageChunk(content="你好")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    # 纯文本 chunk 产生 start + start-step + text-start + text-delta
    # text-end 不在此处发送，由 finish_stream 统一关闭
    types = [e["type"] for e in events]
    assert "text-start" in types
    assert "text-delta" in types
    # text-delta 的 delta 字段
    delta_event = next(e for e in events if e["type"] == "text-delta")
    assert delta_event["delta"] == "你好"


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_tool_call_chunks_incremental():
    """AIMessageChunk 含 tool_call_chunks（增量）→ tool-input-start + tool-input-delta

    LangChain 会自动从 tool_call_chunks 生成 tool_calls（args 为空字典），
    转换器应识别增量模式，优先使用 tool_call_chunks 的字符串 args。
    """
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


@pytest.mark.anyio
async def test_tool_message():
    """ToolMessage → tool-output-available + finish-step"""
    chunk = ToolMessage(content="退货需在7天内", tool_call_id="call_1", name="knowledge_base_query")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    # ToolMessage 产生 start + start-step + tool-output-available + finish-step
    output_event = next(e for e in events if e["type"] == "tool-output-available")
    assert output_event["toolCallId"] == "call_1"
    assert output_event["output"] == "退货需在7天内"
    # finish-step 应在 tool-output-available 之后
    output_idx = next(i for i, e in enumerate(events) if e["type"] == "tool-output-available")
    finish_idx = next(i for i, e in enumerate(events) if e["type"] == "finish-step")
    assert finish_idx > output_idx


@pytest.mark.anyio
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


@pytest.mark.anyio
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


# ---- 流生命周期测试 ----


@pytest.mark.anyio
async def test_start_event_on_first_chunk():
    """首次 chunk 发送 start 事件，携带 messageId"""
    chunk = AIMessageChunk(content="hello")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    start_event = next(e for e in events if e["type"] == "start")
    assert start_event["messageId"] == "msg-1"


@pytest.mark.anyio
async def test_start_event_only_once():
    """start 事件只在首次 chunk 发送一次"""
    chunk1 = AIMessageChunk(content="hello")
    chunk2 = AIMessageChunk(content=" world")
    state = StreamState(message_id="msg-1")

    all_events = []
    for chunk in [chunk1, chunk2]:
        async for event in to_ui_message_stream_chunk(chunk, state):
            all_events.append(event)

    start_count = sum(1 for e in all_events if e["type"] == "start")
    assert start_count == 1


@pytest.mark.anyio
async def test_start_step_on_first_chunk():
    """首次 chunk 发送 start-step 事件"""
    chunk = AIMessageChunk(content="hello")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    assert "start-step" in [e["type"] for e in events]


@pytest.mark.anyio
async def test_auto_generate_message_id():
    """未提供 message_id 时自动生成"""
    chunk = AIMessageChunk(content="hello")
    state = StreamState()  # 无 message_id
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    start_event = next(e for e in events if e["type"] == "start")
    assert start_event["messageId"]  # 非空字符串
    assert len(start_event["messageId"]) > 0


@pytest.mark.anyio
async def test_tool_message_finishes_step():
    """ToolMessage 后发送 finish-step，重置步骤状态"""
    chunk = ToolMessage(content="结果", tool_call_id="call_1", name="kb_query")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    types = [e["type"] for e in events]
    assert "finish-step" in types
    # finish-step 应在 tool-output-available 之后
    output_idx = next(i for i, e in enumerate(events) if e["type"] == "tool-output-available")
    finish_idx = next(i for i, e in enumerate(events) if e["type"] == "finish-step")
    assert finish_idx > output_idx


@pytest.mark.anyio
async def test_new_step_after_tool_message():
    """ToolMessage 后的 AIMessageChunk 应触发新的 start-step"""
    tool_chunk = ToolMessage(content="结果", tool_call_id="call_1", name="kb_query")
    ai_chunk = AIMessageChunk(content="根据查询结果")
    state = StreamState(message_id="msg-1")

    all_events = []
    for chunk in [tool_chunk, ai_chunk]:
        async for event in to_ui_message_stream_chunk(chunk, state):
            all_events.append(event)

    # 应有两个 start-step 事件
    start_step_count = sum(1 for e in all_events if e["type"] == "start-step")
    assert start_step_count == 2


# ---- finish_stream / error_stream 测试 ----


@pytest.mark.anyio
async def test_finish_stream_closes_text_and_step():
    """finish_stream 关闭未关闭的文本块和步骤"""
    state = StreamState(message_id="msg-1", text_id="txt-1", step_started=True)
    events = []
    async for event in finish_stream(state, []):
        events.append(event)

    types = [e["type"] for e in events]
    assert "text-end" in types
    assert "finish-step" in types
    assert "finish" in types
    # 顺序：text-end → finish-step → finish
    text_end_idx = next(i for i, e in enumerate(events) if e["type"] == "text-end")
    finish_step_idx = next(i for i, e in enumerate(events) if e["type"] == "finish-step")
    finish_idx = next(i for i, e in enumerate(events) if e["type"] == "finish")
    assert text_end_idx < finish_step_idx < finish_idx


@pytest.mark.anyio
async def test_finish_stream_no_open_text():
    """finish_stream 无未关闭文本块时不发 text-end"""
    state = StreamState(message_id="msg-1", text_id="", step_started=True)
    events = []
    async for event in finish_stream(state, []):
        events.append(event)

    types = [e["type"] for e in events]
    assert "text-end" not in types
    assert "finish-step" in types
    assert "finish" in types


@pytest.mark.anyio
async def test_error_stream():
    """error_stream 发送 error 事件"""
    state = StreamState(message_id="msg-1")
    events = []
    async for event in error_stream("连接超时", state):
        events.append(event)

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["errorText"] == "连接超时"


# ---- 边界情况测试 ----


@pytest.mark.anyio
async def test_whitespace_only_content_no_text_events():
    """仅含空白字符的 content 不产生 text 事件"""
    chunk = AIMessageChunk(content="   ")
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)
    types = [e["type"] for e in events]
    assert "text-delta" not in types
    assert "text-start" not in types


@pytest.mark.anyio
async def test_text_id_carries_across_chunks():
    """连续文本 chunk 共享同一 text_id，不重复发 text-start"""
    chunk1 = AIMessageChunk(content="你好")
    chunk2 = AIMessageChunk(content="世界")
    state = StreamState(message_id="msg-1")

    all_events = []
    for chunk in [chunk1, chunk2]:
        async for event in to_ui_message_stream_chunk(chunk, state):
            all_events.append(event)

    text_start_count = sum(1 for e in all_events if e["type"] == "text-start")
    assert text_start_count == 1  # 只发一次 text-start


@pytest.mark.anyio
async def test_multiple_tool_calls_in_one_chunk():
    """一个 chunk 包含多个 tool_calls，每个都发 start + available"""
    chunk = AIMessageChunk(
        content="",
        tool_calls=[
            {"name": "kb_query", "args": {"q": "退货"}, "id": "call_a", "type": "tool_call"},
            {"name": "order_query", "args": {"order_id": "123"}, "id": "call_b", "type": "tool_call"},
        ],
    )
    state = StreamState(message_id="msg-1")
    events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        events.append(event)

    tool_starts = [e for e in events if e["type"] == "tool-input-start"]
    assert len(tool_starts) == 2
    tool_ids = {e["toolCallId"] for e in tool_starts}
    assert tool_ids == {"call_a", "call_b"}
