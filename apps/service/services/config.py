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


async def update_configs(db: AsyncSession, configs: list[dict]) -> None:
    """批量更新配置项，并触发动态生效。

    Args:
        configs: 配置项列表，每项包含 key 和 value
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
    if changed_categories:
        await _apply_config_changes(changed_categories)


async def _apply_config_changes(categories: set[str]) -> None:
    """配置变更后，通过 Registry 重建对应组件。"""
    try:
        from app.main import app
        registry = app.state.registry
    except Exception:
        logger.warning("无法获取 Registry，跳过配置动态生效")
        return

    if "llm" in categories:
        registry.rebuild("agent_llm")
        # 重建 Agent：旧的 Agent 持有旧的 LLM 实例，必须重建
        _rebuild_agent(categories)
        logger.info("LLM 配置已变更，Agent 已重建")

    if "embedding" in categories:
        registry.rebuild("embeddings")
        registry.rebuild("vectorstore")
        logger.info("Embedding 配置已变更，组件已重建")

    if "vectorstore" in categories:
        registry.rebuild("vectorstore")
        logger.info("向量数据库配置已变更，组件已重建")


def _rebuild_agent(categories: set[str]) -> None:
    """重建 FastAPI app.state 中的 Agent 实例。"""
    try:
        from app.main import app
        from agent.factory import create_customer_agent

        app.state.agent = create_customer_agent()
    except Exception as e:
        logger.warning("重建 Agent 失败: %s", e)
