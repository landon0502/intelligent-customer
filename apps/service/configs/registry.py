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

        按注册顺序初始化目标组件及其所有前置组件。
        注册顺序保证依赖组件先初始化：agent_llm 在 agent 之前，
        embeddings 在 vectorstore 之前。

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
            # 按注册顺序初始化所有未初始化的前置组件（包括自身）
            for comp_name in self._order:
                comp_slot = self._slots[comp_name]
                if not comp_slot._initialized:
                    config = await self._provider.get_category(comp_slot._config_category)
                    comp_slot.create(config)
                if comp_name == name:
                    break
        return slot.get()

    async def refresh(self, name: str) -> bool:
        """刷新单个组件。

        读取最新配置，创建新实例并替换。失败时保留旧实例。
        刷新前先确保该组件已初始化（懒加载场景）。

        Args:
            name: 组件名称

        Returns:
            是否刷新成功
        """
        slot = self._slots.get(name)
        if slot is None:
            return False
        # 确保组件已初始化（处理首次 refresh 前未 ensure_initialized 的情况）
        if not slot._initialized:
            await self.ensure_initialized(name)
            return True  # 首次初始化成功即视为刷新成功
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
