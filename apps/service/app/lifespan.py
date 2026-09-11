"""应用生命周期管理 — 启动时创建 Provider + Registry，关闭时释放资源。"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
    from models.reranker import create_reranker
    from rag.ingestion.vectorstore import create_chroma_client, create_vectorstore
    from agent.factory import create_customer_agent, filter_tools
    from agent.prompts import build_system_prompt

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

    # 5.5 reranker — config_category: rerank
    #    默认关闭（rerank.enabled=false），启用时懒加载 Qwen3-Reranker 模型
    registry.register("reranker", create_reranker, "rerank")

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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化 Provider + Registry，关闭时释放资源。"""
    from configs.config import validate_security_defaults
    validate_security_defaults()
    logger.info("挂载data静态资源")
    _app.mount("/data", StaticFiles(directory="data"), name="data")
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

    # 预热：注册只建槽位、不创建实例，真正的实例化发生在首个请求
    # （app/dependencies.py 的 ensure_initialized）。若不预热，第一个 chat / 知识库
    # 请求会卡在本地 embedding 权重的载入上，而 /health 不碰 registry、健康检查照常通过，
    # 现象上就是"容器 healthy 但第一个请求超时"。
    # 失败只记日志、不阻断启动 —— 仍可退回懒加载路径，由请求时抛出具体错误。
    logger.info("预热组件（加载本地模型）...")
    started = time.monotonic()
    try:
        # "agent" 在注册顺序最后，会按依赖顺序把 embedding / chroma / vectorstore /
        # reranker 等前置组件一并创建。需要 Chroma 已就绪（compose 里由 depends_on 保证）。
        await registry.ensure_initialized("agent")

        # reranker 单独预热：它的模型是懒加载的（首次重排才载入），
        # enabled=false 时 warmup() 为空操作，保持"不启用则零成本"的设计。
        reranker = registry.get("reranker")
        if reranker.enabled:
            # 模型加载同步阻塞，丢到线程里避免卡住事件循环
            await asyncio.to_thread(reranker.warmup)

        logger.info("预热完成，耗时 %.1fs", time.monotonic() - started)
    except Exception as e:  # noqa: BLE001 —— 预热失败不应导致服务起不来
        logger.error(
            "预热失败（耗时 %.1fs），将在首次请求时重试: %s",
            time.monotonic() - started,
            e,
        )

    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield

    logger.info("关闭中...")
    await mysql.engine.dispose()
    logger.info("已关闭")
