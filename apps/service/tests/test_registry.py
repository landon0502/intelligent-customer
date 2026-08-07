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
async def test_registry_refresh_category_partial_failure_keeps_successful():
    """refresh_category() 逐个替换：成功的立即生效，失败的保留旧实例。"""
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

    # agent_llm 成功替换，agent 失败保留旧实例
    assert result == {"agent_llm": True, "agent": False}
    assert registry.get("agent_llm") == "new_llm"
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


@pytest.mark.anyio
async def test_registry_refresh_category_factory_sees_replaced_dependency():
    """refresh_category() 逐个替换时，后续工厂闭包通过 get() 获取已替换的前置组件。"""
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value={"llm.model": "deepseek-v4-pro"})

    factory_llm = MagicMock(side_effect=["old_llm", "new_llm"])

    # agent 工厂闭包通过 registry.get("agent_llm") 获取依赖
    def _agent_factory(config):
        llm = registry.get("agent_llm")
        return f"agent_with_{llm}"

    registry = ComponentRegistry(mock_provider)
    registry.register("agent_llm", factory_llm, "llm")
    registry.register("agent", _agent_factory, "llm")

    # 初始化
    await registry.ensure_initialized("agent_llm")
    await registry.ensure_initialized("agent")
    assert registry.get("agent") == "agent_with_old_llm"

    # 刷新分类 — agent 工厂应获取已替换的 new_llm
    result = await registry.refresh_category("llm")

    assert result == {"agent_llm": True, "agent": True}
    assert registry.get("agent_llm") == "new_llm"
    assert registry.get("agent") == "agent_with_new_llm"
