import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_visit import MedicalVisit
from app.repositories.base import BaseRepository


class VisitRepository(BaseRepository[MedicalVisit]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MedicalVisit)

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[MedicalVisit]:
        result = await self.session.execute(
            select(MedicalVisit)
            .where(MedicalVisit.user_id == user_id)
            .options(
                selectinload(MedicalVisit.medications),
                selectinload(MedicalVisit.lab_results),
                selectinload(MedicalVisit.clinical_notes),
            )
            .order_by(MedicalVisit.visit_date.asc().nullslast(), MedicalVisit.created_at.asc())
        )
        return result.scalars().all()
