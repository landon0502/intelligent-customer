from pydantic import BaseModel
from typing import Generic, TypeVar
T = TypeVar("T")

class PageResult(BaseModel, Generic[T]):
    list: list[T]
    total: int
    page: int
    page_size: int

