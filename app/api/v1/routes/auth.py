from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.rate_limiter import AUTH_LIMIT, AUTH_REFRESH_LIMIT, limiter
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


def _user_out(user: User) -> UserOut:
    return UserOut.model_validate(
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }
    )


# `request` is required by slowapi's per-route limits.
@router.post("/register", response_model=UserOut)
@limiter.limit(AUTH_LIMIT)
async def register(request: Request, payload: UserCreate, session: AsyncSession = Depends(get_session)) -> UserOut:
    service = AuthService(session)
    user = await service.register(payload)
    return _user_out(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit(AUTH_LIMIT)
async def login(request: Request, payload: UserLogin, session: AsyncSession = Depends(get_session)) -> TokenPair:
    service = AuthService(session)
    return await service.login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def refresh(
    request: Request, payload: RefreshTokenRequest, session: AsyncSession = Depends(get_session)
) -> TokenPair:
    service = AuthService(session)
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Response:
    """Revokes all of the user's tokens, signing them out on every device."""
    await AuthService(session).logout(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", response_model=TokenPair)
@limiter.limit(AUTH_LIMIT)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """Returns a fresh token pair for this device; tokens on other devices stop working."""
    return await AuthService(session).change_password(user, payload.current_password, payload.new_password)


@router.get("/me", response_model=UserOut)
async def current_user(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
