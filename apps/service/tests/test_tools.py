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
