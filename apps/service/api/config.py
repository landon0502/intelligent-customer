"""系统配置接口 — 获取/更新配置，更新后动态生效并返回刷新状态。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.system_config_schema import ConfigItem, ConfigUpdateRequest
from auth.security import get_current_user
from services.config import (
    get_all_configs,
    get_configs_by_category,
    update_configs,
    api_key_placeholder,
)
from app.dependencies import get_registry
from utils.response import success, error

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def list_configs(
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取配置列表，可按分类筛选"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看配置")

    if category:
        configs = await get_configs_by_category(db, category)
    else:
        configs = await get_all_configs(db)

    items = [ConfigItem.model_validate(c) for c in configs]

    # API Key 脱敏：不返回明文，只标记是否已设置
    for item in items:
        if "api_key" in item.key and item.value:
            item.value = api_key_placeholder

    return success(data=items)


@router.put("")
async def update_config(
    req: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry=Depends(get_registry),
):
    """批量更新配置项（管理员权限），更新后自动动态生效。

    返回刷新状态：哪些组件已刷新、是否有刷新失败。
    """
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可修改配置")

    refresh_result = await update_configs(
        db, [c.model_dump() for c in req.configs], registry
    )
    return success(
        data={
            "updated": len(req.configs),
            "refresh_result": refresh_result,
        }
    )
