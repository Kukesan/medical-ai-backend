from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.user import UserProfileCreateRequest, UserProfileResponse, UserProfileUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users")


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    service = UserService(session)
    return await service.get_profile(user)


@router.post("/me/profile", response_model=UserProfileResponse)
async def create_my_profile(
    profile_data: UserProfileCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)
    return await service.create_profile(user, profile_data)


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    profile_data: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)
    return await service.update_profile(user, profile_data)
