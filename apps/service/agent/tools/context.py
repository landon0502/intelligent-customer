"""工具上下文 —— 通过 ContextVar 注入当前请求的用户/会话，供 async 工具读取。

Agent 为懒加载单例，工具无法接收请求级参数；
由 api/chat.py 的 chat_stream 在 astream 前后 set/reset。
"""

from contextvars import ContextVar

_current_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
_current_conversation_id: ContextVar[int | None] = ContextVar(
    "conversation_id", default=None
)


def set_user_context(user_id: int | None, conversation_id: int | None) -> None:
    """设置当前请求的用户与会话上下文。"""
    _current_user_id.set(user_id)
    _current_conversation_id.set(conversation_id)


def reset_user_context() -> None:
    """清空当前请求的用户与会话上下文（防跨请求泄漏）。"""
    _current_user_id.set(None)
    _current_conversation_id.set(None)


def get_current_user_id() -> int | None:
    """读取当前用户 ID；ContextVar 未注入时返回 None。"""
    return _current_user_id.get()


def get_current_conversation_id() -> int | None:
    """读取当前会话 ID；ContextVar 未注入时返回 None。"""
    return _current_conversation_id.get()
