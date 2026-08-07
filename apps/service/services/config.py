"""系统配置业务逻辑 —— 读写配置、动态生效。"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.system_config import SystemConfig

logger = logging.getLogger("intelligent-customer.config")

# ========== 默认配置 ==========

DEFAULT_CONFIGS: dict[str, dict] = {
    # LLM
    "llm.provider": {
        "value": "deepseek",
        "category": "llm",
        "description": "LLM 提供商（deepseek/openai/zhipu）",
    },
    "llm.model": {
        "value": "deepseek-v4-pro",
        "category": "llm",
        "description": "LLM 模型名称",
    },
    "llm.api_key": {"value": "", "category": "llm", "description": "API Key"},
    "llm.base_url": {"value": "", "category": "llm", "description": "API Base URL"},
    "llm.temperature": {"value": "0.7", "category": "llm", "description": "生成温度"},
    "llm.max_tokens": {
        "value": "512",
        "category": "llm",
        "description": "最大输出 Token",
    },
    "llm.timeout": {"value": "15", "category": "llm", "description": "超时时间(秒)"},
    "llm.max_retries": {"value": "1", "category": "llm", "description": "最大重试次数"},
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
    # Embedding
    "embedding.provider": {
        "value": "local",
        "category": "embedding",
        "description": "Embedding 提供商（local/zhipu/openai）",
    },
    "embedding.model": {
        "value": "BAAI/bge-base-zh-v1.5",
        "category": "embedding",
        "description": "Embedding 模型名称",
    },
    "embedding.dimensions": {
        "value": "768",
        "category": "embedding",
        "description": "向量维度",
    },
    # 向量数据库
    "vectorstore.provider": {
        "value": "chroma",
        "category": "vectorstore",
        "description": "向量数据库类型",
    },
    "vectorstore.host": {
        "value": "localhost",
        "category": "vectorstore",
        "description": "主机地址",
    },
    "vectorstore.port": {
        "value": "8000",
        "category": "vectorstore",
        "description": "端口",
    },
    "vectorstore.collection": {
        "value": "knowledge_base",
        "category": "vectorstore",
        "description": "集合名称",
    },
}


async def init_default_configs(db: AsyncSession) -> None:
    """初始化默认配置（仅插入不存在的键）。"""
    for key, cfg in DEFAULT_CONFIGS.items():
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        if result.scalar_one_or_none() is None:
            db.add(
                SystemConfig(
                    key=key,
                    value=cfg["value"],
                    category=cfg["category"],
                    description=cfg["description"],
                )
            )
    await db.commit()
    logger.info("默认配置初始化完成")


async def get_all_configs(db: AsyncSession) -> list[SystemConfig]:
    """获取所有配置项。"""
    result = await db.execute(
        select(SystemConfig).order_by(SystemConfig.category, SystemConfig.key)
    )
    return list(result.scalars().all())


async def get_configs_by_category(
    db: AsyncSession, category: str
) -> list[SystemConfig]:
    """按分类获取配置项。"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.category == category)
    )
    return list(result.scalars().all())


async def get_config_value(db: AsyncSession, key: str) -> str | None:
    """获取单个配置值。"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    return config.value if config else None


api_key_placeholder = "*" * 16


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
        if "api_key" in item["key"] and item.get("value") == api_key_placeholder:
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
                logger.info("分类 %s 刷新成功: %s", category, ", ".join(success_names))
            if fail_names:
                logger.warning(
                    "分类 %s 刷新失败（旧组件继续服务）: %s",
                    category,
                    ", ".join(fail_names),
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
