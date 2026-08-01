from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserOut)
async def register(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> UserOut:
    service = AuthService(session)
    user = await service.register(payload)
    return UserOut.model_validate({
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
    })


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, session: AsyncSession = Depends(get_session)) -> TokenPair:
    service = AuthService(session)
    return await service.login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshTokenRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    service = AuthService(session)
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def current_user(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }
    )
