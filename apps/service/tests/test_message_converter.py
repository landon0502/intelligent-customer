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
        {"role": "user", "parts": [{"type": "text", "text": "退货政策是什么"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "退货政策是什么"


def test_assistant_message_text_only():
    """纯文本助手消息转换"""
    ui_messages = [
        {"role": "assistant", "parts": [{"type": "text", "text": "退货需在7天内"}]}
    ]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 1
    assert isinstance(result[0], AIMessage)
    assert result[0].content == "退货需在7天内"


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
    ui_messages = [{"role": "user", "parts": []}]
    result = ui_messages_to_langchain(ui_messages)
    assert len(result) == 0


def test_mixed_conversation():
    """完整对话序列转换"""
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
