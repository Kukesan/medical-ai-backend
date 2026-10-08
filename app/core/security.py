from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _normalize_password(password: str) -> str:
    return password


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def _create_token(subject: str, token_type: str, expires_delta: timedelta, secret: str, extra: dict) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        **extra,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, token_version: int = 0) -> str:
    return _create_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        secret=settings.jwt_secret_key,
        extra={"ver": token_version},
    )


def create_refresh_token(subject: str, token_version: int = 0, auth_time: int | None = None) -> str:
    """`auth_time` is when the user last entered their password; refreshing keeps it, so a session has a hard end."""
    return _create_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        secret=settings.jwt_refresh_secret_key,
        extra={"ver": token_version, "auth_time": auth_time or int(datetime.now(UTC).timestamp())},
    )


def decode_token(token: str, refresh: bool = False) -> dict:
    secret = settings.jwt_refresh_secret_key if refresh else settings.jwt_secret_key
    try:
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid token") from exc
