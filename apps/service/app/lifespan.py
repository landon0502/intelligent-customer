from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from database import mysql
from configs.config import settings
from agent.factory import create_customer_agent
# 日志
logging.basicConfig(
    level=getattr(logging, "INFO"),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai-service")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化连接池及 Provider 注册，关闭时释放资源"""
    logger.info("启动中...  创建数据库表")
    async with mysql.engine.begin() as conn:
        await conn.run_sync(mysql.Base.metadata.create_all)
    logger.info("初始化agent...")
    _app.state.agent = create_customer_agent()
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...")
    await mysql.engine.dispose()
    logger.info("已关闭")

