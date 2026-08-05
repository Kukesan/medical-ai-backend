from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_timeline import PatientTimeline
from app.repositories.surgery_repository import SurgeryRepository
from app.repositories.visit_repository import VisitRepository
from app.repositories.vaccination_repository import VaccinationRepository
from app.schemas.timeline import TimelineListResponse


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.visit_repo = VisitRepository(session)
        self.vaccine_repo = VaccinationRepository(session)
        self.surgery_repo = SurgeryRepository(session)

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

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[TimelineListResponse]:
        visits = list(await self.visit_repo.list_by_user(user_id))
        vaccines = list(await self.vaccine_repo.list_by_user(user_id))
        surgeries = list(await self.surgery_repo.list_by_user(user_id))

        timeline_entries = []
        for visit in visits:
            timeline_entries.append(
                TimelineListResponse(
                    name=visit.doctor_name,
                    date=visit.visit_date,
                    category="Medical Visit"
                )
            )

        for vaccine in vaccines:
            timeline_entries.append(
                TimelineListResponse(
                    name=vaccine.name,
                    date=vaccine.date_administered,
                    category="Vaccination"
                )
            )

        for surgery in surgeries:
            timeline_entries.append(
                TimelineListResponse(
                    name=surgery.name,
                    date=surgery.date,
                    category="Surgery"
                )
            )

        timeline_entries.sort(key=lambda x: x.date or datetime.min, reverse=True)

        return timeline_entries