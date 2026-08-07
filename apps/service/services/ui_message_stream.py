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
    started_tool_calls: set[str] = field(default_factory=set)
    partial_tool_inputs: dict[str, str] = field(default_factory=dict)
    """增量工具调用的累积输入文本，key 为 tool_call_id，value 为累积的 args 字符串。"""
    completed_tool_calls: set[str] = field(default_factory=set)
    """已发送 tool-input-available 的工具调用 ID 集合。"""
    step_started: bool = False
    stream_started: bool = False


def _new_id() -> str:
    """生成唯一 ID。"""
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
        # 对应的增量工具调用需要先发送 tool-input-available 标记输入完成
        tc_id = chunk.tool_call_id
        if tc_id in state.started_tool_calls and tc_id not in state.completed_tool_calls:
            accumulated = state.partial_tool_inputs.pop(tc_id, "")
            try:
                parsed_input = json.loads(accumulated) if accumulated else {}
                if not isinstance(parsed_input, dict):
                    parsed_input = {}
            except (json.JSONDecodeError, ValueError):
                parsed_input = {}
            state.completed_tool_calls.add(tc_id)
            yield {
                "type": "tool-input-available",
                "toolCallId": tc_id,
                "toolName": chunk.name or "",
                "input": parsed_input,
            }
        # 确保 output 是可 JSON 序列化的值
        output = chunk.content
        if not isinstance(output, (str, int, float, bool, list, dict, type(None))):
            output = str(output)
        yield {
            "type": "tool-output-available",
            "toolCallId": chunk.tool_call_id,
            "output": output,
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

    # LangChain 会自动从 tool_call_chunks 生成 tool_calls，反之亦然。
    # 区分增量 vs 完整模式的标准：
    # - 完整模式：tool_calls 的 args 为非空字典（已解析的完整参数）
    # - 增量模式：tool_calls 的 args 为空字典（LangChain 自动生成的占位），
    #   真实参数在 tool_call_chunks 的 args 字符串中
    is_incremental = False
    if has_tool_call_chunks:
        # 检查 tool_calls 的 args 是否为空字典（LangChain 自动生成的占位）
        if has_tool_calls:
            all_args_empty = all(
                isinstance(tc.get("args"), dict) and not tc.get("args")
                for tc in chunk.tool_calls
            )
            is_incremental = all_args_empty
        else:
            is_incremental = True

    if has_text:
        if not state.text_id:
            state.text_id = _new_id()
            yield {"type": "text-start", "id": state.text_id}
        yield {"type": "text-delta", "id": state.text_id, "delta": chunk.content}

        # 如果同时有工具调用，先关闭文本块
        if has_tool_calls or has_tool_call_chunks:
            yield {"type": "text-end", "id": state.text_id}
            state.text_id = ""

    # 2. 处理增量工具调用（tool_call_chunks 优先）
    if is_incremental:
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
            # 累积增量输入文本
            args_text = tcc.get("args", "")
            if args_text:
                state.partial_tool_inputs[tc_id] = state.partial_tool_inputs.get(tc_id, "") + args_text
            yield {
                "type": "tool-input-delta",
                "toolCallId": tc_id,
                "inputTextDelta": args_text,
            }

    # 3. 处理完整工具调用（tool_calls 的 args 为非空字典）
    elif has_tool_calls:
        for tc in chunk.tool_calls:
            tc_id = tc.get("id", _new_id())
            if tc_id not in state.started_tool_calls:
                state.started_tool_calls.add(tc_id)
                yield {
                    "type": "tool-input-start",
                    "toolCallId": tc_id,
                    "toolName": tc.get("name", ""),
                }
            state.completed_tool_calls.add(tc_id)
            yield {
                "type": "tool-input-available",
                "toolCallId": tc_id,
                "toolName": tc.get("name", ""),
                "input": tc.get("args", {}),
            }


async def finish_stream(state: StreamState) -> AsyncIterator[dict]:
    """发送流结束事件序列。

    Args:
        state: 流状态

    Yields:
        finish-step + finish 事件
    """
    # 关闭未关闭的文本块
    if state.text_id:
        yield {"type": "text-end", "id": state.text_id}
        state.text_id = ""

    # 对已 start 但未发送 tool-input-available 的增量工具调用补发
    pending_tool_ids = state.started_tool_calls - state.completed_tool_calls
    for tc_id in pending_tool_ids:
        accumulated = state.partial_tool_inputs.pop(tc_id, "")
        try:
            parsed_input = json.loads(accumulated) if accumulated else {}
            if not isinstance(parsed_input, dict):
                parsed_input = {}
        except (json.JSONDecodeError, ValueError):
            parsed_input = {}
        state.completed_tool_calls.add(tc_id)
        yield {
            "type": "tool-input-available",
            "toolCallId": tc_id,
            "input": parsed_input,
        }

    # 关闭未关闭的步骤
    if state.step_started:
        yield {"type": "finish-step"}

    yield {"type": "finish"}


async def error_stream(error_message: str, state: StreamState) -> AsyncIterator[dict]:
    """发送错误事件。

    先关闭未完成的文本块和步骤，再发送错误事件，
    避免前端状态不一致。

    Args:
        error_message: 错误消息文本
        state: 流状态

    Yields:
        关闭事件 + error 事件
    """
    # 关闭未关闭的文本块
    if state.text_id:
        yield {"type": "text-end", "id": state.text_id}
        state.text_id = ""

    # 关闭未关闭的步骤
    if state.step_started:
        yield {"type": "finish-step"}

    yield {"type": "error", "errorText": error_message}
