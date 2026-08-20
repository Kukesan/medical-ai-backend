from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record_type import RecordType
from app.repositories.base import BaseRepository


class RecordTypeRepository(BaseRepository[RecordType]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RecordType)

    async def get_by_code(self, code: str) -> RecordType | None:
        result = await self.session.execute(
            select(RecordType).where(RecordType.code == code.upper(), RecordType.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_code_any_status(self, code: str) -> RecordType | None:
        result = await self.session.execute(select(RecordType).where(RecordType.code == code.upper()))
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[RecordType]:
        result = await self.session.execute(
            select(RecordType).where(RecordType.is_active.is_(True)).order_by(RecordType.code)
        )
        return result.scalars().all()
