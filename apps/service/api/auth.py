from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from database import session
from schemas.user import User
from services.auth import authenticate_user, register_user, get_user_by_username
from utils.jwt import create_token
from utils.response import success, error
from auth.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("用户名不能为空")
        if len(v) > 20:
            raise ValueError("用户名最多20位")
        if not v.replace("_", "").isalnum():
            raise ValueError("用户名仅支持字母数字下划线")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少6位")
        return v


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(session.get_db)):
    user = await authenticate_user(db, req.username, req.password)
    if not user:
        return error(code=30001, message="用户名或密码错误")
    token = create_token(user_id=user.id, username=user.username, role=user.role)
    return success(data={
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    })


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(session.get_db)):
    existing = await get_user_by_username(db, req.username)
    if existing:
        return error(code=30002, message="用户名已存在")
    user = await register_user(db, req.username, req.password)
    token = create_token(user_id=user.id, username=user.username, role=user.role)
    return success(data={
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    })


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success(data={
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    })
