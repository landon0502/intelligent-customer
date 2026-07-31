---
change: redesign-agent-init-dynamic-config
design-doc: docs/superpowers/specs/2026-07-31-redesign-agent-init-dynamic-config-design.md
base-ref: b4b31cfa2e6d27268a4b198d850140f03a2b3b8c
---

# Agent 初始化重构与 LLM 配置动态生效 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 service 端 Agent 初始化和 LLM 配置管理，引入 AsyncConfigProvider + ComponentRegistry + ComponentSlot 三层架构，实现请求级配置生效、Agent/RAG LLM 独立配置、懒加载初始化。

**Architecture:** 引入 AsyncConfigProvider 统一异步读取 DB 配置并缓存，ComponentRegistry + ComponentSlot 管理组件的懒加载创建和事务性版本化替换。所有全局单例（`_llm`、`_embeddings`、`_chroma_client`、`_vectorstore`）和同步 DB hack 被移除，改为 Registry 管理的工厂函数。配置更新时通过 Provider 失效缓存 + Registry 事务性刷新组件，保证原子性和失败回退。

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy (async), LangChain, ChromaDB, pytest + pytest-anyio

## Global Constraints

- Factory 签名统一为 `sync (config: dict) -> component`，与 LangChain sync API 兼容
- ComponentRegistry.get() 为同步方法（FastAPI Depends 需要），懒加载通过 `ensure_initialized()` 异步方法实现
- 刷新原子性：`refresh_category()` 先创建所有新实例，全部成功后统一替换，任一失败全部回退
- 注册顺序：`agent_llm` -> `rag_llm` -> `embeddings` -> `chroma_client` -> `vectorstore` -> `agent`
- VectorStore 跨分类：`config_category` 为 `vectorstore`，factory 内部通过 `registry.get("embeddings")` 获取 embeddings；`embedding` 分类变更时额外刷新 vectorstore
- rag_llm fallback：`rag_llm` 分类无配置时回退到 `llm` 分类
- 移除所有 `print()` 调试代码
- 测试使用 pytest + pytest-anyio，mock DB session

---

## File Structure

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| Create | `configs/provider.py` | AsyncConfigProvider — 异步读取 DB 配置，内存缓存，支持失效 |
| Create | `configs/registry.py` | ComponentSlot + ComponentRegistry — 懒加载、原子替换、事务性刷新 |
| Create | `tests/test_provider.py` | AsyncConfigProvider 单元测试 |
| Create | `tests/test_registry.py` | ComponentSlot + ComponentRegistry 单元测试 |
| Create | `tests/test_factory_functions.py` | 工厂函数单元测试 |
| Modify | `models/factory.py` | 移除全局单例和同步 DB hack，改为纯工厂函数 |
| Modify | `models/embedding.py` | 移除全局单例和同步 DB hack，改为纯工厂函数 |
| Modify | `rag/ingestion/vectorstore.py` | 移除全局单例和同步 DB hack，改为纯工厂函数 |
| Modify | `agent/factory.py` | 改为接受注入的 LLM 实例 |
| Modify | `rag/generation/chain.py` | 改为接受注入的 rag_llm 参数 |
| Modify | `services/config.py` | 增加 rag_llm 默认配置，重构 _apply_config_changes |
| Modify | `app/lifespan.py` | 创建 Provider + Registry，注册组件，移除 eager 初始化 |
| Modify | `app/dependencies.py` | 从 Registry 获取组件，增加 get_config_provider / get_registry |
| Modify | `api/chat.py` | SSE 流通过依赖注入获取 Agent 引用 |
| Modify | `api/config.py` | 配置更新 API 返回生效状态 |
| Modify | `rag/retrieval/retriever.py` | 改为从 Registry 获取 vectorstore |
| Modify | `rag/ingestion/__init__.py` | 更新导出 |
| Modify | `rag/__init__.py` | 更新导出 |
| Modify | `services/knowledge.py` | 适配新的 RAG 调用链 |

---

### Task 1: AsyncConfigProvider

**Files:**
- Create: `apps/service/configs/provider.py`
- Modify: `apps/service/configs/__init__.py`
- Test: `apps/service/tests/test_provider.py`

**Interfaces:**
- Consumes: `database.mysql.async_session_factory`, `schemas.system_config.SystemConfig`
- Produces: `configs.provider.AsyncConfigProvider` — `get_category(category: str) -> dict[str, str]`, `get_value(key: str, default: str) -> str`, `invalidate(category: str) -> None`, `invalidate_all() -> None`

- [x] **Step 1: Write the failing test for AsyncConfigProvider**

```python
# apps/service/tests/test_provider.py
"""AsyncConfigProvider 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from configs.provider import AsyncConfigProvider


def _make_mock_rows(data: dict[str, str]):
    """构造模拟 DB 行列表。"""
    rows = []
    for key, value in data.items():
        row = MagicMock()
        row.key = key
        row.value = value
        rows.append(row)
    return rows


@pytest.mark.anyio
async def test_get_category_reads_from_db_on_cache_miss():
    """缓存未命中时从 DB 读取配置。"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "deepseek-v4-pro",
        "llm.temperature": "0.7",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    result = await provider.get_category("llm")

    assert result == {"llm.model": "deepseek-v4-pro", "llm.temperature": "0.7"}
    mock_session.execute.assert_called_once()


@pytest.mark.anyio
async def test_get_category_returns_cached_on_cache_hit():
    """缓存命中时直接返回，不读 DB。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    # 手动填充缓存
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}

    result = await provider.get_category("llm")
    assert result == {"llm.model": "deepseek-v4-pro"}
    # mock_factory 不应被调用
    mock_factory.assert_not_called()


@pytest.mark.anyio
async def test_get_value_extracts_single_value():
    """get_value 从缓存中提取单个值。"""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "deepseek-v4-pro",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    value = await provider.get_value("llm.model", "default-model")
    assert value == "deepseek-v4-pro"


@pytest.mark.anyio
async def test_get_value_returns_default_on_missing_key():
    """get_value 在 key 不存在时返回默认值。"""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.temperature": "0.7",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    value = await provider.get_value("llm.model", "default-model")
    assert value == "default-model"


@pytest.mark.anyio
async def test_invalidate_removes_category_from_cache():
    """invalidate 移除指定分类的缓存。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}
    provider._cache["embedding"] = {"embedding.model": "bge-base-zh"}

    provider.invalidate("llm")
    assert "llm" not in provider._cache
    assert "embedding" in provider._cache


@pytest.mark.anyio
async def test_invalidate_all_clears_entire_cache():
    """invalidate_all 清空所有缓存。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}
    provider._cache["embedding"] = {"embedding.model": "bge-base-zh"}

    provider.invalidate_all()
    assert provider._cache == {}


@pytest.mark.anyio
async def test_invalidate_then_get_re_reads_from_db():
    """失效后再次获取会重新从 DB 读取。"""
    mock_session = AsyncMock()
    mock_result_old = MagicMock()
    mock_result_old.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "old-model",
    })
    mock_result_new = MagicMock()
    mock_result_new.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "new-model",
    })
    mock_session.execute = AsyncMock(
        side_effect=[mock_result_old, mock_result_new]
    )
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)

    # 首次读取
    result1 = await provider.get_category("llm")
    assert result1 == {"llm.model": "old-model"}

    # 失效后重新读取
    provider.invalidate("llm")
    result2 = await provider.get_category("llm")
    assert result2 == {"llm.model": "new-model"}

    assert mock_session.execute.call_count == 2
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'configs.provider'`

