"""UIMessage → LangChain 消息转换器测试。"""

import importlib.util
import os
import sys

import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


# 直接加载 message_converter 模块，绕过 services/__init__.py 的循环导入
_module_path = os.path.join(
    os.path.dirname(__file__), "..", "services", "message_converter.py"
)
_spec = importlib.util.spec_from_file_location(
    "services.message_converter", _module_path
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["services.message_converter"] = _mod
_spec.loader.exec_module(_mod)

ui_messages_to_langchain = _mod.ui_messages_to_langchain


def test_user_message_text_only():
    """纯文本用户消息转换"""
    ui_messages = [
        {"role": "user", "parts": [{"type": "text", "text": "企业开户需要什么材料"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "企业开户需要什么材料"


def test_assistant_message_text_only():
    """纯文本助手消息转换"""
    ui_messages = [
        {"role": "assistant", "parts": [{"type": "text", "text": "开户审核需3个工作日"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].content == "开户审核需3个工作日"


def test_assistant_message_with_tool_invocation():
    """助手消息含 tool-invocation part（legacy 格式）"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {"type": "text", "text": "让我查一下"},
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_1",
                    "args": {"query": "企业开户"},
                    "state": "result",
                    "result": "开户审核需3个工作日...",
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
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-knowledge_base_query",
                    "toolCallId": "call_2",
                    "args": {"query": "开户流程"},
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
    ui_messages = [{"role": "user", "parts": []}]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 0


def test_mixed_conversation():
    """完整对话序列转换"""
    ui_messages = [
        {"role": "user", "parts": [{"type": "text", "text": "查询企业业务"}]},
        {"role": "assistant", "parts": [{"type": "text", "text": "好的"}]},
        {"role": "user", "parts": [{"type": "text", "text": "业务编号B-001"}]},
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 3
    assert isinstance(result[0], HumanMessage)
    assert isinstance(result[1], AIMessage)
    assert isinstance(result[2], HumanMessage)


# ---- AI SDK 7.x 字段优先级与 state 处理测试 ----


def test_tool_args_prefers_input_over_args():
    """7.x 优先级：当 input 和 args 同时存在时，应优先取 input"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_input_priority",
                    "input": {"query": "7.x 查询"},
                    "args": {"query": "旧版查询"},
                    "state": "call",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    # input 应优先于 args
    assert result[0].tool_calls[0]["args"] == {"query": "7.x 查询"}


def test_tool_args_fallback_to_args_when_no_input():
    """7.x 回退：当 input 不存在时，应回退到 args"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_args_fallback",
                    "args": {"query": "旧版查询"},
                    "state": "call",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].tool_calls[0]["args"] == {"query": "旧版查询"}


def test_tool_result_prefers_output_over_result():
    """7.x 优先级：当 output 和 result 同时存在时，应优先取 output"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_output_priority",
                    "args": {"query": "企业开户"},
                    "state": "result",
                    "output": "7.x 输出结果",
                    "result": "旧版输出结果",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 2
    assert isinstance(result[1], ToolMessage)
    # output 应优先于 result
    assert result[1].content == "7.x 输出结果"


def test_tool_result_fallback_to_result_when_no_output():
    """7.x 回退：当 output 不存在时，应回退到 result"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_result_fallback",
                    "args": {"query": "企业开户"},
                    "state": "result",
                    "result": "旧版输出结果",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 2
    assert isinstance(result[1], ToolMessage)
    assert result[1].content == "旧版输出结果"


def test_output_error_state_creates_tool_message():
    """output-error state：工具执行出错时应转为 ToolMessage，content 为 errorText"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_error",
                    "input": {"query": "不存在的查询"},
                    "state": "output-error",
                    "errorText": "工具执行失败：数据库连接超时",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    # 应产生 AIMessage + ToolMessage
    assert len(result) == 2
    assert isinstance(result[0], AIMessage)
    assert result[0].tool_calls[0]["name"] == "knowledge_base_query"
    assert isinstance(result[1], ToolMessage)
    assert result[1].content == "工具执行失败：数据库连接超时"
    assert result[1].tool_call_id == "call_error"


def test_output_available_state_with_output_field():
    """output-available state：使用 output 字段的工具结果"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_output_avail",
                    "input": {"query": "开户流程"},
                    "state": "output-available",
                    "output": "开户审核需3个工作日",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 2
    assert isinstance(result[1], ToolMessage)
    assert result[1].content == "开户审核需3个工作日"


def test_input_available_state_creates_ai_message_only():
    """input-available state：工具参数已就绪但尚未执行，只产生 AIMessage 不产生 ToolMessage"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-invocation",
                    "toolName": "knowledge_base_query",
                    "toolCallId": "call_input_avail",
                    "input": {"query": "服务范围"},
                    "state": "input-available",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    # input-available 表示参数已就绪但尚未执行，只产生 AIMessage
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].tool_calls[0]["name"] == "knowledge_base_query"
    assert result[0].tool_calls[0]["args"] == {"query": "服务范围"}


def test_dynamic_tool_with_input_field():
    """动态格式 tool-{toolName} 使用 input 字段（7.x）"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-knowledge_base_query",
                    "toolCallId": "call_dynamic_input",
                    "input": {"query": "7.x 动态查询"},
                    "state": "call",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].tool_calls[0]["args"] == {"query": "7.x 动态查询"}


def test_dynamic_tool_output_error_state():
    """动态格式 tool-{toolName} 的 output-error state"""
    ui_messages = [
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool-knowledge_base_query",
                    "toolCallId": "call_dynamic_error",
                    "input": {"query": "失败查询"},
                    "state": "output-error",
                    "errorText": "动态工具执行失败",
                },
            ],
        }
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 2
    assert isinstance(result[1], ToolMessage)
    assert result[1].content == "动态工具执行失败"
