"""Agent 动态绑定与动态提示词单元测试。"""

import pytest
from unittest.mock import MagicMock, patch

from agent.tools import ALL_TOOLS, ALL_TOOL_NAMES
from agent.factory import filter_tools
from agent.prompts import build_system_prompt, SYSTEM_PROMPT, TOOL_DESCRIPTIONS


def test_all_tool_names_matches_all_tools():
    assert ALL_TOOL_NAMES == [t.name for t in ALL_TOOLS]
    assert set(ALL_TOOL_NAMES) == {
        "knowledge_base_query",
        "enterprise_query",
        "ticket_submit",
        "ticket_status",
        "transfer_human",
        "clarify",
    }


def test_tool_descriptions_covers_all_tools():
    assert set(TOOL_DESCRIPTIONS.keys()) == set(ALL_TOOL_NAMES)
    assert all(v for v in TOOL_DESCRIPTIONS.values())


def test_filter_tools_excludes_disabled():
    states = {n: "enabled" for n in ALL_TOOL_NAMES}
    states["ticket_submit"] = "disabled"
    enabled = filter_tools(states)
    names = [t.name for t in enabled]
    assert "ticket_submit" not in names
    assert len(names) == len(ALL_TOOL_NAMES) - 1


def test_filter_tools_missing_defaults_enabled():
    assert len(filter_tools({})) == len(ALL_TOOLS)


def test_build_system_prompt_excludes_disabled_tool_description_and_numbering():
    enabled_names = [n for n in ALL_TOOL_NAMES if n != "clarify"]
    prompt = build_system_prompt(enabled_names)
    # 描述与编号移除（PROMPT_FIXED 决策规则段的泛指引用保留，故不断言不含 "clarify"）
    assert "当用户意图不明确，需要追问澄清时使用" not in prompt
    assert "6. **clarify**" not in prompt
    # 启用子集连续编号
    assert "1. **knowledge_base_query**" in prompt
    assert "5. **transfer_human**" in prompt


def test_build_system_prompt_keeps_fixed_sections():
    prompt = build_system_prompt(ALL_TOOL_NAMES)
    assert "## 决策规则" in prompt
    assert "## 回答规范" in prompt
    assert "请严格按照此格式输出。" in prompt


def test_system_prompt_default_equals_full_build():
    assert SYSTEM_PROMPT == build_system_prompt(ALL_TOOL_NAMES)
    assert "6. **clarify**" in SYSTEM_PROMPT


def test_create_customer_agent_receives_injected_tools_and_prompt():
    """create_customer_agent 接收注入的过滤工具集与动态提示词。"""
    from agent.factory import create_customer_agent

    states = {n: "enabled" for n in ALL_TOOL_NAMES}
    states["ticket_submit"] = "disabled"
    enabled = filter_tools(states)
    prompt = build_system_prompt([t.name for t in enabled])
    mock_llm = MagicMock(name="llm")

    with patch("agent.factory.create_agent") as mock_create:
        mock_create.return_value = MagicMock(name="agent")
        create_customer_agent(mock_llm, tools=enabled, system_prompt=prompt)

    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["tools"] == enabled
    content = call_kwargs["system_prompt"].content
    # 禁用工具的「可用工具」段条目（描述与编号）移除；PROMPT_FIXED 决策规则段保留泛指引用，故不断言不含工具名
    assert "3. **ticket_submit**" not in content
    assert "当用户要求办理企业业务、提交申请时使用" not in content
