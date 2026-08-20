import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vitals import Vitals
from app.repositories.base import BaseRepository


class VitalsRepository(BaseRepository[Vitals]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vitals)

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 100, offset: int = 0) -> Sequence[Vitals]:
        stmt = (
            select(Vitals)
            .where(Vitals.user_id == user_id)
            .order_by(Vitals.recorded_at.desc(), Vitals.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest(self, user_id: uuid.UUID) -> Vitals | None:
        stmt = (
            select(Vitals)
            .where(Vitals.user_id == user_id)
            .order_by(Vitals.recorded_at.desc(), Vitals.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
