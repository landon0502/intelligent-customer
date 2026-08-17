"""工具启停服务 —— 读取 tools 分类配置、更新启停并触发热更新。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.system_config import SystemConfig
from agent.tools import ALL_TOOL_NAMES
from agent.prompts import TOOL_DESCRIPTIONS
from services.config import get_configs_by_category

GUARDED_TOOLS = {"transfer_human", "clarify"}
_DEFAULT_STATE = "enabled"


class UnknownToolError(ValueError):
    """工具不存在。"""


class GuardedToolError(ValueError):
    """兜底工具不可禁用。"""


async def list_tool_states(db: AsyncSession) -> dict[str, str]:
    """读取 tools 分类，归一化 key 为工具名，返回 {工具名: enabled/disabled}。

    缺失项按默认 enabled 补齐（与 DEFAULT_CONFIGS 对齐，容忍脏数据）。
    """
    rows = await get_configs_by_category(db, "tools")
    states: dict[str, str] = {
        row.key.split(".", 1)[-1]: row.value
        for row in rows
        if row.key.startswith("tools.")
    }
    for name in ALL_TOOL_NAMES:
        states.setdefault(name, _DEFAULT_STATE)
    return states


async def update_tool_state(
    db: AsyncSession,
    name: str,
    enabled: bool,
    provider,
    registry,
) -> tuple[str, bool, bool]:
    """更新单个工具启停：写库 → invalidate("tools") → refresh("agent")。

    Args:
        db: 数据库会话
        name: 工具名（如 "ticket_submit"）
        enabled: 目标启用状态
        provider: AsyncConfigProvider 实例
        registry: ComponentRegistry 实例

    Returns:
        (name, enabled, refresh_ok)

    Raises:
        UnknownToolError: 工具名不在 ALL_TOOL_NAMES
        GuardedToolError: 兜底工具被禁用
    """
    if name not in ALL_TOOL_NAMES:
        raise UnknownToolError(f"工具不存在: {name}")
    if name in GUARDED_TOOLS and not enabled:
        raise GuardedToolError("兜底工具不可禁用")

    new_value = "enabled" if enabled else "disabled"
    key = f"tools.{name}"

    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        config.value = new_value
    else:
        db.add(
            SystemConfig(
                key=key,
                value=new_value,
                category="tools",
                description=TOOL_DESCRIPTIONS.get(name),
            )
        )
    await db.commit()

    provider.invalidate("tools")
    refresh_ok = await registry.refresh("agent")

    return name, enabled, refresh_ok
