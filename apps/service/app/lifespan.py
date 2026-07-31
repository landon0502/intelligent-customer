from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from database import mysql
from database.session import get_db
from configs.config import settings
from agent.factory import create_customer_agent
from rag.ingestion.vectorstore import create_chroma_client

# 确保所有 ORM 模型被注册到 Base.metadata
import database.models  # noqa: F401

# 日志
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化连接池及 Provider 注册，关闭时释放资源"""
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
    logger.info("初始化 Chroma 连接...")
    try:
        client = create_chroma_client({})
        client.heartbeat()
        _app.state.chroma_client = client
        logger.info("Chroma 连接成功: %s:%s", settings.CHROMA_HOST, settings.CHROMA_PORT)
    except Exception as e:
        logger.warning("Chroma 连接失败: %s，RAG 功能暂不可用", e)
        _app.state.chroma_client = None
    logger.info("初始化agent...")
    _app.state.agent = create_customer_agent()
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...")
    await mysql.engine.dispose()
    logger.info("已关闭")