- [x] **Step 3: Write AsyncConfigProvider implementation**

```python
# apps/service/configs/provider.py
"""统一配置提供者 — 异步读取 DB 配置，内存缓存，支持失效。"""

import logging
from typing import Callable, Any

from sqlalchemy import select

from schemas.system_config import SystemConfig

logger = logging.getLogger("intelligent-customer.config.provider")


class AsyncConfigProvider:
    """统一配置提供者 — 异步读取 DB 配置，内存缓存，支持失效。

    使用 Cache-Aside 模式：先查缓存，miss 时读 DB 并写入缓存。
    按分类缓存，与配置更新 API 的分类粒度一致。
    """

    def __init__(self, session_factory: Callable):
        """
        Args:
            session_factory: async_session_factory，调用返回 async context manager
        """
        self._session_factory = session_factory
        self._cache: dict[str, dict[str, str]] = {}

    async def get_category(self, category: str) -> dict[str, str]:
        """获取某分类下所有配置，优先返回缓存。

        Args:
            category: 配置分类名（如 "llm", "embedding", "vectorstore"）

        Returns:
            该分类下所有配置的 {key: value} 字典
        """
        if category in self._cache:
            return self._cache[category]

        async with self._session_factory() as db:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.category == category)
            )
            rows = result.scalars().all()
            config = {row.key: row.value for row in rows}
            self._cache[category] = config
            return config

    async def get_value(self, key: str, default: str = "") -> str:
        """获取单个配置值，从缓存中提取。

        key 格式为 "category.rest"，如 "llm.model"。
        自动提取 category 部分加载对应分类缓存。

        Args:
            key: 配置键（如 "llm.model"）
            default: 默认值

        Returns:
            配置值，不存在时返回 default
        """
        category = key.split(".")[0]
        config = await self.get_category(category)
        return config.get(key, default)

    def invalidate(self, category: str) -> None:
        """失效某分类的缓存。

        Args:
            category: 要失效的分类名
        """
        self._cache.pop(category, None)

    def invalidate_all(self) -> None:
        """失效所有缓存。"""
        self._cache.clear()
```

- [x] **Step 4: Update configs/__init__.py to export AsyncConfigProvider**

```python
# apps/service/configs/__init__.py
from configs.config import Settings
from configs.provider import AsyncConfigProvider
```

- [x] **Step 5: Run test to verify it passes**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_provider.py -v`
Expected: ALL PASS

- [x] **Step 6: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/configs/provider.py apps/service/configs/__init__.py apps/service/tests/test_provider.py
git commit -m "feat: add AsyncConfigProvider with cache-aside pattern and unit tests"
```

---

### Task 2: ComponentSlot + ComponentRegistry

**Files:**
- Create: `apps/service/configs/registry.py`
- Modify: `apps/service/configs/__init__.py`
- Test: `apps/service/tests/test_registry.py`

**Interfaces:**
- Consumes: `configs.provider.AsyncConfigProvider`
- Produces: `configs.registry.ComponentSlot` — `get() -> Any`, `create(config: dict) -> Any`, `replace(new_instance: Any) -> None`
- Produces: `configs.registry.ComponentRegistry` — `register(name, factory, config_category)`, `get(name) -> Any`, `ensure_initialized(name) -> Any` (async), `refresh(name) -> bool` (async), `refresh_category(category) -> dict[str, bool]` (async)

- [x] **Step 1: Write the failing test for ComponentSlot and ComponentRegistry**

```python
# apps/service/tests/test_registry.py
"""ComponentSlot + ComponentRegistry 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from configs.registry import ComponentSlot, ComponentRegistry


# ========== ComponentSlot 测试 ==========


def test_slot_get_raises_on_uninitialized():
    """未初始化时 get() 抛出 RuntimeError。"""
    slot = ComponentSlot("test", factory=lambda c: "instance", config_category="llm")
    with pytest.raises(RuntimeError, match="not initialized"):
        slot.get()


def test_slot_create_initializes_instance():
    """create() 用给定配置创建实例。"""
    factory = MagicMock(return_value="created_instance")
    slot = ComponentSlot("test", factory=factory, config_category="llm")
    result = slot.create({"llm.model": "deepseek-v4-pro"})

    assert result == "created_instance"
    assert slot.get() == "created_instance"
    factory.assert_called_once_with({"llm.model": "deepseek-v4-pro"})


def test_slot_replace_swaps_instance():
    """replace() 原子替换当前实例。"""
    slot = ComponentSlot("test", factory=lambda c: "old", config_category="llm")
    slot.create({})
    slot.replace("new_instance")
    assert slot.get() == "new_instance"


# ========== ComponentRegistry 测试 ==========


def test_registry_get_raises_on_unregistered():
    """获取未注册的组件抛出 KeyError。"""
    provider = MagicMock()
    registry = ComponentRegistry(provider)
    with pytest.raises(KeyError, match="not registered"):
        registry.get("nonexistent")


@pytest.mark.anyio
async def test_registry_ensure_initialized_creates_on_first_call():
    """首次 ensure_initialized 时创建组件。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value={"llm.model": "deepseek-v4-pro"})

    factory = MagicMock(return_value="llm_instance")
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    result = await registry.ensure_initialized("agent_llm")

    assert result == "llm_instance"
    mock_provider.get_category.assert_called_once_with("llm")
    factory.assert_called_once_with({"llm.model": "deepseek-v4-pro"})


@pytest.mark.anyio
async def test_registry_ensure_initialized_returns_existing():
    """已初始化时 ensure_initialized 直接返回现有实例。"""
    mock_provider = AsyncMock()
    factory = MagicMock(return_value="llm_instance")
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    # 首次初始化
    result1 = await registry.ensure_initialized("agent_llm")
    # 再次获取
    result2 = await registry.ensure_initialized("agent_llm")

    assert result1 == result2
    assert factory.call_count == 1  # 只创建一次


def test_registry_get_returns_initialized_instance():
    """get() 返回已初始化的实例（同步方法）。"""
    mock_provider = AsyncMock()
    factory = MagicMock(return_value="llm_instance")
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    # 手动初始化 slot
    registry._slots["agent_llm"].create({"llm.model": "deepseek-v4-pro"})

    result = registry.get("agent_llm")
    assert result == "llm_instance"


@pytest.mark.anyio
async def test_registry_refresh_replaces_single_component():
    """refresh() 刷新单个组件。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(
        side_effect=[
            {"llm.model": "old-model"},  # ensure_initialized
            {"llm.model": "new-model"},  # refresh
        ]
    )

    factory = MagicMock(side_effect=["old_instance", "new_instance"])
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    await registry.ensure_initialized("agent_llm")
    assert registry.get("agent_llm") == "old_instance"

    success = await registry.refresh("agent_llm")
    assert success is True
    assert registry.get("agent_llm") == "new_instance"


@pytest.mark.anyio
async def test_registry_refresh_failure_keeps_old_instance():
    """refresh() 失败时保留旧实例。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value={"llm.model": "deepseek-v4-pro"})

    factory = MagicMock(side_effect=["old_instance", Exception("creation failed")])
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    await registry.ensure_initialized("agent_llm")
    assert registry.get("agent_llm") == "old_instance"

    success = await registry.refresh("agent_llm")
    assert success is False
    assert registry.get("agent_llm") == "old_instance"


@pytest.mark.anyio
async def test_registry_refresh_category_transactional_all_or_nothing():
    """refresh_category() 事务性刷新：全部成功才替换，任一失败全部回退。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value={"llm.model": "deepseek-v4-pro"})

    # agent_llm 成功，agent 失败
    factory_llm = MagicMock(side_effect=["old_llm", "new_llm"])
    factory_agent = MagicMock(side_effect=["old_agent", Exception("agent creation failed")])

    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory_llm, "llm")
    registry.register("agent", factory_agent, "llm")

    # 初始化
    await registry.ensure_initialized("agent_llm")
    await registry.ensure_initialized("agent")

    # 刷新分类
    result = await registry.refresh_category("llm")

    # 全部回退
    assert result == {"agent_llm": False, "agent": False}
    assert registry.get("agent_llm") == "old_llm"
    assert registry.get("agent") == "old_agent"


@pytest.mark.anyio
async def test_registry_refresh_category_all_success():
    """refresh_category() 全部成功时统一替换。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value={"llm.model": "deepseek-v4-pro"})

    factory_llm = MagicMock(side_effect=["old_llm", "new_llm"])
    factory_agent = MagicMock(side_effect=["old_agent", "new_agent"])

    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory_llm, "llm")
    registry.register("agent", factory_agent, "llm")

    await registry.ensure_initialized("agent_llm")
    await registry.ensure_initialized("agent")

    result = await registry.refresh_category("llm")

    assert result == {"agent_llm": True, "agent": True}
    assert registry.get("agent_llm") == "new_llm"
    assert registry.get("agent") == "new_agent"


@pytest.mark.anyio
async def test_registry_refresh_category_invalidates_cache_first():
    """refresh_category() 先失效缓存再读取。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(
        side_effect=[
            {"llm.model": "old-model"},  # ensure_initialized
            {"llm.model": "new-model"},  # refresh (after invalidate)
        ]
    )
    mock_provider.invalidate = MagicMock()

    factory = MagicMock(side_effect=["old_instance", "new_instance"])
    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory, "llm")

    await registry.ensure_initialized("agent_llm")
    await registry.refresh_category("llm")

    mock_provider.invalidate.assert_called_once_with("llm")
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'configs.registry'`

