import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vaccination import Vaccination
from app.repositories.base import BaseRepository


class VaccinationRepository(BaseRepository[Vaccination]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vaccination)

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[Vaccination]:
        result = await self.session.execute(
            select(Vaccination).where(Vaccination.user_id == user_id).order_by(Vaccination.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_user_and_id(self, user_id: uuid.UUID, vaccination_id: uuid.UUID) -> Vaccination | None:
        result = await self.session.execute(
            select(Vaccination).where(Vaccination.user_id == user_id, Vaccination.id == vaccination_id)
        )
        return result.scalar_one_or_none()