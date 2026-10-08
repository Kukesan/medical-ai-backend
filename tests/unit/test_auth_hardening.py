import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.schemas.auth import UserCreate, UserLogin
from app.services.auth_service import AuthService


def _user(**overrides) -> SimpleNamespace:
    values = {
        "id": uuid.uuid4(),
        "email": "jane@example.com",
        "hashed_password": get_password_hash("correct-password"),
        "is_active": True,
        "token_version": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _service_with_user(user) -> AuthService:
    service = AuthService(AsyncMock())
    service.repo = AsyncMock()
    service.repo.get.return_value = user
    service.repo.get_by_email.return_value = user
    return service


async def _current_user_for(token: str, user) -> object:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none = lambda: user
    return await get_current_user(credentials=credentials, session=session)


@pytest.mark.asyncio
async def test_access_token_rejected_after_token_version_bump() -> None:
    user = _user(token_version=1)
    token = create_access_token(str(user.id), token_version=0)

    with pytest.raises(UnauthorizedException, match="no longer valid"):
        await _current_user_for(token, user)


@pytest.mark.asyncio
async def test_access_token_rejected_for_disabled_user() -> None:
    user = _user(is_active=False)
    token = create_access_token(str(user.id), token_version=0)

    with pytest.raises(UnauthorizedException):
        await _current_user_for(token, user)


@pytest.mark.asyncio
async def test_access_token_accepted_for_current_version() -> None:
    user = _user(token_version=3)
    token = create_access_token(str(user.id), token_version=3)

    assert await _current_user_for(token, user) is user


@pytest.mark.asyncio
async def test_refresh_with_garbage_token_is_401_not_500() -> None:
    with pytest.raises(UnauthorizedException):
        await _service_with_user(None).refresh("not-a-jwt")


@pytest.mark.asyncio
async def test_refresh_rejects_revoked_version() -> None:
    user = _user(token_version=2)
    token = create_refresh_token(str(user.id), token_version=1)

    with pytest.raises(UnauthorizedException, match="no longer valid"):
        await _service_with_user(user).refresh(token)


@pytest.mark.asyncio
async def test_refresh_enforces_absolute_session_age() -> None:
    user = _user()
    long_ago = int((datetime.now(UTC) - timedelta(days=60)).timestamp())
    token = create_refresh_token(str(user.id), token_version=0, auth_time=long_ago)

    with pytest.raises(UnauthorizedException, match="expired"):
        await _service_with_user(user).refresh(token)


@pytest.mark.asyncio
async def test_refresh_keeps_original_auth_time() -> None:
    from app.core.security import decode_token

    user = _user()
    started = int((datetime.now(UTC) - timedelta(days=3)).timestamp())
    token = create_refresh_token(str(user.id), token_version=0, auth_time=started)

    pair = await _service_with_user(user).refresh(token)

    assert decode_token(pair.refresh_token, refresh=True)["auth_time"] == started


@pytest.mark.asyncio
async def test_login_rejects_disabled_account() -> None:
    service = _service_with_user(_user(is_active=False))

    with pytest.raises(ForbiddenException):
        await service.login("jane@example.com", "correct-password")


@pytest.mark.asyncio
async def test_register_duplicate_email_is_conflict() -> None:
    service = _service_with_user(_user())
    payload = UserCreate(email="Jane@Example.com", full_name="Jane", password="long-enough", accept_terms=True)

    with pytest.raises(ConflictException):
        await service.register(payload)


def test_emails_are_normalized_to_lowercase() -> None:
    assert UserLogin(email="  Jane@Example.COM ", password="x").email == "jane@example.com"


def test_register_requires_terms_acceptance() -> None:
    with pytest.raises(ValidationError, match="Terms"):
        UserCreate(email="jane@example.com", full_name="Jane", password="long-enough", accept_terms=False)
