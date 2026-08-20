import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.vitals import Vitals
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.vitals import VitalsCreateRequest, VitalsUpdateRequest


class VitalsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VitalsRepository(session)

    async def create(self, user_id: uuid.UUID, data: VitalsCreateRequest) -> Vitals:
        vitals = Vitals(user_id=user_id, **data.model_dump())
        await self.repo.create(vitals)
        await self.session.commit()
        await self.session.refresh(vitals)
        return vitals

    async def get(self, user_id: uuid.UUID, vitals_id: uuid.UUID) -> Vitals:
        vitals = await self.repo.get(vitals_id)
        if vitals is None:
            raise NotFoundException("Vitals entry not found")
        if vitals.user_id != user_id:
            raise ForbiddenException("You do not have access to this vitals entry")
        return vitals

    async def list(self, user_id: uuid.UUID, limit: int = 100, offset: int = 0) -> Sequence[Vitals]:
        return await self.repo.list_by_user(user_id, limit=limit, offset=offset)

    async def get_latest(self, user_id: uuid.UUID) -> Vitals | None:
        return await self.repo.get_latest(user_id)

    async def update(self, user_id: uuid.UUID, vitals_id: uuid.UUID, data: VitalsUpdateRequest) -> Vitals:
        vitals = await self.get(user_id, vitals_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(vitals, field, value)
        await self.session.commit()
        await self.session.refresh(vitals)
        return vitals

    async def delete(self, user_id: uuid.UUID, vitals_id: uuid.UUID) -> None:
        vitals = await self.get(user_id, vitals_id)
        await self.repo.delete(vitals)
        await self.session.commit()