- [x] **Step 3: Write ComponentSlot and ComponentRegistry implementation**

```python
# apps/service/configs/registry.py
"""组件注册表 — 管理组件的懒加载创建和事务性版本化替换。"""

import logging
from typing import Any, Callable

from configs.provider import AsyncConfigProvider

logger = logging.getLogger("intelligent-customer.config.registry")


class ComponentSlot:
    """组件槽位 — 懒加载、原子替换、失败保留旧实例。

    每个槽位持有一个组件实例和创建该组件的工厂函数。
    首次通过 create() 创建，后续通过 replace() 原子替换。
    """

    def __init__(self, name: str, factory: Callable[[dict], Any], config_category: str):
        """
        Args:
            name: 组件名称（如 "agent_llm"）
            factory: 同步工厂函数，签名为 (config: dict) -> component
            config_category: 依赖的配置分类（如 "llm"）
        """
        self.name = name
        self._factory = factory
        self._config_category = config_category
        self._current: Any = None
        self._initialized = False

    def get(self) -> Any:
        """获取当前组件实例。

        Returns:
            当前组件实例

        Raises:
            RuntimeError: 组件未初始化
        """
        if not self._initialized:
            raise RuntimeError(f"Component '{self.name}' not initialized. Call create first.")
        return self._current

    def create(self, config: dict) -> Any:
        """用给定配置创建组件实例（首次创建）。

        Args:
            config: 从 AsyncConfigProvider 获取的配置字典

        Returns:
            创建的组件实例
        """
        instance = self._factory(config)
        self._current = instance
        self._initialized = True
        return instance

    def replace(self, new_instance: Any) -> None:
        """原子替换当前实例。

        旧引用继续有效直到释放（Python 引用计数）。

        Args:
            new_instance: 新的组件实例
        """
        self._current = new_instance


class ComponentRegistry:
    """组件注册表 — 管理组件的懒加载创建和事务性版本化替换。

    注册顺序决定刷新顺序，保证依赖组件先刷新。
    refresh_category() 实现事务性刷新：先创建所有新实例，
    全部成功后统一替换；任一失败则全部回退，保留旧实例。
    """

    def __init__(self, provider: AsyncConfigProvider):
        """
        Args:
            provider: AsyncConfigProvider 实例，用于读取配置
        """
        self._provider = provider
        self._slots: dict[str, ComponentSlot] = {}
        self._order: list[str] = []  # 注册顺序

    def register(self, name: str, factory: Callable[[dict], Any],
                 config_category: str) -> None:
        """注册组件（不触发创建）。

        Args:
            name: 组件名称
            factory: 同步工厂函数 (config: dict) -> component
            config_category: 依赖的配置分类
        """
        slot = ComponentSlot(name, factory, config_category)
        self._slots[name] = slot
        self._order.append(name)

    def get(self, name: str) -> Any:
        """获取组件（同步，必须已初始化）。

        Args:
            name: 组件名称

        Returns:
            组件实例

        Raises:
            KeyError: 组件未注册
        """
        slot = self._slots.get(name)
        if slot is None:
            raise KeyError(f"Component '{name}' not registered")
        return slot.get()

    async def ensure_initialized(self, name: str) -> Any:
        """确保组件已初始化（懒加载）。

        首次调用时从 Provider 读取配置并创建组件实例，
        后续调用直接返回已有实例。

        Args:
            name: 组件名称

        Returns:
            组件实例

        Raises:
            KeyError: 组件未注册
        """
        slot = self._slots.get(name)
        if slot is None:
            raise KeyError(f"Component '{name}' not registered")
        if not slot._initialized:
            config = await self._provider.get_category(slot._config_category)
            slot.create(config)
        return slot.get()

    async def refresh(self, name: str) -> bool:
        """刷新单个组件。

        读取最新配置，创建新实例并替换。失败时保留旧实例。

        Args:
            name: 组件名称

        Returns:
            是否刷新成功
        """
        slot = self._slots.get(name)
        if slot is None:
            return False
        try:
            config = await self._provider.get_category(slot._config_category)
            new_instance = slot._factory(config)
            slot.replace(new_instance)
            return True
        except Exception as e:
            logger.error("刷新组件 %s 失败: %s", name, e)
            return False

    async def refresh_category(self, category: str) -> dict[str, bool]:
        """事务性刷新某分类下所有组件。

        先失效缓存，确保读取最新配置。
        为每个 slot 创建新实例，全部成功后统一替换；
        任一失败则全部回退，保留旧实例。

        Args:
            category: 配置分类名

        Returns:
            {组件名: 是否刷新成功} 字典
        """
        # 1. 收集该分类下的 slot（按注册顺序）
        affected = [s for s in self._slots.values()
                     if s._config_category == category]

        if not affected:
            return {}

        # 2. 先失效缓存，确保读取最新配置
        self._provider.invalidate(category)

        # 3. 为每个 slot 创建新实例
        new_instances: dict[str, tuple[ComponentSlot, Any]] = {}
        for slot in affected:
            try:
                config = await self._provider.get_category(slot._config_category)
                new_instance = slot._factory(config)
                new_instances[slot.name] = (slot, new_instance)
            except Exception as e:
                logger.error("事务性刷新失败: 创建 %s 时出错: %s", slot.name, e)
                # 全部回退：不替换任何实例
                return {name: False for name in self._slots
                        if self._slots[name]._config_category == category}

        # 4. 全部成功，统一替换
        for slot, new_instance in new_instances.values():
            slot.replace(new_instance)

        return {name: True for name in new_instances}
```

