"""
统一响应工具模块 —— 所有接口返回统一格式 { code, message, data }，
便于前端统一处理。
"""
from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """标准响应模型 —— 用于 Swagger 文档生成"""

    code: int = 0
    message: str = "success"
    data: Any = None


def success(data: Any = None, message: str = "success") -> dict:
    """成功响应快捷函数"""
    return {"code": 0, "message": message, "data": data}


def error(code: int = 400, message: str = "error", data: Any = None) -> dict:
    """失败响应快捷函数"""
    return {"code": code, "message": message, "data": data}
