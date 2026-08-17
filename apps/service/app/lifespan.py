"""应用生命周期管理 — 启动时创建 Provider + Registry，关闭时释放资源。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import mysql
from database.session import get_db, async_session_factory
from configs.config import settings
from configs.provider import AsyncConfigProvider
from configs.registry import ComponentRegistry

# 确保所有 ORM 模型被注册到 Base.metadata
import database.models  # noqa: F401

logging.basicConfig(
    level=getattr(logging, "INFO"),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("intelligent-customer")


async def _seed_initial_data() -> None:
    """初始化种子数据：创建管理员用户 + 企业业务"""
    from services.auth import seed_admin_user
    from services.enterprise import seed_enterprise_businesses

    async for db in get_db():
        await seed_admin_user(db)
        await seed_enterprise_businesses(db)


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
        # llm_config 在 ensure_initialized 时已缓存
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
    from configs.config import validate_security_defaults
    validate_security_defaults()

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
