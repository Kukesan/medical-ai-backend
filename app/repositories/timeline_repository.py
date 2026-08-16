import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_timeline import PatientTimeline
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[PatientTimeline]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatientTimeline)

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[PatientTimeline]:
        result = await self.session.execute(
            select(PatientTimeline)
            .where(PatientTimeline.user_id == user_id)
            .order_by(PatientTimeline.visit_date.asc().nullslast(), PatientTimeline.generated_at.asc())
        )
        return result.scalars().all()

    async def get_by_document_id(self, document_id: uuid.UUID) -> PatientTimeline | None:
        result = await self.session.execute(
            select(PatientTimeline).where(PatientTimeline.document_id == document_id)
        )
        return result.scalars().first()
