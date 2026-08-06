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
            yield {
                "type": "tool-input-delta",
                "toolCallId": tc_id,
                "inputTextDelta": tcc.get("args", ""),
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
            yield {
                "type": "tool-input-available",
                "toolCallId": tc_id,
                "toolName": tc.get("name", ""),
                "input": tc.get("args", {}),
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
