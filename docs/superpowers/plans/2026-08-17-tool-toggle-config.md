---
change: tool-toggle-config
design-doc: docs/superpowers/specs/2026-08-17-tool-toggle-config-design.md
base-ref: 01e3ab6e25f06f19cd2c28d1e83eee142e307108
archived-with: 2026-08-17-tool-toggle-config
---

# 工具启停配置实施计划（tool-toggle-config）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 通过 `system_configs` 表的 `tools` 分类实现 6 个 Agent 工具的启停配置，Agent 按启用工具动态绑定工具集与动态系统提示词，新增 admin 专属 GET/PATCH 管理接口，前端 tools 页去掉 mock、对接真实接口并支持启停切换。

**架构：** 数据层复用现有 `system_configs` 表（`SystemConfig` ORM，key 唯一 + category 分类）；服务层新增 `services/tools.py` 读写 `tools` 分类；`AsyncConfigProvider`（Cache-Aside 按分类缓存）负责读配置；`ComponentRegistry` 事务性重建 `agent` 组件（失败保留旧实例）；`agent/prompts.py` 拆出 `TOOL_DESCRIPTIONS` + `build_system_prompt()` 实现动态提示词，`agent/factory.py` 新增 `filter_tools()`；`api/tools.py` 提供 GET/PATCH 接口；前端 `services/tools.ts` + `app/tools/useServices.ts` + `page.tsx` 去 mock 对接。

**技术栈：** 后端 `apps/service/`（FastAPI + SQLAlchemy async + LangChain + pytest + anyio）；前端 `apps/web/`（Next.js App Router + next-intl + ahooks useRequest + 自定义 fetchClient 封装）。

## 全局约束

- **key 前缀归一化（全变更最高优先级）**：`get_category("tools")` 返回的 key 是 `tools.<name>`，而 Agent/接口层按工具名 `<name>` 引用。所有消费点（`services/tools.py`、`app/lifespan.py`、`api/tools.py` 之下的读取逻辑）必须统一归一化 `{k.split(".", 1)[-1]: v for k, v in category.items()}`，不得混用两种命名。
- **提示词单一来源**：工具描述只定义在 `agent/prompts.py` 的 `TOOL_DESCRIPTIONS`，`SYSTEM_PROMPT = build_system_prompt(ALL_TOOL_NAMES)` 作为兼容默认（现有调用方不传 system_prompt 时行为不变）；禁用工具即从 `build_system_prompt` 输出的「可用工具」段移除其描述与编号。
- **`PROMPT_FIXED` 原文不动**：`## 决策规则` / `## 回答规范` / `## 回答格式要求` 按 Design D2 明确「原文不动」，其中对工具名的泛指引用（如"使用 clarify 追问"）保留；测试断言「禁用后不含该工具**描述与编号**」，不断言"不含工具名"。
- **兜底硬校验**：`GUARDED_TOOLS = {"transfer_human", "clarify"}` 后端拒绝禁用（防绕过），前端对应行开关置灰（UX）。
- **兼容默认**：`create_customer_agent(agent_llm, tools=None, system_prompt=None)` 签名保持不变，调用方注入过滤后的 `tools` 与动态 `system_prompt`。
- **热更新顺序固定**：写库 → `provider.invalidate("tools")` → `registry.refresh("agent")`，refresh 内缓存 miss 读库，失败保留旧实例。
- **测试命令**：后端 `cd apps/service && .venv/bin/python -m pytest tests/ -q`；前端 `pnpm typecheck`（仓库根，turbo 分发，web 侧 `tsc --noEmit`）。
- **commit 纪律**：每个 Task 验收后单独 commit，不得积攒。

## 文件结构

| 文件 | 动作 | 职责 |
|------|------|------|
| `apps/service/services/config.py` | 修改 | `DEFAULT_CONFIGS` 新增 tools 分类 6 项；`_apply_config_changes` 增加 llm→refresh(agent) |
| `apps/service/services/tools.py` | 新增 | `list_tool_states` / `update_tool_state` / `GUARDED_TOOLS` / 异常类型 |
| `apps/service/agent/prompts.py` | 修改 | `TOOL_DESCRIPTIONS` / `PROMPT_FIXED` / `build_system_prompt()` / `SYSTEM_PROMPT` 改为动态 |
| `apps/service/agent/factory.py` | 修改 | 新增 `filter_tools()` |
| `apps/service/agent/tools/__init__.py` | 修改 | 新增 `ALL_TOOL_NAMES` |
| `apps/service/app/lifespan.py` | 修改 | `_agent_factory` 闭包读 tools 分类；`register("agent", ..., "tools")` |
| `apps/service/api/tools.py` | 新增 | GET /api/tools + PATCH /api/tools/{name}（仅 admin） |
| `apps/service/api/__init__.py` | 修改 | 导出 `tools_router` |
| `apps/service/app/main.py` | 修改 | include `tools_router` |
| `apps/service/tests/test_tools.py` | 新增 | Task1/2/4-service 单测 |
| `apps/service/tests/test_agent_tools.py` | 新增 | Task3 单测 |
| `apps/service/tests/test_lifespan_agent.py` | 新增 | Task4 集成测试 |
| `apps/service/tests/test_tools_api.py` | 新增 | Task5 API 测试 |
| `apps/web/services/tools.ts` | 新增 | `ToolItem` / `getToolsApi` / `updateToolApi` |
| `apps/web/app/tools/useServices.ts` | 新增 | `useRequest` 加载 + toggle |
| `apps/web/app/tools/page.tsx` | 修改 | 去 mock、合并后端 name/enabled、兜底置灰 |
| `apps/web/messages/zh-CN.json` | 修改 | tools 新增错误/成功提示 |
| `apps/web/messages/en-US.json` | 修改 | tools 新增错误/成功提示 |

