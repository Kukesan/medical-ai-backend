from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user
from app.core.exceptions import UnauthorizedException


@pytest.mark.asyncio
async def test_get_current_user_rejects_non_uuid_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.dependencies.decode_token",
        lambda _token, refresh=False: {"type": "access", "sub": "not-a-uuid"},
    )

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    session = AsyncMock()

    with pytest.raises(UnauthorizedException, match="Invalid token subject"):
        await get_current_user(credentials=credentials, session=session)
