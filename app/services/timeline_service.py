import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.timeline.service import TimelineService as AITimelineService
from app.models.patient_timeline import PatientTimeline
from app.repositories.timeline_repository import TimelineRepository
from app.repositories.visit_repository import VisitRepository


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.visit_repo = VisitRepository(session)
        self.timeline_repo = TimelineRepository(session)
        self.ai_timeline = AITimelineService()

    async def build_for_user(self, user_id: uuid.UUID) -> list[dict]:
        visits = list(await self.visit_repo.list_by_user(user_id))
        timeline = self.ai_timeline.build(visits)

        record = PatientTimeline(user_id=user_id, timeline_payload=timeline)
        await self.timeline_repo.create(record)
        await self.session.commit()
        return timeline

    async def get_latest(self, user_id: uuid.UUID) -> list[dict]:
        latest = await self.timeline_repo.get_latest_by_user(user_id)
        return latest.timeline_payload if latest else []