---

## Task 1: tools 分类默认配置（tasks.md 组1 Task1）

**Files:**
- Modify: `apps/service/services/config.py`（`DEFAULT_CONFIGS` 末尾追加）
- Test: `apps/service/tests/test_tools.py`（新建）

**Interfaces:**
- Consumes: `SystemConfig` ORM（`schemas/system_config.py`）；现有 `init_default_configs` 幂等实现。
- Produces: `DEFAULT_CONFIGS` 中 category=`tools` 的 6 项，key 格式 `tools.<工具名>`，value 固定 `enabled`，供 Task2 的 `list_tool_states` 作为默认回退对齐。

- [x] **Step 1: 写失败测试**

在 `apps/service/tests/test_tools.py` 中新增：

```python
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
```

- [x] **Step 2: 运行确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools.py -q`
Expected: FAIL —— `DEFAULT_CONFIGS` 中尚无 `tools` 分类，断言 6 项失败。

- [x] **Step 3: 实现默认配置**

在 `apps/service/services/config.py` 的 `DEFAULT_CONFIGS` 末尾追加（`# 向量数据库` 分组之后）：

```python
    # 工具启停（默认全启用；transfer_human / clarify 为兜底工具，后端禁止禁用）
    "tools.knowledge_base_query": {
        "value": "enabled",
        "category": "tools",
        "description": "知识库问答工具是否启用",
    },
    "tools.enterprise_query": {
        "value": "enabled",
        "category": "tools",
        "description": "企业业务查询工具是否启用",
    },
    "tools.ticket_submit": {
        "value": "enabled",
        "category": "tools",
        "description": "工单提交工具是否启用",
    },
    "tools.ticket_status": {
        "value": "enabled",
        "category": "tools",
        "description": "工单状态查询工具是否启用",
    },
    "tools.transfer_human": {
        "value": "enabled",
        "category": "tools",
        "description": "转人工工具是否启用（兜底，不可禁用）",
    },
    "tools.clarify": {
        "value": "enabled",
        "category": "tools",
        "description": "追问澄清工具是否启用（兜底，不可禁用）",
    },
```

`init_default_configs` 现有实现即"仅插入缺失键、不覆盖已有值"，**不改动**。

- [x] **Step 4: 运行确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools.py -q`
Expected: PASS（两个用例）。

- [x] **Step 5: Commit**

```bash
git add apps/service/services/config.py apps/service/tests/test_tools.py
git commit -m "feat(service): 新增 tools 分类默认启停配置（6 工具默认启用）"
```

---

## Task 2: 工具启停服务层（tasks.md 组1 Task2）

**Files:**
- Create: `apps/service/services/tools.py`
- Test: `apps/service/tests/test_tools.py`（追加）

**Interfaces:**
- Consumes: `ALL_TOOL_NAMES`（Task3 在 `agent/tools/__init__.py` 产出；Task2 内可先用 `[t.name for t in ALL_TOOLS]` 先行开发，Task3 落地后改为引用 `ALL_TOOL_NAMES`）；`TOOL_DESCRIPTIONS`（`agent/prompts.py`）；`get_configs_by_category`（`services/config.py`）。
- Produces:
  - `GUARDED_TOOLS: set[str]`
  - `class UnknownToolError(ValueError)`、`class GuardedToolError(ValueError)`（供 Task5 区分 40005/40004）
  - `async def list_tool_states(db) -> dict[str, str]`：`{工具名: "enabled"/"disabled"}`，缺失项默认 `enabled`
  - `async def update_tool_state(db, name, enabled, provider, registry) -> tuple[str, bool, bool]`：返回 `(name, enabled, refresh_ok)`；未知工具抛 `UnknownToolError`、兜底禁用抛 `GuardedToolError`。

- [x] **Step 1: 先补 `ALL_TOOL_NAMES`（Task3 依赖项，提前落地一行）**

在 `apps/service/agent/tools/__init__.py` 末尾追加：

```python
ALL_TOOL_NAMES = [t.name for t in ALL_TOOLS]
```

（`t.name` 为 LangChain StructuredTool / @tool 装饰函数的工具名。）

- [x] **Step 2: 写失败测试**

在 `apps/service/tests/test_tools.py` 追加：

```python
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
```

- [x] **Step 3: 运行确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools.py -q`
Expected: FAIL —— `from services.tools import ...` ImportError。

- [x] **Step 4: 实现 `services/tools.py`**

```python
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
```

> 说明：`services/tools.py` 顶层的 import 链为 `services.tools → agent.prompts → agent.tools → 各 tool 模块`，tool 模块不反向 import 本模块，无循环依赖。

