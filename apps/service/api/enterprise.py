"""企业业务接口 —— 业务列表与单业务查询（登录即可访问）。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from auth.security import get_current_user
from services.enterprise import list_businesses, get_business_by_code
from utils.response import success, error

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


class EnterpriseBizItem(BaseModel):
    """企业业务响应模型"""
    id: int
    code: str
    name: str
    description: str
    requirements: str
    process: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/businesses")
async def list_businesses_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取企业业务列表（登录即可）"""
    businesses = await list_businesses(db)
    items = [EnterpriseBizItem.model_validate(b).model_dump() for b in businesses]
    return success(data=items)


@router.get("/businesses/{code}")
async def get_business_api(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按业务编号查询单条业务（登录即可）"""
    biz = await get_business_by_code(db, code.upper())
    if not biz:
        return error(code=40006, message=f"未找到业务编号 {code}")
    return success(data=EnterpriseBizItem.model_validate(biz).model_dump())
