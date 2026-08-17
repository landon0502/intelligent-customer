"""
应用入口 —— FastAPI 实例创建、中间件注册、路由挂载、连接池生命周期管理。
启动命令: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import health_router, auth_router, chat_router, conversations_router, knowledge_router, config_router, enterprise_router, tickets_router, users_router, tools_router
from .lifespan import lifespan
from configs.config import settings
# ==== FastAPI 实例 ====

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 解决跨域问题
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
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(knowledge_router)
app.include_router(config_router)
app.include_router(enterprise_router)
app.include_router(tickets_router)
app.include_router(users_router)
app.include_router(tools_router)