- [x] **Step 5: 运行确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools.py -q`
Expected: PASS（新增 5 个用例 + Task1 2 个用例）。

- [x] **Step 6: Commit**

```bash
git add apps/service/services/tools.py apps/service/tests/test_tools.py apps/service/agent/tools/__init__.py
git commit -m "feat(service): 新增工具启停服务层 list_tool_states/update_tool_state"
```

---

## Task 3: Agent 动态绑定与动态提示词（tasks.md 组1 Task3）

**Files:**
- Modify: `apps/service/agent/prompts.py`
- Modify: `apps/service/agent/factory.py`
- Test: `apps/service/tests/test_agent_tools.py`（新建）

**Interfaces:**
- Consumes: `ALL_TOOLS`、`ALL_TOOL_NAMES`（`agent/tools/__init__.py`）。
- Produces:
  - `TOOL_DESCRIPTIONS: dict[str, str]`（name → 描述，6 项）
  - `PROMPT_FIXED: str`（`## 决策规则` / `## 回答规范` / `## 回答格式要求` 原文）
  - `build_system_prompt(enabled_names: list[str]) -> str`
  - `SYSTEM_PROMPT = build_system_prompt(ALL_TOOL_NAMES)`（兼容默认）
  - `filter_tools(tool_states: dict[str, str]) -> list`（`agent/factory.py`）
  - 供 Task4 的 lifespan `_agent_factory` 使用。

- [x] **Step 1: 写失败测试**

在 `apps/service/tests/test_agent_tools.py` 中写入：

```python
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
    assert "ticket_submit" not in content
    assert "当用户要求办理企业业务、提交申请时使用" not in content
```

- [x] **Step 2: 运行确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_agent_tools.py -q`
Expected: FAIL —— `build_system_prompt` / `filter_tools` / `TOOL_DESCRIPTIONS` 尚未定义。

- [x] **Step 3: 重写 `agent/prompts.py`**

整文件替换为：

```python
"""Agent Prompt 模板 —— 定义系统提示词和角色设定。

工具描述集中在 TOOL_DESCRIPTIONS（单一来源），禁用工具即从
build_system_prompt 生成的「可用工具」段移除其描述与编号。
"""

from agent.tools import ALL_TOOL_NAMES

TOOL_DESCRIPTIONS: dict[str, str] = {
    "knowledge_base_query": "当用户询问业务流程、办理条件、服务规范、常见问题等知识性问题时使用",
    "enterprise_query": "当用户提供业务编号或询问企业业务流程、办理条件时使用",
    "ticket_submit": "当用户要求办理企业业务、提交申请时使用",
    "ticket_status": "当用户询问办理进度、工单状态时使用",
    "transfer_human": "当你判断无法处理或需要人工介入时使用",
    "clarify": "当用户意图不明确，需要追问澄清时使用",
}

PROMPT_FIXED = """\
## 决策规则

- **优先判断是否涉及企业业务**：如果用户提到业务编号或要求办理业务（提交申请、查询进度），使用 enterprise_query、ticket_submit 或 ticket_status
- **知识性问题**：如果用户询问政策、规则、服务规范等，使用 knowledge_base_query
- **意图不明确**：如果无法确定用户想要什么，使用 clarify 追问
- **转人工兜底**：连续两次无法确定意图后，使用 transfer_human 转人工
- **闲聊直接回复**：打招呼、寒暄、简单问答等可以直接回复，无需调用工具

## 回答规范

- 语气友好、专业，使用"您"称呼用户
- 回答简洁明了，重点信息加粗
- 涉及操作结果时，给出明确的下一步指引
- 引用知识库内容时，在回答末尾标注来源

## 回答格式要求：

回答必须严格遵循 Markdown CommonMark 规范：
要求：
- 标题必须使用 # 或者多级 # 为开头，标识符和标题间需要有一个空格，例：一级标题为 # 标题；二级标题 ## 标题；三级标题：### 标题；依次类推，最多6级
- 标题和正文之间必须空一行
- 列表必须使用 - 或 1. 开头
- 表格必须符合 GitHub Flavored Markdown(GFM)
- 表格前后必须有空行
- 表格必须单独占一行
- 不允许输出 HTML 标签
- 不允许混合 Markdown 和普通文本格式
- 不输出 ```markdown 包裹整个回答
- 代码必须使用代码块
- 每个 Markdown 元素必须完整输出

示例：

## 查询结果

| 业务编号 | 业务名称 | 办理说明 |
| --- | --- | --- |
| B-001 | 企业开户 | 需提供营业执照及法人身份证件 |

请严格按照此格式输出。
"""


def build_system_prompt(enabled_names: list[str]) -> str:
    """按启用工具动态生成系统提示词。

    Args:
        enabled_names: 启用的工具名列表（按此顺序编号）

    Returns:
        完整系统提示词：引言 + 「可用工具及适用场景」动态段 + 固定段。
    """
    header = (
        "你是一个专业、友好的智能客服助手，服务于企业客户的智能客服。"
        "你需要根据用户的问题选择合适的工具来提供帮助，或直接回复简单问题。"
    )
    tool_lines = [
        f"{i}. **{name}** — {TOOL_DESCRIPTIONS.get(name, '')}"
        for i, name in enumerate(enabled_names, start=1)
    ]
    tool_block = "\n".join(tool_lines)
    return "\n\n".join([header, "## 可用工具及适用场景", tool_block, PROMPT_FIXED])


SYSTEM_PROMPT = build_system_prompt(ALL_TOOL_NAMES)
```

- [x] **Step 4: 在 `agent/factory.py` 新增 `filter_tools`**

```python
def filter_tools(tool_states: dict[str, str]) -> list:
    """从 ALL_TOOLS 过滤出启用工具（缺失状态按 enabled 处理）。"""
    return [t for t in ALL_TOOLS if tool_states.get(t.name, "enabled") == "enabled"]
