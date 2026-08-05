from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileCreateRequest, UserProfileResponse, UserProfileUpdateRequest


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_profile(self, user: User) -> UserProfileResponse:
        return UserProfileResponse.model_validate(user)

    async def create_profile(self, user: User, profile_data: UserProfileCreateRequest) -> UserProfileResponse:
        user.age = profile_data.age
        user.height = profile_data.height
        user.weight = profile_data.weight
        user.blood_group = profile_data.blood_group
        user.pressure = profile_data.pressure
        user.blood_sugar = profile_data.blood_sugar
        await self.session.commit()
        await self.session.refresh(user)
        return UserProfileResponse.model_validate(user)

    async def update_profile(self, user: User, profile_data: UserProfileUpdateRequest) -> UserProfileResponse:
        updates = profile_data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(user, field, value)
        await self.session.commit()
        await self.session.refresh(user)
        return UserProfileResponse.model_validate(user)
