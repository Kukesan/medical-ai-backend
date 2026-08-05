import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.surgery import Surgery
from app.repositories.base import BaseRepository


class SurgeryRepository(BaseRepository[Surgery]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Surgery)

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[Surgery]:
        result = await self.session.execute(
            select(Surgery).where(Surgery.user_id == user_id).order_by(Surgery.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_user_and_id(self, user_id: uuid.UUID, surgery_id: uuid.UUID) -> Surgery | None:
        result = await self.session.execute(
            select(Surgery).where(Surgery.user_id == user_id, Surgery.id == surgery_id)
        )
        return result.scalar_one_or_none()