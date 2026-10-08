import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException, ValidationException
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair, UserCreate

# Verified against when the email is unknown, so a login takes the same time whether or not the account exists.
_DUMMY_PASSWORD_HASH = get_password_hash("dummy-password-for-timing")


def issue_tokens(user: User, auth_time: int | None = None) -> TokenPair:
    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject, user.token_version),
        refresh_token=create_refresh_token(subject, user.token_version, auth_time),
    )


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, payload: UserCreate) -> User:
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise ConflictException("An account with this email already exists")

        user = User(
            email=payload.email,
            full_name=payload.full_name.strip(),
            hashed_password=get_password_hash(payload.password),
            terms_accepted_at=datetime.now(UTC),
        )
        await self.repo.create(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.repo.get_by_email(email)
        password_ok = verify_password(password, user.hashed_password if user else _DUMMY_PASSWORD_HASH)
        if not user or not password_ok:
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise ForbiddenException("This account has been disabled")

        return issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, refresh=True)
        except ValueError as exc:
            raise UnauthorizedException("Invalid refresh token") from exc

        if payload.get("type") != TokenType.REFRESH:
            raise UnauthorizedException("Invalid refresh token")

        try:
            user_id = uuid.UUID(str(payload.get("sub")))
        except ValueError as exc:
            raise UnauthorizedException("Invalid refresh token subject") from exc

        user = await self.repo.get(user_id)
        if not user or not user.is_active or payload.get("ver") != user.token_version:
            raise UnauthorizedException("Session is no longer valid")

        auth_time = payload.get("auth_time")
        session_deadline = datetime.now(UTC) - timedelta(days=settings.session_max_age_days)
        if not isinstance(auth_time, int) or datetime.fromtimestamp(auth_time, UTC) < session_deadline:
            raise UnauthorizedException("Session expired, please sign in again")

        return issue_tokens(user, auth_time=auth_time)

    async def logout(self, user: User) -> None:
        """Revokes every token issued to this user (all devices)."""
        user.token_version += 1
        await self.session.commit()

    async def change_password(self, user: User, current_password: str, new_password: str) -> TokenPair:
        # 403, not 401: the session is valid, so the client must not treat this as an expired token.
        if not verify_password(current_password, user.hashed_password):
            raise ForbiddenException("Current password is incorrect")
        if current_password == new_password:
            raise ValidationException("New password must be different from the current password")

        user.hashed_password = get_password_hash(new_password)
        user.token_version += 1  # sign out every other device
        await self.session.commit()
        await self.session.refresh(user)
        return issue_tokens(user)
