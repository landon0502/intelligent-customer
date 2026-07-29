from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from schemas.user import User
from utils.password import hash_password, verify_password
from configs.config import settings


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """根据用户名查询用户"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """验证用户名密码，成功返回 User，失败返回 None"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def register_user(db: AsyncSession, username: str, password: str) -> User:
    """创建新用户（默认 role='user'）"""
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def seed_admin_user(db: AsyncSession) -> None:
    """启动时检查 admin 用户是否存在，不存在则创建"""
    existing = await get_user_by_username(db, "admin")
    if not existing:
        admin = User(
            username="admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        await db.commit()