```

`create_customer_agent` 保持不动（签名已支持注入 `tools` / `system_prompt`）。

- [x] **Step 5: 运行确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_agent_tools.py tests/test_tools.py -q`
Expected: PASS。

- [x] **Step 6: Commit**

```bash
git add apps/service/agent/prompts.py apps/service/agent/factory.py apps/service/tests/test_agent_tools.py
git commit -m "feat(agent): 动态系统提示词 build_system_prompt + filter_tools 过滤启用工具"
```

---

## Task 4: lifespan 接线与 llm 变更对称刷新（tasks.md 组1 Task4）

**Files:**
- Modify: `apps/service/app/lifespan.py`
- Modify: `apps/service/services/config.py`（`_apply_config_changes`）
- Test: `apps/service/tests/test_lifespan_agent.py`（新建）+ `apps/service/tests/test_tools.py`（追加 1 例）

**Interfaces:**
- Consumes: `filter_tools`（Task3）、`build_system_prompt`（Task3）、`create_customer_agent`（现有）。
- Produces:
  - `app/lifespan.py`：`_agent_factory(config)` 闭包按 `config`（tools 分类，key 含 `tools.` 前缀）归一化 → `filter_tools` → `build_system_prompt` → `create_customer_agent(agent_llm, tools=enabled, system_prompt=system_prompt)`；`registry.register("agent", _agent_factory, "tools")`。
  - `services/config.py` `_apply_config_changes`：`llm` 分类变更时额外 `refresh("agent")`（对称 embedding→vectorstore 先例）。

- [x] **Step 1: 写失败测试（集成：真实 `_register_components`）**

在 `apps/service/tests/test_lifespan_agent.py` 写入：

```python
"""lifespan 组件接线集成测试 —— agent slot 绑定 tools 分类并动态绑定工具。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from configs.registry import ComponentRegistry
from app.lifespan import _register_components

# 覆盖 6 个分类的同一份 mock 配置（各 factory 已 patch）
_MOCK_CONFIG = {
    "llm.model": "deepseek-v4-pro",
    "tools.knowledge_base_query": "enabled",
    "tools.enterprise_query": "enabled",
    "tools.ticket_submit": "disabled",
    "tools.ticket_status": "enabled",
    "tools.transfer_human": "enabled",
    "tools.clarify": "enabled",
}


@pytest.mark.anyio
async def test_lifespan_agent_slot_binds_tools_and_filters_disabled():
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value=dict(_MOCK_CONFIG))
    registry = ComponentRegistry(mock_provider)

    mock_llm = MagicMock(name="agent_llm")
    mock_agent = MagicMock(name="agent")

    with (
        patch("models.factory.create_agent_llm", return_value=mock_llm),
        patch("models.factory.create_rag_llm", return_value=MagicMock()),
        patch("models.embedding.create_embeddings", return_value=MagicMock()),
        patch(
            "rag.ingestion.vectorstore.create_chroma_client",
            return_value=MagicMock(),
        ),
        patch(
            "rag.ingestion.vectorstore.create_vectorstore",
            return_value=MagicMock(),
        ),
        patch(
            "agent.factory.create_customer_agent",
            return_value=mock_agent,
        ) as mock_create,
    ):
        _register_components(registry)
        agent = await registry.ensure_initialized("agent")

    assert agent is mock_agent
    # agent slot 绑定 tools 分类
    assert registry._slots["agent"]._config_category == "tools"

    # 注入 create_customer_agent 的工具集不含 ticket_submit
    call_kwargs = mock_create.call_args[1]
    enabled_names = [t.name for t in call_kwargs["tools"]]
    assert "ticket_submit" not in enabled_names
    assert len(enabled_names) == 5
    # 动态提示词不含 ticket_submit 描述
    assert "当用户要求办理企业业务、提交申请时使用" not in call_kwargs["system_prompt"].content
```

> 说明：`_register_components` 函数体内 `from agent.factory import create_customer_agent` 等是按调用时模块属性解析的，因此 `patch("agent.factory.create_customer_agent")` 等生效。

在 `apps/service/tests/test_tools.py` 追加 `_apply_config_changes` 用例：

```python
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
```

- [x] **Step 2: 运行确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_lifespan_agent.py tests/test_tools.py -q`
Expected: FAIL —— agent 仍注册为 `llm` 分类、`_apply_config_changes` 无 llm 对称刷新。

- [x] **Step 3: 改 `app/lifespan.py`**

在 `_register_components` 中：

1. 顶部 import 追加（注意 `create_customer_agent` 已有 import）：

```python
    from agent.factory import create_customer_agent, filter_tools
    from agent.prompts import build_system_prompt
```

2. 将第 6 段 `_agent_factory` 与注册替换为：

```python
    # 6. agent — config_category: tools
    #    factory 需要已创建的 agent_llm + tools 分类配置；
    #    config 是 tools 分类配置（key 含 "tools." 前缀），归一化后过滤启用工具。
    def _agent_factory(config: dict):
        agent_llm = registry.get("agent_llm")
        states = {k.split(".", 1)[-1]: v for k, v in config.items()}
        enabled = filter_tools(states)
        system_prompt = build_system_prompt([t.name for t in enabled])
        return create_customer_agent(
            agent_llm, tools=enabled, system_prompt=system_prompt
        )

    registry.register("agent", _agent_factory, "tools")
