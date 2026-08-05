import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.lab_result import LabResult
from app.models.medical_visit import MedicalVisit
from app.repositories.base import BaseRepository


class LabResultRepository(BaseRepository[LabResult]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LabResult)

    async def list_by_visit_id(self, visit_id: uuid.UUID) -> Sequence[LabResult]:
        result = await self.session.execute(
            select(LabResult).where(LabResult.visit_id == visit_id)
        )
        return result.scalars().all()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[LabResult]:
        result = await self.session.execute(
            select(LabResult)
            .join(MedicalVisit, LabResult.visit_id == MedicalVisit.id)
            .where(MedicalVisit.user_id == user_id)
            .options(joinedload(LabResult.visit))
        )
        return result.scalars().all()
