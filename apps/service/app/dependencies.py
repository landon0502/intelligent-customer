from fastapi import Request


def get_agent(request: Request):
    """获取 Agent 实例。"""
    return request.app.state.agent


def get_chroma_client_from_app(request: Request):
    """获取 Chroma Client 实例。"""
    return request.app.state.chroma_client
