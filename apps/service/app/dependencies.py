"""FastAPI 依赖注入 — 从 app.state 获取组件实例。"""

from fastapi import Request

from configs.provider import AsyncConfigProvider
from configs.registry import ComponentRegistry


def get_agent(request: Request):
    """获取 Agent 实例（同步，必须已初始化）。"""
    return request.app.state.registry.get("agent")


async def get_agent_async(request: Request):
    """获取 Agent 实例（异步，支持懒加载）。"""
    return await request.app.state.registry.ensure_initialized("agent")


def get_chroma_client(request: Request):
    """获取 Chroma Client 实例。"""
    return request.app.state.registry.get("chroma_client")


def get_config_provider(request: Request) -> AsyncConfigProvider:
    """获取 AsyncConfigProvider 实例。"""
    return request.app.state.config_provider


def get_registry(request: Request) -> ComponentRegistry:
    """获取 ComponentRegistry 实例。"""
    return request.app.state.registry