```

- [x] **Step 4: 改 `services/config.py` `_apply_config_changes`**

在现有 `# 特殊处理：embedding 变更时额外刷新 vectorstore` 块之后追加：

```python
    # 特殊处理：llm 变更时额外刷新 agent
    # agent slot 的 config_category 已改为 tools，单纯 refresh_category("llm")
    # 不再覆盖 agent；agent 内部持有 agent_llm 引用，需显式重建拿到新 LLM。
    if "llm" in categories:
        agent_refresh = await registry.refresh("agent")
        result.setdefault("llm", {})["agent"] = agent_refresh
        if agent_refresh:
            logger.info("llm 变更后 agent 刷新成功")
        else:
            logger.warning("llm 变更后 agent 刷新失败（旧组件继续服务）")
```

- [x] **Step 5: 运行确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_lifespan_agent.py tests/test_tools.py -q`
Expected: PASS。

- [x] **Step 6: Commit**

```bash
git add apps/service/app/lifespan.py apps/service/services/config.py apps/service/tests/test_lifespan_agent.py apps/service/tests/test_tools.py
git commit -m "feat(service): agent slot 绑定 tools 分类，llm 变更对称刷新 agent"
```

---

## Task 5: api/tools.py 接口与路由注册（tasks.md 组2 Task5）

**Files:**
- Create: `apps/service/api/tools.py`
- Modify: `apps/service/api/__init__.py`
- Modify: `apps/service/app/main.py`
- Test: `apps/service/tests/test_tools_api.py`（新建）

**Interfaces:**
- Consumes: `list_tool_states` / `update_tool_state` / `UnknownToolError` / `GuardedToolError`（Task2）；`TOOL_DESCRIPTIONS`（Task3）；`get_config_provider` / `get_registry`（`app/dependencies.py`）；`get_current_user`（`auth/security.py`）。
- Produces:
  - `GET /api/tools`（admin）：`{ code: 0, data: [{ name, description, enabled }, ...] }`；非 admin → `error(40003)`
  - `PATCH /api/tools/{name}`（admin）：body `{enabled: bool}`；成功 → `{ name, enabled, refresh_ok }`；兜底禁用 → 40004；未知工具 → 40005；非 admin → 40003
  - `api/__init__.py` 导出 `tools_router`；`app/main.py` include。

- [x] **Step 1: 写失败测试**

在 `apps/service/tests/test_tools_api.py` 写入：

```python
"""api/tools 接口测试 —— admin 权限、错误码映射。"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.tools import router as tools_router
from database.session import get_db
from auth.security import get_current_user
from app.dependencies import get_config_provider, get_registry
from services.tools import UnknownToolError, GuardedToolError


def _make_client(role="admin"):
    """构造仅挂载 tools 路由的测试应用，override 鉴权/DB/依赖。"""
    app = FastAPI()
    app.include_router(tools_router)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = role
    mock_db = AsyncMock()

    def _override_user():
        return mock_user

    def _override_db():
        yield mock_db

    def _override_provider():
        return MagicMock()

    def _override_registry():
        return MagicMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_config_provider] = _override_provider
    app.dependency_overrides[get_registry] = _override_registry

    return TestClient(app)


def test_get_rejects_non_admin():
    resp = _make_client("user").get("/api/tools")
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_patch_rejects_non_admin():
    resp = _make_client("user").patch(
        "/api/tools/knowledge_base_query", json={"enabled": False}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_get_success():
    client = _make_client("admin")
    with patch(
        "api.tools.list_tool_states",
        new=AsyncMock(
            return_value={"knowledge_base_query": "enabled", "clarify": "enabled"}
        ),
    ):
        resp = client.get("/api/tools")

    assert resp.json()["code"] == 0
    items = resp.json()["data"]
    assert items[0]["name"] == "knowledge_base_query"
    assert items[0]["enabled"] is True
    assert items[0]["description"]  # 来自 TOOL_DESCRIPTIONS


def test_patch_success():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        new=AsyncMock(return_value=("knowledge_base_query", False, True)),
    ):
        resp = client.patch(
            "/api/tools/knowledge_base_query", json={"enabled": False}
        )

    assert resp.json()["code"] == 0
    assert resp.json()["data"] == {
        "name": "knowledge_base_query",
        "enabled": False,
        "refresh_ok": True,
    }


def test_patch_guarded_disable_returns_40004():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        side_effect=GuardedToolError("兜底工具不可禁用"),
    ):
        resp = client.patch("/api/tools/transfer_human", json={"enabled": False})

    assert resp.status_code == 200
    assert resp.json()["code"] == 40004


def test_patch_unknown_tool_returns_40005():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        side_effect=UnknownToolError("工具不存在: xxx"),
    ):
        resp = client.patch("/api/tools/xxx", json={"enabled": True})

    assert resp.status_code == 200
    assert resp.json()["code"] == 40005
```

- [x] **Step 2: 运行确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools_api.py -q`
Expected: FAIL —— `api/tools` 模块不存在。

- [x] **Step 3: 实现 `api/tools.py`**

```python
"""工具启停接口 —— 列表与启停切换（仅管理员）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from auth.security import get_current_user
from services.tools import (
    list_tool_states,
    update_tool_state,
    UnknownToolError,
    GuardedToolError,
)
from agent.prompts import TOOL_DESCRIPTIONS
from app.dependencies import get_config_provider, get_registry
from utils.response import success, error

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolUpdateRequest(BaseModel):
    enabled: bool


