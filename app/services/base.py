from typing import Any, Dict, Generic, List, Optional, TypeVar

from app.repositories.base import BaseRepository

RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService(Generic[RepositoryType]):
    """Generic base service that wraps a repository."""

    def __init__(self, repository: RepositoryType):
        self.repository = repository

    async def get_by_id(self, id: Any) -> Optional[Any]:
        return await self.repository.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Any]:
        return await self.repository.get_all(skip=skip, limit=limit)

    async def count(self) -> int:
        return await self.repository.count()

    async def create(self, data: Dict[str, Any]) -> Any:
        return await self.repository.create(data)

    async def update(self, db_obj: Any, data: Dict[str, Any]) -> Any:
        return await self.repository.update(db_obj, data)

    async def delete(self, db_obj: Any) -> None:
        await self.repository.delete(db_obj)
