"""
健康检查路由 —— 供 K8s / docker-compose 探活使用。
"""
from fastapi import APIRouter

from utils.response import success

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return success(data={"status": "ok"})
