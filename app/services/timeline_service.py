import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.timeline_repository import TimelineRepository
from app.schemas.timeline import TimelineListResponse
from app.services.document_record_service import DocumentRecordService
from app.services.medical_record_service import MedicalRecordService


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.timeline_repo = TimelineRepository(session)
        self.record_service = MedicalRecordService(session)
        self.document_record_service = DocumentRecordService(session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[TimelineListResponse]:
        entries = list(await self.timeline_repo.list_by_user(user_id))
        vaccinations = [
            *await self.record_service.list_data_by_type(user_id, "VACCINATION"),
            *await self.document_record_service.list_records(user_id, record_type_code="VACCINATION"),
        ]
        surgeries = [
            *await self.record_service.list_data_by_type(user_id, "SURGERY"),
            *await self.document_record_service.list_records(user_id, record_type_code="SURGERY"),
        ]

        timeline_entries = []
        for entry in entries:
            timeline_entries.append(
                TimelineListResponse(
                    name=entry.doctor_name,
                    date=entry.visit_date,
                    category="Medical Visit"
                )
            )

        for vaccination in vaccinations:
            timeline_entries.append(
                TimelineListResponse(
                    name=vaccination.data.get("name"),
                    date=_parse_datetime(vaccination.data.get("date_administered")),
                    category="Vaccination"
                )
            )

        for surgery in surgeries:
            timeline_entries.append(
                TimelineListResponse(
                    name=surgery.data.get("name"),
                    date=_parse_date(surgery.data.get("date")),
                    category="Surgery"
                )
            )

        timeline_entries.sort(key=lambda x: x.date or datetime.min, reverse=True)

        return timeline_entries
