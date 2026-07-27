from datetime import datetime, timezone, timedelta

import jwt

from app.core.config import settings


def create_token(user_id: int, username: str, role: str) -> str:
    """生成 HS256 JWT，payload 包含 sub(user_id)、username、role、exp"""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    """验证 JWT 签名和有效期，返回 payload 或抛出异常"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_sub": False})
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token 已过期")
    except jwt.InvalidTokenError:
        raise ValueError("无效的 Token")
