import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_timeline import PatientTimeline
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[PatientTimeline]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatientTimeline)

    async def get_latest_by_user(self, user_id: uuid.UUID) -> PatientTimeline | None:
        result = await self.session.execute(
            select(PatientTimeline)
            .where(PatientTimeline.user_id == user_id)
            .order_by(PatientTimeline.generated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