- [x] **Step 4: Update configs/__init__.py to export registry**

```python
# apps/service/configs/__init__.py
from configs.config import Settings
from configs.provider import AsyncConfigProvider
from configs.registry import ComponentSlot, ComponentRegistry
```

- [x] **Step 5: Run test to verify it passes**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_registry.py -v`
Expected: ALL PASS

- [x] **Step 6: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/configs/registry.py apps/service/configs/__init__.py apps/service/tests/test_registry.py
git commit -m "feat: add ComponentSlot + ComponentRegistry with transactional refresh and unit tests"
```

---

### Task 3: 重构模型工厂函数

**Files:**
- Modify: `apps/service/models/factory.py`
- Modify: `apps/service/models/embedding.py`
- Modify: `apps/service/rag/ingestion/vectorstore.py`
- Create: `apps/service/tests/test_factory_functions.py`

**Interfaces:**
- Consumes: `configs.provider.AsyncConfigProvider`, `configs.registry.ComponentRegistry`
- Produces: `models.factory.create_agent_llm(config: dict) -> BaseChatModel`, `models.factory.create_rag_llm(rag_config: dict, llm_config: dict) -> BaseChatModel`
- Produces: `models.embedding.create_embeddings(config: dict) -> HuggingFaceEmbeddings`
- Produces: `rag.ingestion.vectorstore.create_chroma_client(config: dict) -> HttpClient`, `rag.ingestion.vectorstore.create_vectorstore(config: dict, embeddings, client) -> Chroma`

- [x] **Step 1: Write the failing test for factory function unit tests**

```python
# apps/service/tests/test_factory_functions.py
"""工厂函数单元测试 — 验证纯工厂函数正确创建组件。"""

import pytest
from unittest.mock import MagicMock, patch


def test_create_agent_llm_creates_chat_model():
    """create_agent_llm 用配置创建 BaseChatModel。"""
    from models.factory import create_agent_llm

    config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "test-key",
        "llm.base_url": "https://api.test.com",
        "llm.temperature": "0.5",
        "llm.max_tokens": "1024",
        "llm.timeout": "30",
        "llm.max_retries": "2",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_agent_llm(config)

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["max_retries"] == 2


def test_create_agent_llm_uses_defaults_on_missing_keys():
    """create_agent_llm 在配置缺失时使用默认值。"""
    from models.factory import create_agent_llm

    config = {}  # 空配置

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        create_agent_llm(config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"  # 默认值
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 512


def test_create_rag_llm_with_rag_config():
    """create_rag_llm 使用 rag_llm 分类配置。"""
    from models.factory import create_rag_llm

    rag_config = {
        "rag_llm.model": "glm-4-flash",
        "rag_llm.api_key": "rag-key",
        "rag_llm.base_url": "https://rag.test.com",
        "rag_llm.temperature": "0.3",
        "rag_llm.max_tokens": "256",
        "rag_llm.timeout": "10",
        "rag_llm.max_retries": "1",
    }
    llm_config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "llm-key",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_rag_llm(rag_config, llm_config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "glm-4-flash"
        assert call_kwargs["temperature"] == 0.3


def test_create_rag_llm_falls_back_to_llm_config():
    """create_rag_llm 在 rag_llm 配置为空时回退到 llm 配置。"""
    from models.factory import create_rag_llm

    rag_config = {}  # 空 rag_llm 配置
    llm_config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "llm-key",
        "llm.base_url": "https://api.test.com",
        "llm.temperature": "0.7",
        "llm.max_tokens": "512",
        "llm.timeout": "15",
        "llm.max_retries": "1",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_rag_llm(rag_config, llm_config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"
        assert call_kwargs["api_key"] == "llm-key"


def test_create_embeddings_creates_hf_instance():
    """create_embeddings 用配置创建 HuggingFaceEmbeddings。"""
    from models.embedding import create_embeddings

    config = {
        "embedding.model": "BAAI/bge-large-zh",
    }

    with patch("models.embedding.HuggingFaceEmbeddings") as mock_hf:
        mock_hf.return_value = MagicMock(name="HuggingFaceEmbeddings")
        result = create_embeddings(config)

        mock_hf.assert_called_once()
        call_kwargs = mock_hf.call_args[1]
        assert call_kwargs["model_name"] == "BAAI/bge-large-zh"


def test_create_embeddings_uses_default_model():
    """create_embeddings 在配置缺失时使用默认模型。"""
    from models.embedding import create_embeddings

    config = {}

    with patch("models.embedding.HuggingFaceEmbeddings") as mock_hf:
        mock_hf.return_value = MagicMock(name="HuggingFaceEmbeddings")
        create_embeddings(config)

        call_kwargs = mock_hf.call_args[1]
        assert call_kwargs["model_name"] == "BAAI/bge-base-zh-v1.5"


def test_create_chroma_client_creates_http_client():
    """create_chroma_client 用配置创建 chromadb.HttpClient。"""
    from rag.ingestion.vectorstore import create_chroma_client

    config = {
        "vectorstore.host": "192.168.1.100",
        "vectorstore.port": "9000",
    }

    with patch("rag.ingestion.vectorstore.chromadb") as mock_chroma:
        mock_chroma.HttpClient.return_value = MagicMock(name="HttpClient")
        result = create_chroma_client(config)

        mock_chroma.HttpClient.assert_called_once_with(
            host="192.168.1.100", port=9000
        )


def test_create_vectorstore_creates_chroma_instance():
    """create_vectorstore 用配置和 embeddings 创建 Chroma。"""
    from rag.ingestion.vectorstore import create_vectorstore

    config = {
        "vectorstore.host": "localhost",
        "vectorstore.port": "8000",
        "vectorstore.collection": "test_collection",
    }
    mock_embeddings = MagicMock(name="HuggingFaceEmbeddings")
    mock_client = MagicMock(name="HttpClient")

    with patch("rag.ingestion.vectorstore.Chroma") as mock_chroma_cls:
        mock_chroma_cls.return_value = MagicMock(name="Chroma")
        result = create_vectorstore(config, mock_embeddings, mock_client)

        mock_chroma_cls.assert_called_once_with(
            client=mock_client,
            collection_name="test_collection",
            embedding_function=mock_embeddings,
        )
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_factory_functions.py -v`
Expected: FAIL — `ImportError: cannot import name 'create_agent_llm'`

- [x] **Step 3: Rewrite models/factory.py — remove global singleton, add pure factory functions**

Replace entire file content:

