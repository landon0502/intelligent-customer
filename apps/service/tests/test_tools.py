"""工具启停服务测试 —— tools 分类默认配置、启停读写与热更新。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.config import DEFAULT_CONFIGS


TOOL_NAMES = [
    "knowledge_base_query",
    "enterprise_query",
    "ticket_submit",
    "ticket_status",
    "transfer_human",
    "clarify",
]


def test_default_configs_has_six_tools_enabled():
    """tools 分类 6 项，value 均为 enabled。"""
    tool_cfgs = {
        k: v for k, v in DEFAULT_CONFIGS.items() if v["category"] == "tools"
    }
    assert len(tool_cfgs) == 6
    assert all(v["value"] == "enabled" for v in tool_cfgs.values())
    assert all(k.startswith("tools.") for k in tool_cfgs)


@pytest.mark.anyio
async def test_init_default_configs_inserts_tools_keys():
    """init_default_configs 对缺失的 tools 键执行插入，且不覆盖已有值。"""
    from services.config import init_default_configs

    db = AsyncMock()
    # 所有 key 的 scalar_one_or_none() 均为 None → 全部插入
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    await init_default_configs(db)

    added = [call.args[0] for call in db.add.call_args_list]
    tool_added = [c for c in added if c.category == "tools"]
    assert len(tool_added) == 6
    assert all(c.value == "enabled" for c in tool_added)
    assert all(c.key.startswith("tools.") for c in tool_added)


from services.tools import (
    list_tool_states,
    update_tool_state,
    UnknownToolError,
    GuardedToolError,
)
from agent.tools import ALL_TOOL_NAMES


def _config_row(key, value):
    row = MagicMock()
    row.key = key
    row.value = value
    return row


@pytest.mark.anyio
async def test_list_tool_states_reads_and_defaults_missing():
    """读取 tools 分类并归一化 key；缺失工具默认 enabled。"""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _config_row("tools.knowledge_base_query", "enabled"),
        _config_row("tools.ticket_submit", "disabled"),
    ]
    db.execute = AsyncMock(return_value=result)

    states = await list_tool_states(db)

    assert states["knowledge_base_query"] == "enabled"
    assert states["ticket_submit"] == "disabled"
    # 缺失（未入库）工具默认 enabled
    assert states["clarify"] == "enabled"
    assert set(states.keys()) == set(ALL_TOOL_NAMES)


@pytest.mark.anyio
async def test_update_tool_state_unknown_tool_raises():
    db = AsyncMock()
    provider = MagicMock()
    registry = AsyncMock()

    with pytest.raises(UnknownToolError):
        await update_tool_state(db, "no_such_tool", True, provider, registry)


@pytest.mark.anyio
async def test_update_tool_state_guarded_tool_disable_raises():
    db = AsyncMock()
    provider = MagicMock()
    registry = AsyncMock()

    with pytest.raises(GuardedToolError):
        await update_tool_state(db, "transfer_human", False, provider, registry)


@pytest.mark.anyio
async def test_update_tool_state_writes_invalidates_refreshes():
    """正常启停：写库 + invalidate("tools") + refresh("agent")。"""
    db = AsyncMock()
    existing = MagicMock()
    existing.value = "enabled"
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    db.commit = AsyncMock()
    provider = MagicMock()
    registry = AsyncMock()
    registry.refresh = AsyncMock(return_value=True)

    name, enabled, refresh_ok = await update_tool_state(
        db, "knowledge_base_query", False, provider, registry
    )

    assert (name, enabled, refresh_ok) == ("knowledge_base_query", False, True)
    assert existing.value == "disabled"
    db.commit.assert_called_once()
    provider.invalidate.assert_called_once_with("tools")
    registry.refresh.assert_called_once_with("agent")


@pytest.mark.anyio
async def test_update_tool_state_inserts_missing_key():
    """配置行不存在时插入（description 来自 TOOL_DESCRIPTIONS）。"""
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    provider = MagicMock()
    registry = AsyncMock()
    registry.refresh = AsyncMock(return_value=True)

    await update_tool_state(db, "clarify", True, provider, registry)

    inserted = [c.args[0] for c in db.add.call_args_list]
    assert len(inserted) == 1
    assert inserted[0].key == "tools.clarify"
    assert inserted[0].category == "tools"
    assert inserted[0].value == "enabled"


@pytest.mark.anyio
async def test_apply_config_changes_refreshes_agent_on_llm_change():
    """llm 分类变更时对称额外刷新 agent（agent slot 已解耦为 tools 分类）。"""
    from services.config import _apply_config_changes

    registry = AsyncMock()
    registry.refresh_category = AsyncMock(return_value={"agent_llm": True})
    registry.refresh = AsyncMock(return_value=True)

    result = await _apply_config_changes({"llm"}, registry)

    registry.refresh.assert_called_once_with("agent")
    assert result["llm"]["agent"] is True
