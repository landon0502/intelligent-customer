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
