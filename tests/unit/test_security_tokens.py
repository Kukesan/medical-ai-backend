from app.core.security import create_access_token, create_refresh_token, decode_token


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token("user-xyz")
    payload = decode_token(token, refresh=True)

    assert payload["sub"] == "user-xyz"
    assert payload["type"] == "refresh"
