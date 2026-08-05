import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.medication import Medication
from app.models.medical_visit import MedicalVisit
from app.repositories.base import BaseRepository


class MedicationRepository(BaseRepository[Medication]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Medication)

    async def list_by_visit_id(self, visit_id: uuid.UUID) -> Sequence[Medication]:
        result = await self.session.execute(
            select(Medication).where(Medication.visit_id == visit_id)
        )
        return result.scalars().all()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[Medication]:
        result = await self.session.execute(
            select(Medication)
            .join(MedicalVisit, Medication.visit_id == MedicalVisit.id)
            .where(MedicalVisit.user_id == user_id)
            .options(joinedload(Medication.visit))
        )
        return result.scalars().all()