```python
# apps/service/models/factory.py
"""LLM 工厂函数 — 创建 Agent LLM 和 RAG LLM 实例。

纯函数，无全局状态。由 ComponentRegistry 调用。
"""

import httpx
from langchain.chat_models import init_chat_model


def _build_llm_params(config: dict, prefix: str = "llm") -> dict:
    """从配置字典构建 LLM 参数。

    Args:
        config: 配置字典（key 格式为 "prefix.xxx"）
        prefix: 配置键前缀（"llm" 或 "rag_llm"）

    Returns:
        init_chat_model 所需的参数字典
    """
    model = config.get(f"{prefix}.model", "deepseek-v4-pro")
    temperature = float(config.get(f"{prefix}.temperature", "0.7"))
    max_tokens = int(config.get(f"{prefix}.max_tokens", "512"))
    timeout = int(config.get(f"{prefix}.timeout", "15"))
    max_retries = int(config.get(f"{prefix}.max_retries", "1"))
    api_key = config.get(f"{prefix}.api_key", "")
    base_url = config.get(f"{prefix}.base_url", "")

    return {
        "model": model,
        "model_provider": "openai",
        "api_key": api_key,
        "base_url": base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "max_retries": max_retries,
        "http_async_client": httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10)
        ),
    }


def create_agent_llm(config: dict):
    """创建 Agent 使用的 LLM 实例。

    Args:
        config: "llm" 分类的配置字典

    Returns:
        BaseChatModel 实例
    """
    params = _build_llm_params(config, prefix="llm")
    return init_chat_model(**params)


def create_rag_llm(rag_config: dict, llm_config: dict):
    """创建 RAG 生成链使用的 LLM 实例。

    当 rag_llm 分类无配置时，回退到 llm 分类配置。

    Args:
        rag_config: "rag_llm" 分类的配置字典
        llm_config: "llm" 分类的配置字典（fallback）

    Returns:
        BaseChatModel 实例
    """
    if not rag_config:
        # rag_llm 分类无配置，回退到 llm 分类
        params = _build_llm_params(llm_config, prefix="llm")
    else:
        params = _build_llm_params(rag_config, prefix="rag_llm")
    return init_chat_model(**params)
```

- [x] **Step 4: Rewrite models/embedding.py — remove global singleton, add pure factory function**

Replace entire file content:

```python
# apps/service/models/embedding.py
"""Embedding 模型工厂函数 — 创建 HuggingFaceEmbeddings 实例。

纯函数，无全局状态。由 ComponentRegistry 调用。
"""

from langchain_huggingface import HuggingFaceEmbeddings


def create_embeddings(config: dict) -> HuggingFaceEmbeddings:
    """创建 Embedding 实例。

    Args:
        config: "embedding" 分类的配置字典

    Returns:
        HuggingFaceEmbeddings 实例
    """
    model_name = config.get("embedding.model", "BAAI/bge-base-zh-v1.5")

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
```

- [x] **Step 5: Rewrite rag/ingestion/vectorstore.py — remove global singletons, add pure factory functions**

Replace entire file content:

```python
# apps/service/rag/ingestion/vectorstore.py
"""向量化与 Chroma 入库 — 文档块 Embedding + Chroma 存储/删除。

工厂函数由 ComponentRegistry 调用。
运行时函数（add_documents_to_vectorstore, delete_from_vectorstore）
通过 Registry 获取当前组件实例。
"""

import asyncio
import logging

import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma

logger = logging.getLogger("intelligent-customer.rag.vectorstore")


# ========== 工厂函数（由 ComponentRegistry 调用） ==========

def create_chroma_client(config: dict) -> chromadb.HttpClient:
    """创建 Chroma HTTP Client 实例。

    Args:
        config: "vectorstore" 分类的配置字典

    Returns:
        chromadb.HttpClient 实例
    """
    from configs.config import settings
    host = config.get("vectorstore.host", settings.CHROMA_HOST)
    port = config.get("vectorstore.port", str(settings.CHROMA_PORT))

    return chromadb.HttpClient(
        host=host,
        port=int(port),
    )


def create_vectorstore(config: dict, embeddings, client) -> Chroma:
    """创建 Chroma VectorStore 实例。

    Args:
        config: "vectorstore" 分类的配置字典
        embeddings: HuggingFaceEmbeddings 实例（由 Registry 提供）
        client: chromadb.HttpClient 实例（由 Registry 提供）

    Returns:
        Chroma VectorStore 实例
    """
    from configs.config import settings
    collection = config.get("vectorstore.collection", settings.CHROMA_COLLECTION)

    return Chroma(
        client=client,
        collection_name=collection,
        embedding_function=embeddings,
    )


# ========== 运行时函数（通过 Registry 获取组件） ==========

def _get_registry():
    """获取 ComponentRegistry 实例。"""
    from app.main import app
    return app.state.registry


async def add_documents_to_vectorstore(
    documents: list[Document], doc_id: int, filename: str
) -> int:
    """将文档块向量化并存入 Chroma。"""
    if not documents:
        return 0

    for doc in documents:
        doc.metadata["doc_id"] = doc_id
        doc.metadata["filename"] = filename

    registry = _get_registry()
    vectorstore = registry.get("vectorstore")
    await asyncio.to_thread(vectorstore.add_documents, documents)
    logger.info(
        "文档 %s (id=%d) 共 %d 个块已入库",
        filename, doc_id, len(documents),
    )
    return len(documents)


async def delete_from_vectorstore(doc_id: int) -> None:
    """从 Chroma 中删除指定文档的所有向量。"""
    try:
        registry = _get_registry()
        client = registry.get("chroma_client")
        from configs.config import settings
        collection_name = settings.CHROMA_COLLECTION
        collection = client.get_collection(collection_name)
        collection.delete(
            where={"doc_id": doc_id},
        )
        logger.info("文档 id=%d 的向量已从 Chroma 删除", doc_id)
    except Exception as e:
        logger.warning("从 Chroma 删除文档 id=%d 向量失败: %s", doc_id, e)
```

- [x] **Step 6: Run factory function tests**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/test_factory_functions.py -v`
Expected: ALL PASS

- [x] **Step 7: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/models/factory.py apps/service/models/embedding.py apps/service/rag/ingestion/vectorstore.py apps/service/tests/test_factory_functions.py
git commit -m "refactor: remove global singletons and sync DB hacks, replace with pure factory functions"
```

---

### Task 4: 重构 Agent 工厂和 RAG 生成链

**Files:**
- Modify: `apps/service/agent/factory.py`
- Modify: `apps/service/rag/generation/chain.py`

**Interfaces:**
- Consumes: `agent.tools.ALL_TOOLS`, `agent.prompts.SYSTEM_PROMPT`, `langchain.agents.create_agent`
- Produces: `agent.factory.create_customer_agent(agent_llm, tools=None, system_prompt=None)` — 接受注入的 LLM 实例
- Produces: `rag.generation.chain.generate_answer(query, context_chunks, rag_llm=None)` — 接受注入的 rag_llm

- [x] **Step 1: Rewrite agent/factory.py — accept injected LLM**

Replace entire file content:

