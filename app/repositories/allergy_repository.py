import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy
from app.repositories.base import BaseRepository


class AllergyRepository(BaseRepository[Allergy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Allergy)

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[Allergy]:
        result = await self.session.execute(
            select(Allergy).where(Allergy.user_id == user_id).order_by(Allergy.created_at.desc())
        )
        return result.scalars().all()
