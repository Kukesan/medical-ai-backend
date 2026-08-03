import pytest

from app.core.security import get_password_hash, verify_password


@pytest.mark.parametrize(
    ("password"),
    [
        "StrongPassword123",
        "very-long-password-that-exceeds-the-bcrypt-72-byte-limit-and-should-still-hash",
    ],
)
def test_password_hashing_and_verification(password: str) -> None:
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