```python
# apps/service/agent/factory.py
"""Agent 工厂函数 — 创建客服 Agent 实例。

纯函数，接受注入的 LLM 实例。由 ComponentRegistry 调用。
"""

from langchain.agents import create_agent

from agent.tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT


def create_customer_agent(agent_llm, tools=None, system_prompt=None):
    """创建客服 Agent，绑定工具集和系统提示词。

    Args:
        agent_llm: BaseChatModel 实例（由 Registry 注入）
        tools: 工具列表，默认使用 ALL_TOOLS
        system_prompt: 系统提示词，默认使用 SYSTEM_PROMPT

    Returns:
        Agent 实例
    """
    return create_agent(
        model=agent_llm,
        tools=tools or ALL_TOOLS,
        system_prompt=system_prompt or SYSTEM_PROMPT,
    )
```

- [x] **Step 2: Rewrite rag/generation/chain.py — accept injected rag_llm**

Replace entire file content:

```python
# apps/service/rag/generation/chain.py
"""RAG 生成模块 — Prompt 组装 + LLM 回答生成。

generate_answer 接受注入的 rag_llm 实例。
"""

import logging
import time
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser

from rag.retrieval.prompts import RAG_PROMPT_TEMPLATE
from rag.retrieval.retriever import RetrievalResult

logger = logging.getLogger("intelligent-customer.rag.generation")


@dataclass
class GenerationResult:
    """生成结果。"""

    answer: str
    sources: list[dict] = field(default_factory=list)


def _format_context(chunks: list[RetrievalResult]) -> str:
    """将检索结果格式化为上下文字符串。"""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.metadata.get("filename", "未知文档")
        content = chunk.content.strip()
        parts.append(f"[来源{i}] 文件：{filename} | 内容：{content}")
    return "\n".join(parts)


def _extract_sources(chunks: list[RetrievalResult]) -> list[dict]:
    """从检索结果中提取来源信息。"""
    return [
        {
            "filename": chunk.metadata.get("filename", "未知文档"),
            "chunk_index": chunk.metadata.get("chunk_index", 0),
            "score": round(chunk.score, 4),
        }
        for chunk in chunks
    ]


async def generate_answer(
    query: str, context_chunks: list[RetrievalResult], rag_llm=None
) -> GenerationResult:
    """基于检索结果生成回答。

    Args:
        query: 用户查询
        context_chunks: 检索结果列表
        rag_llm: BaseChatModel 实例（由调用方注入）。为 None 时从 Registry 获取。

    Returns:
        GenerationResult 包含回答和来源
    """
    if not context_chunks:
        return GenerationResult(
            answer="抱歉，我在知识库中没有找到相关信息，无法回答您的问题。",
            sources=[],
        )

    # 如果未注入 rag_llm，从 Registry 获取
    if rag_llm is None:
        from app.main import app
        rag_llm = app.state.registry.get("rag_llm")

    # 组装上下文
    context = _format_context(context_chunks)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

    # 调用 LLM
    t0 = time.time()
    chain = rag_llm | StrOutputParser()
    answer = await chain.ainvoke(prompt)
    logger.info("LLM 生成耗时: %.2fs", time.time() - t0)

    # 提取来源
    sources = _extract_sources(context_chunks)

    logger.info("RAG 回答生成完成, 来源数: %d", len(sources))
    return GenerationResult(answer=answer, sources=sources)
```

- [x] **Step 3: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/agent/factory.py apps/service/rag/generation/chain.py
git commit -m "refactor: agent factory and RAG chain accept injected LLM instances"
```

---

### Task 5: 增加 rag_llm 默认配置

**Files:**
- Modify: `apps/service/services/config.py`

**Interfaces:**
- Consumes: 无新依赖
- Produces: `services/config.DEFAULT_CONFIGS` 中增加 `rag_llm.*` 配置项

- [x] **Step 1: Add rag_llm default configs to DEFAULT_CONFIGS**

在 `DEFAULT_CONFIGS` 字典中，`llm.max_retries` 条目之后、`embedding.provider` 条目之前，插入以下内容：

```python
    # RAG LLM（独立配置，为空时回退到 llm 分类）
    "rag_llm.model": {
        "value": "",
        "category": "rag_llm",
        "description": "RAG 生成链使用的 LLM 模型（为空时回退到 llm.model）",
    },
    "rag_llm.api_key": {
        "value": "",
        "category": "rag_llm",
        "description": "RAG LLM API Key（为空时回退到 llm.api_key）",
    },
    "rag_llm.base_url": {
        "value": "",
        "category": "rag_llm",
        "description": "RAG LLM API Base URL（为空时回退到 llm.base_url）",
    },
    "rag_llm.temperature": {
        "value": "0.3",
        "category": "rag_llm",
        "description": "RAG 生成温度",
    },
    "rag_llm.max_tokens": {
        "value": "512",
        "category": "rag_llm",
        "description": "RAG 最大输出 Token",
    },
    "rag_llm.timeout": {
        "value": "15",
        "category": "rag_llm",
        "description": "RAG LLM 超时时间(秒)",
    },
    "rag_llm.max_retries": {
        "value": "1",
        "category": "rag_llm",
        "description": "RAG LLM 最大重试次数",
    },
```

- [x] **Step 2: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/services/config.py
git commit -m "feat: add rag_llm default config items with fallback to llm category"
```

---

### Task 6: 重构应用启动和依赖注入

**Files:**
- Modify: `apps/service/app/lifespan.py`
- Modify: `apps/service/app/dependencies.py`

**Interfaces:**
- Consumes: `configs.provider.AsyncConfigProvider`, `configs.registry.ComponentRegistry`, `models.factory.create_agent_llm`, `models.factory.create_rag_llm`, `models.embedding.create_embeddings`, `rag.ingestion.vectorstore.create_chroma_client`, `rag.ingestion.vectorstore.create_vectorstore`, `agent.factory.create_customer_agent`
- Produces: `app.state.config_provider`, `app.state.registry`
- Produces: `app.dependencies.get_agent(request) -> Agent`, `app.dependencies.get_agent_async(request) -> Agent` (async), `app.dependencies.get_config_provider(request) -> AsyncConfigProvider`, `app.dependencies.get_registry(request) -> ComponentRegistry`

- [x] **Step 1: Rewrite app/lifespan.py — create Provider + Registry, register components**

Replace entire file content:

