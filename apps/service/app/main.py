"""
应用入口 —— FastAPI 实例创建、中间件注册、路由挂载、连接池生命周期管理。
启动命令: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import health_router, auth_router
from app.core.config import settings
from app.db.session import engine, Base
from app.services.auth import seed_admin_user
from app.db.session import async_session_factory

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
    logger.info("启动中...  创建数据库表")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("启动中...  初始化 admin 用户")
    async with async_session_factory() as session:
        await seed_admin_user(session)
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...")
    await engine.dispose()
    logger.info("已关闭")

# ==== FastAPI 实例 ====

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(health_router)
app.include_router(auth_router)
