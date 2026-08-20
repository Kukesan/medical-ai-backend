import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RecordStatus
from app.models.record_type import RecordType
from app.repositories.timeline_repository import TimelineRepository
from app.schemas.timeline import TimelineListResponse
from app.services.document_record_service import DocumentRecordService
from app.services.medical_record_service import MedicalRecordService
from app.services.record_type_service import RecordTypeService


def _as_datetime(value: date | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def _record_label(data: dict, record_type: RecordType | None) -> str | None:
    if record_type and record_type.identity_field and data.get(record_type.identity_field):
        return str(data[record_type.identity_field])
    return record_type.name if record_type else None


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.timeline_repo = TimelineRepository(session)
        self.record_service = MedicalRecordService(session)
        self.document_record_service = DocumentRecordService(session)
        self.record_type_service = RecordTypeService(session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[TimelineListResponse]:
        entries = list(await self.timeline_repo.list_by_user(user_id))

        timeline_entries = [
            TimelineListResponse(
                name=entry.doctor_name,
                date=_as_datetime(entry.visit_date),
                category="Medical Visit",
            )
            for entry in entries
        ]

        # Every other record type (manually entered via intake, or read off a
        # document's classified extraction) carries its own recorded_at instead of
        # living in patient_timeline, so pull those in generically by date rather
        # than hardcoding a per-type field name here.
        record_type_cache: dict[uuid.UUID, RecordType | None] = {}

        records = await self.record_service.list_records(user_id, limit=10_000)
        for record in records:
            if record.status == RecordStatus.REJECTED or record.recorded_at is None:
                continue
            if record.record_type_id not in record_type_cache:
                record_type_cache[record.record_type_id] = await self.record_type_service.get_by_id(
                    record.record_type_id
                )
            record_type = record_type_cache[record.record_type_id]
            timeline_entries.append(
                TimelineListResponse(
                    name=_record_label(record.data, record_type),
                    date=_as_datetime(record.recorded_at),
                    category=record_type.name if record_type else "Medical Record",
                )
            )

        record_type_by_code = {rt.code: rt for rt in record_type_cache.values() if rt}
        document_records = await self.document_record_service.list_records(user_id)
        for doc_record in document_records:
            if doc_record.recorded_at is None:
                continue
            if doc_record.record_type_code not in record_type_by_code:
                record_type_by_code[doc_record.record_type_code] = await self.record_type_service.get_by_code_any_status(
                    doc_record.record_type_code
                )
            record_type = record_type_by_code[doc_record.record_type_code]
            timeline_entries.append(
                TimelineListResponse(
                    name=_record_label(doc_record.data, record_type),
                    date=_as_datetime(doc_record.recorded_at),
                    category=record_type.name if record_type else doc_record.record_type_code.replace("_", " ").title(),
                )
            )

        timeline_entries.sort(key=lambda x: x.date or datetime.min, reverse=True)

        return timeline_entries
