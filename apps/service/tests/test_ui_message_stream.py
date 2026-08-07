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
    async for event in finish_stream(state):
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
    async for event in finish_stream(state):
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


@pytest.mark.anyio
async def test_error_stream_closes_open_text_and_step():
    """error_stream 应先关闭未完成的文本块和步骤，再发送 error 事件。

    当流中途出错时，可能存在未关闭的 text_id 和 step_started，
    error_stream 应先关闭这些块再发送错误，避免前端状态不一致。
    """
    state = StreamState(message_id="msg-1", text_id="txt-err", step_started=True)
    events = []
    async for event in error_stream("连接超时", state):
        events.append(event)

    types = [e["type"] for e in events]
    # 应先关闭文本块和步骤，再发 error
    assert "text-end" in types
    assert "finish-step" in types
    assert "error" in types
    # 顺序：text-end → finish-step → error
    text_end_idx = next(i for i, e in enumerate(events) if e["type"] == "text-end")
    finish_step_idx = next(i for i, e in enumerate(events) if e["type"] == "finish-step")
    error_idx = next(i for i, e in enumerate(events) if e["type"] == "error")
    assert text_end_idx < finish_step_idx < error_idx


@pytest.mark.anyio
async def test_error_stream_no_open_text_no_text_end():
    """error_stream 无未关闭文本块时不发 text-end"""
    state = StreamState(message_id="msg-1", text_id="", step_started=True)
    events = []
    async for event in error_stream("连接超时", state):
        events.append(event)

    types = [e["type"] for e in events]
    assert "text-end" not in types
    assert "finish-step" in types
    assert "error" in types


@pytest.mark.anyio
async def test_finish_stream_no_full_response_param():
    """finish_stream 不再接受 full_response 参数"""
    import inspect
    sig = inspect.signature(finish_stream)
    param_names = list(sig.parameters.keys())
    assert "full_response" not in param_names, f"finish_stream 不应包含 full_response 参数，实际参数: {param_names}"


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
async def test_incremental_tool_call_sends_input_available_on_tool_message():
    """增量工具调用：收到 ToolMessage 时应发送 tool-input-available 标记输入完成。

    AI SDK 7.x 中 tool-input-start 将工具状态设为 input-streaming，
    只有 tool-input-available 才能将状态转为 input-available。
    缺少此事件会导致前端工具调用永远停留在 input-streaming 状态。
    """
    # 模拟增量工具调用：先发 tool_call_chunks，再发 ToolMessage
    chunk1 = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": '{"quer', "id": "call_inc1", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    chunk2 = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": 'y": "退货"}', "id": "call_inc1", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    tool_msg = ToolMessage(content="退货需在7天内", tool_call_id="call_inc1", name="kb_query")

    state = StreamState(message_id="msg-1")
    all_events = []
    for chunk in [chunk1, chunk2, tool_msg]:
        async for event in to_ui_message_stream_chunk(chunk, state):
            all_events.append(event)

    # 关键断言：ToolMessage 处理时应先发 tool-input-available
    available_events = [e for e in all_events if e["type"] == "tool-input-available" and e.get("toolCallId") == "call_inc1"]
    assert len(available_events) == 1, f"期望 1 个 tool-input-available 事件，实际 {len(available_events)}"
    # input 应从累积的增量文本解析
    assert available_events[0]["input"] == {"query": "退货"}
    # tool-input-available 应在 tool-output-available 之前
    available_idx = next(i for i, e in enumerate(all_events) if e["type"] == "tool-input-available" and e.get("toolCallId") == "call_inc1")
    output_idx = next(i for i, e in enumerate(all_events) if e["type"] == "tool-output-available" and e.get("toolCallId") == "call_inc1")
    assert available_idx < output_idx


@pytest.mark.anyio
async def test_incremental_tool_call_finish_stream_sends_input_available():
    """增量工具调用：finish_stream 应对未发送 tool-input-available 的工具调用补发。

    当流正常结束但工具调用尚未收到 ToolMessage 时（如 LLM 决定不调用工具），
    finish_stream 应补发 tool-input-available 以关闭 input-streaming 状态。
    使用不完整 JSON 的 args 确保 LangChain 生成空字典的 tool_calls（增量模式）。
    """
    chunk = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": '{"quer', "id": "call_inc2", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    state = StreamState(message_id="msg-1")
    all_events = []
    async for event in to_ui_message_stream_chunk(chunk, state):
        all_events.append(event)

    # 增量模式下不应有 tool-input-available（只有 start + delta）
    available_before = [e for e in all_events if e["type"] == "tool-input-available"]
    assert len(available_before) == 0

    # finish_stream 应补发 tool-input-available
    finish_events = []
    async for event in finish_stream(state):
        finish_events.append(event)

    available_after = [e for e in finish_events if e["type"] == "tool-input-available"]
    assert len(available_after) == 1, f"期望 1 个 tool-input-available 事件，实际 {len(available_after)}"
    assert available_after[0]["toolCallId"] == "call_inc2"
    # 不完整 JSON 解析失败，应使用空字典
    assert available_after[0]["input"] == {}


@pytest.mark.anyio
async def test_incremental_tool_call_input_parse_fallback():
    """增量工具调用：累积输入文本解析失败时使用空字典作为 input。"""
    chunk = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "kb_query", "args": '{"incomplete', "id": "call_inc3", "index": 0, "type": "tool_call_chunk"}
        ],
    )
    tool_msg = ToolMessage(content="结果", tool_call_id="call_inc3", name="kb_query")

    state = StreamState(message_id="msg-1")
    all_events = []
    for c in [chunk, tool_msg]:
        async for event in to_ui_message_stream_chunk(c, state):
            all_events.append(event)

    available_events = [e for e in all_events if e["type"] == "tool-input-available" and e.get("toolCallId") == "call_inc3"]
    assert len(available_events) == 1
    # 解析失败应使用空字典
    assert available_events[0]["input"] == {}


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
