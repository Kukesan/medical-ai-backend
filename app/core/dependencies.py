import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise UnauthorizedException("Missing authorization token")

    token = credentials.credentials
    try:
        payload = decode_token(token, refresh=False)
    except ValueError as exc:
        raise UnauthorizedException("Invalid access token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid access token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token subject")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise UnauthorizedException("Invalid token subject") from exc

    repo = UserRepository(session)
    user = await repo.get(user_uuid)
    if not user:
        raise UnauthorizedException("User not found")

    return user
