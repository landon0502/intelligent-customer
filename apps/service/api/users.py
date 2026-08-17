"""用户管理接口 —— 列表、创建、删除（仅管理员）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.user_schema import UserItem
from auth.security import get_current_user
from services.auth import list_users, create_user, delete_user
from utils.response import success, error

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


@router.get("")
async def list_users_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看用户列表")
    users = await list_users(db)
    items = [UserItem.model_validate(u) for u in users]
    return success(data=items)


@router.post("")
async def create_user_endpoint(
    req: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（管理员权限）——业务校验错误统一 40004"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可创建用户")
    try:
        user = await create_user(db, req.username, req.password, req.role)
    except ValueError as e:
        return error(code=40004, message=str(e))
    return success(data=UserItem.model_validate(user))


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（管理员权限）——目标不存在 40005，删除保护 ValueError 40004"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可删除用户")
    try:
        deleted = await delete_user(db, user_id, current_user.id)
    except ValueError as e:
        return error(code=40004, message=str(e))
    if deleted is None:
        return error(code=40005, message="用户不存在")
    return success(data={"success": True})
