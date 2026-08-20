import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_session
from app.core.exceptions import ForbiddenException, NotFoundException
from app.main import app
from app.models.user import User
from app.services.medical_record_service import MedicalRecordService


async def _fake_session() -> AsyncGenerator[None, None]:
    yield None


def _fake_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="reviewer@example.com",
        full_name="Reviewer",
        hashed_password="hashed",
        is_active=True,
    )


def test_get_medical_record_requires_auth() -> None:
    app.dependency_overrides[get_session] = _fake_session
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/medical-records/{uuid.uuid4()}")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_get_medical_record_returns_403_for_other_users_record(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self, user_id, record_id):
        raise ForbiddenException("You do not have access to this medical record")

    monkeypatch.setattr(MedicalRecordService, "get", fake_get)
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_session] = _fake_session
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/medical-records/{uuid.uuid4()}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_get_medical_record_returns_404_for_missing_record(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self, user_id, record_id):
        raise NotFoundException("Medical record not found")

    monkeypatch.setattr(MedicalRecordService, "get", fake_get)
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_session] = _fake_session
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/medical-records/{uuid.uuid4()}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
