"""
应用入口 —— FastAPI 实例创建、中间件注册、路由挂载、连接池生命周期管理。
启动命令: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
"""
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import health_router
from app.core.config import settings

# 日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai-service")


# ==== 应用生命周期 ====

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化连接池及 Provider 注册，关闭时释放资源"""
    logger.info("启动中...  Provider 注册")
    # init_providers()
    logger.info("启动中...  Redis 连接池初始化")
    # await redis_client.connect()
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...  Redis 连接池释放")
    # await redis_client.disconnect()
    logger.info("已关闭")

# ==== FastAPI 实例 ====

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 路由
app.include_router(health_router)