@router.get("")
async def list_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取工具启停状态列表（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工具")
    states = await list_tool_states(db)
    items = [
        {
            "name": name,
            "description": TOOL_DESCRIPTIONS.get(name, ""),
            "enabled": value == "enabled",
        }
        for name, value in states.items()
    ]
    return success(data=items)


@router.patch("/{name}")
async def update_tool(
    name: str,
    req: ToolUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider=Depends(get_config_provider),
    registry=Depends(get_registry),
):
    """启停工具（管理员权限）—— 兜底禁用 40004、未知工具 40005"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可修改工具")
    try:
        tool_name, enabled, refresh_ok = await update_tool_state(
            db, name, req.enabled, provider, registry
        )
    except GuardedToolError as e:
        return error(code=40004, message=str(e))
    except UnknownToolError as e:
        return error(code=40005, message=str(e))
    return success(
        data={"name": tool_name, "enabled": enabled, "refresh_ok": refresh_ok}
    )
```

- [x] **Step 4: 注册路由**

`apps/service/api/__init__.py` 末尾追加：

```python
from .tools import router as tools_router
```

`apps/service/app/main.py`：

1. 第 7 行 import 追加 `tools_router`：

```python
from api import health_router, auth_router, chat_router, conversations_router, knowledge_router, config_router, enterprise_router, tickets_router, users_router, tools_router
```

2. 末尾 `app.include_router(tools_router)`：

```python
app.include_router(users_router)
app.include_router(tools_router)
```

- [x] **Step 5: 运行确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_tools_api.py -q`
Expected: PASS（6 个用例）。

- [x] **Step 6: Commit**

```bash
git add apps/service/api/tools.py apps/service/api/__init__.py apps/service/app/main.py apps/service/tests/test_tools_api.py
git commit -m "feat(api): 新增 /api/tools GET/PATCH 管理接口（仅 admin，40004/40005 错误码）"
```

---

## Task 6: 前端 services 与 useServices（tasks.md 组2 Task6）

**Files:**
- Create: `apps/web/services/tools.ts`
- Create: `apps/web/app/tools/useServices.ts`

**Interfaces:**
- Consumes: `fetchClient`（`apps/web/lib/fetch`，支持 `get`/`patch`，返回 `{ code, message, data }`）。
- Produces:
  - `ToolItem { name: string; description: string; enabled: boolean }`
  - `ToolUpdateResult { name: string; enabled: boolean; refresh_ok: boolean }`
  - `getToolsApi(): Promise<ApiResponse<ToolItem[]>>`（GET /tools）
  - `updateToolApi(name: string, enabled: boolean): Promise<ApiResponse<ToolUpdateResult>>`（PATCH /tools/{name}）
  - `useToolServices()`：`listControl` / `tools` / `toggleControl` / `toggleTool(name, enabled)`
  - 供 Task7 的 `page.tsx` 消费。

- [x] **Step 1: 创建 `apps/web/services/tools.ts`**

```ts
import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface ToolItem {
  name: string
  description: string
  enabled: boolean
}

export interface ToolUpdateResult {
  name: string
  enabled: boolean
  refresh_ok: boolean
}

// ========== 工具启停接口 ==========

export async function getToolsApi() {
  return fetchClient.get<ToolItem[]>("/tools")
}

export async function updateToolApi(name: string, enabled: boolean) {
  return fetchClient.patch<ToolUpdateResult>(`/tools/${name}`, { enabled })
}
```

- [x] **Step 2: 创建 `apps/web/app/tools/useServices.ts`**（沿用 `app/users/useServices.ts` 的 ahooks 模式）

```ts
import { useRequest } from "ahooks";
import { useMemo } from "react";
import { getToolsApi, updateToolApi, type ToolItem } from "@/services/tools";

export default function useToolServices() {
  // 工具列表（自动模式：挂载首拉；切换后手动重拉）
  const listControl = useRequest(getToolsApi, {});
  const { data: listData } = listControl;
  const tools = useMemo(() => listData?.data ?? [], [listData]);

  // 启停切换
  const toggleControl = useRequest(
    async (name: string, enabled: boolean) => updateToolApi(name, enabled),
    { manual: true },
  );

  async function toggleTool(name: string, enabled: boolean) {
    await toggleControl.runAsync(name, enabled);
    await listControl.run();
  }

  return {
    listControl,
    tools,
    toggleControl,
    toggleTool,
  };
}
```

- [x] **Step 3: typecheck**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer && pnpm typecheck`
Expected: PASS，无本文件新增错误（`pnpm typecheck` 经 turbo 分发到 web 的 `tsc --noEmit`）。

- [x] **Step 4: Commit**

```bash
git add apps/web/services/tools.ts apps/web/app/tools/useServices.ts
git commit -m "feat(web): 新增 tools 接口封装与 useToolServices 启停 hook"
```

---

## Task 7: page.tsx 去 mock 与 i18n（tasks.md 组2 Task7）

**Files:**
- Modify: `apps/web/app/tools/page.tsx`
- Modify: `apps/web/messages/zh-CN.json`
- Modify: `apps/web/messages/en-US.json`

**Interfaces:**
- Consumes: `useToolServices()`（Task6，返回 `tools` / `toggleTool`）；后端 GET 返回的 `ToolItem[]`（`name`/`description`/`enabled`）。
- Produces: 去 mock 后的 tools 页：静态 `toolMeta` 元数据（i18n 键 + implemented）与后端 `name`/`enabled` 合并渲染；开关调 PATCH；`transfer_human`/`clarify` 行开关置灰。

- [x] **Step 1: 写失败（typecheck）先行验证点**：无独立测试框架，本 Task 以 `pnpm typecheck` + 本地渲染验证作为验收。

- [x] **Step 2: 替换 `apps/web/app/tools/page.tsx`**

整文件替换为：

```tsx
"use client"

import { useCallback, useState } from "react"
import { useTranslations } from "next-intl"
import { Search, Wrench, ToggleLeft, ToggleRight } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import useToolServices from "./useServices"

// 前端静态展示元数据（i18n 键映射 + 实现标记），与后端返回的 name/enabled 合并渲染
interface ToolMeta {
  triggerKey: string
  inputKey: string | null
  outputKey: string
  implemented: boolean
}

const toolMeta: Record<string, ToolMeta> = {
  knowledge_base_query: {
    triggerKey: "toolTriggerKnowledge",
    inputKey: "toolInputQuestion",
    outputKey: "toolOutputChunks",
    implemented: true,
  },
  enterprise_query: {
    triggerKey: "toolTriggerEnterprise",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputBusinessInfo",
    implemented: true,
  },
  ticket_submit: {
    triggerKey: "toolTriggerSubmit",
    inputKey: "toolInputSubmit",
    outputKey: "toolOutputTicket",
    implemented: true,
  },
  ticket_status: {
    triggerKey: "toolTriggerStatus",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputTicket",
    implemented: true,
  },
  transfer_human: {
    triggerKey: "toolTriggerHuman",
    inputKey: null,
    outputKey: "toolOutputNotify",
    implemented: true,
  },
  clarify: {
    triggerKey: "toolTriggerClarify",
    inputKey: null,
    outputKey: "toolOutputQuestion",
    implemented: true,
  },
}

// 兜底工具：后端硬校验不可禁用，前端行开关置灰
const GUARDED_TOOLS = new Set(["transfer_human", "clarify"])

export default function ToolsPage() {
  const t = useTranslations("tools")
  const { tools, toggleTool } = useToolServices()

  const [searchQuery, setSearchQuery] = useState("")

  const filteredTools = tools.filter(
    (tool) =>
      !searchQuery ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleToggle = useCallback(
    async (name: string, enabled: boolean) => {
      try {
        await toggleTool(name, enabled)
        toast.success(t("toggleSuccess"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [toggleTool, t]
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("toolCount", { count: tools.length })} ·{" "}
            {t("enabledCount", {
              count: tools.filter((tool) => tool.enabled).length,
            })}
          </p>
        </div>
        <div className="relative">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t("searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-60 pl-9"
          />
        </div>
      </div>

      {/* 工具表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("colName")}</TableHead>
                <TableHead>{t("colTrigger")}</TableHead>
                <TableHead>{t("colInput")}</TableHead>
                <TableHead>{t("colOutput")}</TableHead>
                <TableHead>{t("colImplemented")}</TableHead>
                <TableHead>{t("colStatus")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTools.map((tool) => {
                const meta = toolMeta[tool.name]
                const isGuarded = GUARDED_TOOLS.has(tool.name)
                return (
                  <TableRow key={tool.name}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Wrench className="size-4 text-muted-foreground" />
                        <code className="text-sm">{tool.name}</code>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      {meta
                        ? t(meta.triggerKey as Parameters<typeof t>[0])
                        : tool.description}
                    </TableCell>
                    <TableCell className="text-sm">
                      {meta?.inputKey
                        ? t(meta.inputKey as Parameters<typeof t>[0])
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {meta
                        ? t(meta.outputKey as Parameters<typeof t>[0])
                        : "—"}
                    </TableCell>
                    <TableCell>
                      {meta?.implemented ? (
                        <Badge
                          variant="default"
                          className="bg-green-100 text-green-700 hover:bg-green-100"
                        >
                          {t("implemented")}
                        </Badge>
                      ) : (
                        <Badge
                          variant="secondary"
                          className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
                        >
                          {t("simulated")}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={tool.enabled ? "default" : "outline"}
                        className={
                          tool.enabled
                            ? "bg-primary/10 text-primary hover:bg-primary/10"
                            : ""
                        }
                      >
                        {tool.enabled ? t("enabled") : t("disabled")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isGuarded}
                        title={isGuarded ? t("guardedToolTip") : undefined}
                        onClick={() => handleToggle(tool.name, !tool.enabled)}
                      >
                        {tool.enabled ? (
                          <>
                            <ToggleRight className="mr-1 size-4 text-primary" />
                            {t("disable")}
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="mr-1 size-4 text-muted-foreground" />
                            {t("enable")}
                          </>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [x] **Step 3: 补充 i18n**

在 `apps/web/messages/zh-CN.json` 的 `"tools"` 对象末尾（`"toolOutputQuestion"` 之后）追加：

```json
    "toggleSuccess": "工具状态已更新",
    "guardedToolTip": "兜底工具不可禁用",
    "toggleFailed": "操作失败，请重试"
```

在 `apps/web/messages/en-US.json` 的 `"tools"` 对象末尾（`"toolOutputQuestion"` 之后）追加：

```json
    "toggleSuccess": "Tool status updated",
    "guardedToolTip": "Guarded tools cannot be disabled",
    "toggleFailed": "Operation failed, please retry"
```

（注意 JSON 末尾逗号规则：`"toolOutputQuestion"` 与新增键之间加逗号，最后一项不带逗号。）

- [x] **Step 4: typecheck + 本地验证**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer && pnpm typecheck`
Expected: PASS。

本地验证（后端已可运行 + 前端 dev）：`cd apps/web && pnpm dev`，admin 登录后进入「工具配置」页：
- 列表真实渲染 6 个工具，状态来自 GET /api/tools
- 点击某工具开关 → 调 PATCH → 成功 toast + 列表刷新
- `transfer_human` / `clarify` 两行开关置灰不可点（hover 显示「兜底工具不可禁用」）

- [x] **Step 5: Commit**

```bash
git add apps/web/app/tools/page.tsx apps/web/messages/zh-CN.json apps/web/messages/en-US.json
git commit -m "feat(web): tools 页去 mock 对接真实接口，兜底工具置灰"
```

---

## Task 8: 全量测试与端到端验证（tasks.md 组3 Task8）

**Files:** 无新增/修改（验证类任务）。

**Interfaces:** 承接 Task1-7 全部产物。

- [x] **Step 1: 后端全量测试**

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全量通过（含新增 `test_tools.py` / `test_agent_tools.py` / `test_lifespan_agent.py` / `test_tools_api.py` 用例，且既有用例不回归——尤其 `SYSTEM_PROMPT` 重构后 `test_chat_endpoint.py` 等仍通过）。

- [x] **Step 2: 前端构建**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer && npm run build`
Expected: turbo build 成功（含 `/tools` 路由）。

- [x] **Step 3: 端到端验证（admin 登录）**

启动后端：`cd apps/service && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001`

```bash
# 1. 管理员登录（密码取 .env 的 ADMIN_PASSWORD，默认 admin123456）
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123456"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["token"])')

# 2. GET /api/tools：返回 6 个工具，全部 enabled
curl -s http://localhost:8001/api/tools -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
#   期望：code=0，data 含 6 项，name/description/enabled 齐全且 enabled 均为 true

# 3. PATCH 禁用 knowledge_base_query → code=0, data={name, enabled:false, refresh_ok:true}
curl -s -X PATCH http://localhost:8001/api/tools/knowledge_base_query \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled": false}' | python3 -m json.tool

# 4. 再次 GET：knowledge_base_query.enabled=false，状态已持久化
curl -s http://localhost:8001/api/tools -H "Authorization: Bearer $TOKEN" | python3 -c \
  'import sys,json;print([i for i in json.load(sys.stdin)["data"] if i["name"]=="knowledge_base_query"])'

# 5. PATCH 禁用 transfer_human → code=40004（兜底工具不可禁用）
curl -s -X PATCH http://localhost:8001/api/tools/transfer_human \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled": false}' | python3 -m json.tool

# 6. PATCH 未知工具 → code=40005
curl -s -X PATCH http://localhost:8001/api/tools/not_a_tool \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled": true}' | python3 -m json.tool

# 7. 恢复 knowledge_base_query 为 enabled
curl -s -X PATCH http://localhost:8001/api/tools/knowledge_base_query \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled": true}' | python3 -m json.tool
```

热更新验证：Task4 的集成测试已断言 `registry.refresh("agent")` 后新 Agent 绑定的工具集与动态提示词与 `tools` 分类配置一致；如上重启后端后以 admin 打开前端「工具配置」页，确认列表真实渲染、开关切换后刷新、兜底行置灰。

- [x] **Step 4: 数据清理**

确认步骤 7 已将 `knowledge_base_query` 恢复为 `enabled`；最终 `GET /api/tools` 应为 6 工具全 `enabled`（`transfer_human`/`clarify` 恒为 enabled）。无脏数据残留。

- [x] **Step 5: Commit（如需，验证期间的辅助改动）**

如验证中发现需修正的小问题，按对应 Task 修复并单独 commit；如无改动则跳过。

---

## 自检记录

- **Spec 覆盖**：Design D1（Task1/2）✓、D2（Task3）✓、D3（Task4）✓、D4（Task2 时序 + Task4 接线）✓、D5（Task2）✓、D6（Task5）✓、D7（Task6/7）✓、测试策略（Task1-5 单测、Task4 集成、Task8 端到端）✓、迁移（无 schema 变更，复用 system_configs + 幂等插入）✓。
- **占位符扫描**：所有任务均含具体代码、测试代码、命令与验收标准，无 TBD/TODO/"类似 Task N"。
- **类型一致性**：`update_tool_state` 返回 `(name, enabled, refresh_ok)` 与 Task5 解包一致；`UnknownToolError`/`GuardedToolError`（继承 ValueError）在服务层抛出、接口层区分 40005/40004；`build_system_prompt`/`filter_tools`/`TOOL_DESCRIPTIONS` 在 Task3 定义、Task4/5 引用签名一致；前端 `ToolItem`/`ToolUpdateResult`/`getToolsApi`/`updateToolApi`/`useToolServices` 在 Task6 定义、Task7 消费一致。