```python
# apps/service/app/lifespan.py
"""应用生命周期管理 — 启动时创建 Provider + Registry，关闭时释放资源。"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import mysql
from database.session import get_db
from configs.config import settings
from configs.provider import AsyncConfigProvider
from configs.registry import ComponentRegistry
from database.session import async_session_factory

# 确保所有 ORM 模型被注册到 Base.metadata
import database.models  # noqa: F401

logging.basicConfig(
    level=getattr(logging, "INFO"),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("intelligent-customer")


async def _seed_initial_data() -> None:
    """初始化种子数据：创建管理员用户"""
    from services.auth import seed_admin_user
    async for db in get_db():
        await seed_admin_user(db)


def _register_components(registry: ComponentRegistry) -> None:
    """注册所有组件到 Registry。

    注册顺序保证刷新时依赖组件先刷新：
    agent_llm -> rag_llm -> embeddings -> chroma_client -> vectorstore -> agent

    注意：rag_llm 的 factory 需要同时访问 rag_llm 和 llm 两个分类的配置，
    因此使用闭包捕获 provider。
    """
    from models.factory import create_agent_llm, create_rag_llm
    from models.embedding import create_embeddings
    from rag.ingestion.vectorstore import create_chroma_client, create_vectorstore
    from agent.factory import create_customer_agent

    provider = registry._provider

    # 1. agent_llm — config_category: llm
    registry.register("agent_llm", create_agent_llm, "llm")

    # 2. rag_llm — config_category: rag_llm
    #    factory 需要同时读取 rag_llm 和 llm 配置（fallback）
    def _rag_llm_factory(config: dict):
        # config 是 rag_llm 分类的配置
        # 需要同步获取 llm 分类配置作为 fallback
        # 由于 factory 是 sync，llm_config 在 ensure_initialized 时已缓存
        llm_config = provider._cache.get("llm", {})
        return create_rag_llm(config, llm_config)

    registry.register("rag_llm", _rag_llm_factory, "rag_llm")

    # 3. embeddings — config_category: embedding
    registry.register("embeddings", create_embeddings, "embedding")

    # 4. chroma_client — config_category: vectorstore
    registry.register("chroma_client", create_chroma_client, "vectorstore")

    # 5. vectorstore — config_category: vectorstore
    #    factory 需要已创建的 embeddings 和 chroma_client
    def _vectorstore_factory(config: dict):
        embeddings = registry.get("embeddings")
        client = registry.get("chroma_client")
        return create_vectorstore(config, embeddings, client)

    registry.register("vectorstore", _vectorstore_factory, "vectorstore")

    # 6. agent — config_category: llm
    #    factory 需要已创建的 agent_llm
    def _agent_factory(config: dict):
        agent_llm = registry.get("agent_llm")
        return create_customer_agent(agent_llm)

    registry.register("agent", _agent_factory, "llm")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化 Provider + Registry，关闭时释放资源。"""
    logger.info("启动中...  创建数据库表")
    async with mysql.engine.begin() as conn:
        await conn.run_sync(mysql.Base.metadata.create_all)

    logger.info("初始化种子数据...")
    await _seed_initial_data()

    logger.info("初始化默认配置...")
    try:
        async for db in get_db():
            from services.config import init_default_configs
            await init_default_configs(db)
    except Exception as e:
        logger.warning("初始化默认配置失败: %s", e)

    # 创建 ConfigProvider + Registry
    logger.info("创建 ConfigProvider 和 ComponentRegistry...")
    provider = AsyncConfigProvider(async_session_factory)
    registry = ComponentRegistry(provider)

    # 注册组件（不触发创建）
    _register_components(registry)

    _app.state.config_provider = provider
    _app.state.registry = registry

    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield  # <- 首次请求时懒加载创建组件

    logger.info("关闭中...")
    await mysql.engine.dispose()
    logger.info("已关闭")
```

- [x] **Step 2: Rewrite app/dependencies.py — get components from Registry**

Replace entire file content:

```python
# apps/service/app/dependencies.py
"""FastAPI 依赖注入 — 从 app.state 获取组件实例。"""

from fastapi import Request

from configs.provider import AsyncConfigProvider
from configs.registry import ComponentRegistry


def get_agent(request: Request):
    """获取 Agent 实例（同步，必须已初始化）。"""
    return request.app.state.registry.get("agent")


async def get_agent_async(request: Request):
    """获取 Agent 实例（异步，支持懒加载）。"""
    return await request.app.state.registry.ensure_initialized("agent")


def get_chroma_client(request: Request):
    """获取 Chroma Client 实例。"""
    return request.app.state.registry.get("chroma_client")


def get_config_provider(request: Request) -> AsyncConfigProvider:
    """获取 AsyncConfigProvider 实例。"""
    return request.app.state.config_provider


def get_registry(request: Request) -> ComponentRegistry:
    """获取 ComponentRegistry 实例。"""
    return request.app.state.registry
```

- [x] **Step 3: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/app/lifespan.py apps/service/app/dependencies.py
git commit -m "refactor: lifespan creates Provider+Registry, dependencies get components from Registry"
```

---

### Task 7: 重构 API 层 — chat 和 config

**Files:**
- Modify: `apps/service/api/chat.py`
- Modify: `apps/service/api/config.py`

**Interfaces:**
- Consumes: `app.dependencies.get_agent_async`, `app.dependencies.get_registry`
- Produces: chat SSE 流使用懒加载 Agent；config API 返回刷新状态

- [x] **Step 1: Update api/chat.py — use async agent dependency for lazy loading**

Change the import line from:

```python
from app.dependencies import get_agent
```

to:

```python
from app.dependencies import get_agent_async
```

Change the endpoint parameter from:

```python
    agent=Depends(get_agent),
```

to:

```python
    agent=Depends(get_agent_async),
