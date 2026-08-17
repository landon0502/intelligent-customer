"""工具启停接口 —— 列表与启停切换（仅管理员）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from auth.security import get_current_user
from services.tools import (
    list_tool_states,
    update_tool_state,
    UnknownToolError,
    GuardedToolError,
)
from agent.prompts import TOOL_DESCRIPTIONS
from app.dependencies import get_config_provider, get_registry
from utils.response import success, error

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolUpdateRequest(BaseModel):
    enabled: bool


@router.get("")
async def list_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取工具启停状态列表（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工具")
    states = await list_tool_states(db)
    items = [
        {
            "name": name,
            "description": TOOL_DESCRIPTIONS.get(name, ""),
            "enabled": value == "enabled",
        }
        for name, value in states.items()
    ]
    return success(data=items)


@router.patch("/{name}")
async def update_tool(
    name: str,
    req: ToolUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider=Depends(get_config_provider),
    registry=Depends(get_registry),
):
    """启停工具（管理员权限）—— 兜底禁用 40004、未知工具 40005"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可修改工具")
    try:
        tool_name, enabled, refresh_ok = await update_tool_state(
            db, name, req.enabled, provider, registry
        )
    except GuardedToolError as e:
        return error(code=40004, message=str(e))
    except UnknownToolError as e:
        return error(code=40005, message=str(e))
    return success(
        data={"name": tool_name, "enabled": enabled, "refresh_ok": refresh_ok}
    )
