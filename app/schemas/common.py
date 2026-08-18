"""通用出入参：分页封装。"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """统一分页响应：{total, page, size, items}。"""

    total: int
    page: int
    size: int
    items: List[T]