```

The rest of the file remains unchanged.

- [x] **Step 2: Rewrite api/config.py — return refresh status on update**

Replace entire file content:

```python
# apps/service/api/config.py
"""系统配置接口 — 获取/更新配置，更新后动态生效并返回刷新状态。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.system_config_schema import ConfigItem, ConfigUpdateRequest
from auth.security import get_current_user
from services.config import (
    get_all_configs,
    get_configs_by_category,
    update_configs,
)
from app.dependencies import get_registry
from utils.response import success, error

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def list_configs(
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取配置列表，可按分类筛选"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看配置")

    if category:
        configs = await get_configs_by_category(db, category)
    else:
        configs = await get_all_configs(db)

    items = [ConfigItem.model_validate(c) for c in configs]

    # API Key 脱敏：不返回明文，只标记是否已设置
    for item in items:
        if "api_key" in item.key and item.value:
            item.value = "*" * 16

    return success(data=items)


@router.put("")
async def update_config(
    req: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry=Depends(get_registry),
):
    """批量更新配置项（管理员权限），更新后自动动态生效。

    返回刷新状态：哪些组件已刷新、是否有刷新失败。
    """
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可修改配置")

    refresh_result = await update_configs(
        db, [c.model_dump() for c in req.configs], registry
    )
    return success(data={
        "updated": len(req.configs),
        "refresh_result": refresh_result,
    })
```

- [x] **Step 3: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/api/chat.py apps/service/api/config.py
git commit -m "refactor: chat uses async agent dep, config API returns refresh status"
```

---

### Task 8: 重构配置更新流程

**Files:**
- Modify: `apps/service/services/config.py`

**Interfaces:**
- Consumes: `configs.registry.ComponentRegistry`
- Produces: `services/config.update_configs(db, configs, registry=None)` — 接受 registry 参数，返回刷新结果
- Produces: `services/config._apply_config_changes(categories, registry)` — 使用 Provider 失效 + Registry 刷新

- [x] **Step 1: Rewrite update_configs and _apply_config_changes, remove _rebuild_agent**

Replace the `update_configs` function with:

```python
async def update_configs(
    db: AsyncSession, configs: list[dict], registry=None
) -> dict[str, dict[str, bool]]:
    """批量更新配置项，并触发动态生效。

    Args:
        db: 数据库会话
        configs: 配置项列表，每项包含 key 和 value
        registry: ComponentRegistry 实例（用于动态刷新组件）

    Returns:
        刷新结果 {category: {component_name: success}}
    """
    changed_categories: set[str] = set()

    for item in configs:
        # 跳过脱敏占位值，不覆盖真实的 API Key
        if "api_key" in item["key"] and item.get("value") == "******":
            continue

        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == item["key"])
        )
        config = result.scalar_one_or_none()
        if config:
            if config.value != item["value"]:
                config.value = item["value"]
                changed_categories.add(config.category)
        else:
            # 新增配置项
            category = item.get("category", "general")
            db.add(
                SystemConfig(
                    key=item["key"],
                    value=item["value"],
                    category=category,
                    description=item.get("description"),
                )
            )
            changed_categories.add(category)

    await db.commit()

    # 动态生效
    refresh_result: dict[str, dict[str, bool]] = {}
    if changed_categories and registry is not None:
        refresh_result = await _apply_config_changes(changed_categories, registry)

    return refresh_result
```

Replace the `_apply_config_changes` function with:

```python
async def _apply_config_changes(
    categories: set[str], registry
) -> dict[str, dict[str, bool]]:
    """配置变更后，通过 Registry 事务性刷新对应组件。

    Args:
        categories: 变更的分类集合
        registry: ComponentRegistry 实例

    Returns:
        {category: {component_name: success}} 刷新结果
    """
    result: dict[str, dict[str, bool]] = {}

    for category in categories:
        refresh_result = await registry.refresh_category(category)
        result[category] = refresh_result

        if refresh_result:
            success_names = [n for n, ok in refresh_result.items() if ok]
            fail_names = [n for n, ok in refresh_result.items() if not ok]
            if success_names:
                logger.info(
                    "分类 %s 刷新成功: %s", category, ", ".join(success_names)
                )
            if fail_names:
                logger.warning(
                    "分类 %s 刷新失败（旧组件继续服务）: %s",
                    category, ", ".join(fail_names),
                )

    # 特殊处理：embedding 变更时额外刷新 vectorstore
    if "embedding" in categories:
        vs_refresh = await registry.refresh("vectorstore")
        result.setdefault("embedding", {})["vectorstore"] = vs_refresh
        if vs_refresh:
            logger.info("embedding 变更后 vectorstore 刷新成功")
        else:
            logger.warning("embedding 变更后 vectorstore 刷新失败（旧组件继续服务）")

    return result
```

Delete the entire `_rebuild_agent` function.

- [x] **Step 2: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/services/config.py
git commit -m "refactor: config update uses Provider invalidate + Registry refresh, remove _rebuild_agent"
```

---

### Task 9: 适配 RAG 调用链

**Files:**
- Modify: `apps/service/rag/retrieval/retriever.py`
- Modify: `apps/service/rag/ingestion/__init__.py`
- Modify: `apps/service/rag/__init__.py`
- Modify: `apps/service/services/knowledge.py`

**Interfaces:**
- Consumes: `app.state.registry` 获取 vectorstore 和 rag_llm
- Produces: `rag.retrieval.retriever.retrieve(query, top_k)` — 从 Registry 获取 vectorstore

- [x] **Step 1: Rewrite rag/retrieval/retriever.py — get vectorstore from Registry**

Replace entire file content:

```python
# apps/service/rag/retrieval/retriever.py
"""RAG 检索模块 — 向量搜索 + 相似度过滤。"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from configs.config import settings

logger = logging.getLogger("intelligent-customer.rag.retrieval")


@dataclass
class RetrievalResult:
    """单条检索结果。"""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)


async def retrieve(
    query: str, top_k: int | None = None
) -> list[RetrievalResult]:
    """检索与查询最相关的文档块。

    流程：问题向量化 -> Chroma 相似度检索 -> 过滤低分 -> 取 Top-K

    Args:
        query: 用户查询文本
        top_k: 返回结果数量，默认使用配置值

    Returns:
        检索结果列表，按相关性排序
    """
    k = top_k or settings.RAG_TOP_K
    t0 = time.time()

    # 从 Registry 获取 vectorstore
    from app.main import app
    vectorstore = app.state.registry.get("vectorstore")

    # Chroma 相似度检索（同步阻塞操作，放入线程池避免卡住事件循环）
    raw_results = await asyncio.to_thread(
        vectorstore.similarity_search_with_relevance_scores, query, k=k
    )
    logger.info("Chroma 检索耗时: %.2fs", time.time() - t0)

    if not raw_results:
        logger.info("检索无结果: query=%s", query[:50])
        return []

    # 过滤低分结果
    filtered = [
        (doc, score)
        for doc, score in raw_results
        if score >= settings.RAG_SCORE_THRESHOLD
    ]

    if not filtered:
        logger.info(
            "检索结果全低于阈值 %.2f: query=%s",
            settings.RAG_SCORE_THRESHOLD,
            query[:50],
        )
        return []

    logger.info(
        "Chroma 检索: %d 条原始结果, %d 条过滤后, 耗时: %.2fs",
        len(raw_results), len(filtered), time.time() - t0,
    )

    # 组装结果
    results = [
        RetrievalResult(
            content=doc.page_content,
            score=score,
            metadata=doc.metadata,
        )
        for doc, score in filtered
    ]

    return results
```

- [x] **Step 2: Update rag/ingestion/__init__.py — remove get_vectorstore export**

```python
# apps/service/rag/ingestion/__init__.py
"""RAG 文档摄取模块 — 负责文档加载、清洗、切片和向量化。"""

from rag.ingestion.pipeline import ingest_document
from rag.ingestion.vectorstore import delete_from_vectorstore

__all__ = [
    "ingest_document",
    "delete_from_vectorstore",
]
```

- [x] **Step 3: Update rag/__init__.py — remove get_vectorstore export**

```python
# apps/service/rag/__init__.py
"""RAG 模块 — 检索增强生成，覆盖文档摄取、检索、生成全链路。"""

from rag.ingestion import ingest_document, delete_from_vectorstore
from rag.retrieval import retrieve, RetrievalResult
from rag.generation import generate_answer, GenerationResult

__all__ = [
    "ingest_document",
    "delete_from_vectorstore",
    "retrieve",
    "RetrievalResult",
    "generate_answer",
    "GenerationResult",
]
```

- [x] **Step 4: Update services/knowledge.py — pass rag_llm to generate_answer**

In the `query_knowledge` function, change:

```python
    result = await generate_answer(question, chunks)
```

to:

```python
    from app.main import app
    rag_llm = app.state.registry.get("rag_llm")
    result = await generate_answer(question, chunks, rag_llm=rag_llm)
```

- [x] **Step 5: Commit**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/rag/retrieval/retriever.py apps/service/rag/ingestion/__init__.py apps/service/rag/__init__.py apps/service/services/knowledge.py
git commit -m "refactor: RAG chain gets vectorstore and rag_llm from Registry"
```

---

### Task 10: 集成验证

**Files:**
- No new files — manual verification

**Interfaces:**
- Consumes: 所有已重构的模块
- Produces: 验证通过

- [x] **Step 1: 启动服务验证懒加载**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001`
Expected: 启动日志显示 "创建 ConfigProvider 和 ComponentRegistry" 和 "启动完成"，无 eager 初始化 Agent 的日志

- [x] **Step 2: 首次 chat 请求触发懒加载**

发送 chat 请求，观察日志中出现组件初始化信息。
Expected: 首次请求时日志显示组件创建，后续请求直接使用已创建实例

- [x] **Step 3: 运行全部单元测试**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && python -m pytest tests/ -v`
Expected: ALL PASS

- [x] **Step 4: Commit (if any fixes were needed)**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add -A
git commit -m "fix: integration fixes from verification"
```
