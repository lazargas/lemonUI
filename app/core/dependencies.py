from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user_id(authorization: str = Header(...)) -> str:
    """Dependency to extract and validate the current user from JWT token."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException("Invalid authorization header")
    user_id = decode_access_token(token)
    if not user_id:
        raise UnauthorizedException("Invalid or expired token")
    return user_id
