import math
from typing import TypeVar, List
from app.schemas.base import PaginatedResponse

DataT = TypeVar("DataT")


def paginate(
    items: List[DataT],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[DataT]:
    pages = math.ceil(total / page_size) if page_size > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def get_skip(page: int, page_size: int) -> int:
    """Convert page/page_size to a DB offset (skip)."""
    return (page - 1) * page_size
