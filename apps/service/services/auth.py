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


async def list_users(db: AsyncSession) -> list[User]:
    """获取全部用户（按 id 升序，管理员使用）"""
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession, username: str, password: str, role: str = "user"
) -> User:
    """创建用户（管理员专用）——重复用户名/密码过短/非法角色抛 ValueError"""
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError("用户名已存在")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    if role not in {"user", "admin"}:
        raise ValueError("非法角色")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(
    db: AsyncSession, user_id: int, current_user_id: int
) -> bool | None:
    """删除用户（管理员专用）——目标不存在返回 None；删除保护抛 ValueError"""
    user = await db.get(User, user_id)
    if not user:
        return None
    if user.role == "admin":
        raise ValueError("不能删除管理员用户")
    if user.id == current_user_id:
        raise ValueError("不能删除当前登录用户")
    await db.delete(user)
    await db.commit()
    return True
