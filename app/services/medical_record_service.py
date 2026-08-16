import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.enums import RecordStatus
from app.models.medical_record import MedicalRecord
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.services.record_type_service import RecordTypeService

VERIFIABLE_STATUSES = (RecordStatus.NEEDS_REVIEW, RecordStatus.USER_EDITED)
REJECTABLE_STATUSES = (RecordStatus.NEEDS_REVIEW, RecordStatus.USER_EDITED, RecordStatus.CONFLICT_REQUIRES_REVIEW)


class MedicalRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicalRecordRepository(session)
        self.record_type_service = RecordTypeService(session)

    async def create_from_extraction(
        self,
        user_id: uuid.UUID,
        record_type_code: str,
        data: dict[str, Any],
        source_document_id: uuid.UUID | None = None,
        recorded_at: date | None = None,
    ) -> MedicalRecord | None:
        try:
            record_type = await self.record_type_service.get_by_code(record_type_code)
        except NotFoundException:
            return None

        status = RecordStatus.NEEDS_REVIEW
        conflict_with_record_id = None

        if record_type.identity_field:
            incoming_value = data.get(record_type.identity_field)
            if incoming_value:
                existing = await self.repo.find_sole_verified(user_id, record_type.id)
                if existing is not None:
                    existing_value = existing.data.get(record_type.identity_field)
                    if existing_value and str(existing_value).strip().lower() != str(incoming_value).strip().lower():
                        status = RecordStatus.CONFLICT_REQUIRES_REVIEW
                        conflict_with_record_id = existing.id

        record = MedicalRecord(
            user_id=user_id,
            record_type_id=record_type.id,
            source_document_id=source_document_id,
            recorded_at=recorded_at,
            status=status,
            data=data,
            current_version=1,
            conflict_with_record_id=conflict_with_record_id,
        )
        await self.repo.create(record)

        return record

    async def get(self, user_id: uuid.UUID, record_id: uuid.UUID) -> MedicalRecord:
        record = await self.repo.get(record_id)
        if record is None:
            raise NotFoundException("Medical record not found")
        if record.user_id != user_id:
            raise ForbiddenException("You do not have access to this medical record")
        return record

    async def list_records(
        self,
        user_id: uuid.UUID,
        status: RecordStatus | None = None,
        record_type_code: str | None = None,
        document_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[MedicalRecord]:
        record_type_id = None
        if record_type_code is not None:
            record_type = await self.record_type_service.get_by_code(record_type_code)
            record_type_id = record_type.id
        return await self.repo.list_by_user(
            user_id,
            status=status,
            record_type_id=record_type_id,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )

    async def list_data_by_type(
        self,
        user_id: uuid.UUID,
        record_type_code: str,
        exclude_status: RecordStatus = RecordStatus.REJECTED,
    ) -> Sequence[MedicalRecord]:
        """All of a user's records of one type, excluding a status (rejected by default).

        Used by downstream consumers (drug interactions, consultant context, timeline,
        lab trends) that want every record a person hasn't explicitly discarded - matching
        the legacy tables' behavior of having no review concept and counting everything.
        """
        records = await self.list_records(user_id, record_type_code=record_type_code, limit=10_000)
        return [record for record in records if record.status != exclude_status]

    async def patch(self, user_id: uuid.UUID, record_id: uuid.UUID, data: dict[str, Any]) -> MedicalRecord:
        record = await self.get(user_id, record_id)
        if record.status == RecordStatus.REJECTED:
            raise ConflictException("Cannot edit a rejected record")

        record_type = await self.record_type_service.get_by_id(record.record_type_id)
        merged = {**record.data, **data}
        self.record_type_service.validate_data(record_type, merged)

        changed_fields = [key for key, value in data.items() if record.data.get(key) != value]
        if not changed_fields:
            return record

        record.data = merged
        record.current_version += 1
        record.status = RecordStatus.USER_EDITED

        await self.session.commit()
        return record

    async def verify(self, user_id: uuid.UUID, record_id: uuid.UUID) -> MedicalRecord:
        record = await self.get(user_id, record_id)
        if record.status not in VERIFIABLE_STATUSES:
            raise ConflictException(f"Cannot verify a record in status '{record.status.value}'")

        record.status = RecordStatus.VERIFIED
        record.current_version += 1

        await self.session.commit()
        return record

    async def reject(self, user_id: uuid.UUID, record_id: uuid.UUID) -> MedicalRecord:
        record = await self.get(user_id, record_id)
        if record.status not in REJECTABLE_STATUSES:
            raise ConflictException(f"Cannot reject a record in status '{record.status.value}'")

        record.status = RecordStatus.REJECTED
        record.current_version += 1

        await self.session.commit()
        return record

    async def resolve_conflict(
        self,
        user_id: uuid.UUID,
        record_id: uuid.UUID,
        resolution: Literal["keep_existing", "accept_incoming"],
    ) -> MedicalRecord:
        record = await self.get(user_id, record_id)
        if record.status != RecordStatus.CONFLICT_REQUIRES_REVIEW:
            raise ConflictException("Record is not in a conflict state")

        if resolution == "keep_existing":
            record.status = RecordStatus.REJECTED
            record.current_version += 1
        else:
            record.status = RecordStatus.VERIFIED
            record.current_version += 1

            if record.conflict_with_record_id is not None:
                superseded = await self.repo.get(record.conflict_with_record_id)
                if superseded is not None and superseded.status == RecordStatus.VERIFIED:
                    superseded.status = RecordStatus.REJECTED
                    superseded.current_version += 1

        await self.session.commit()
        return record
