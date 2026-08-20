import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RecordStatus
from app.models.medical_record import MedicalRecord
from app.repositories.base import BaseRepository


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MedicalRecord)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: RecordStatus | None = None,
        record_type_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[MedicalRecord]:
        stmt = select(MedicalRecord).where(MedicalRecord.user_id == user_id)
        if status is not None:
            stmt = stmt.where(MedicalRecord.status == status)
        if record_type_id is not None:
            stmt = stmt.where(MedicalRecord.record_type_id == record_type_id)
        if document_id is not None:
            stmt = stmt.where(MedicalRecord.source_document_id == document_id)
        stmt = stmt.order_by(MedicalRecord.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_sole_verified(self, user_id: uuid.UUID, record_type_id: uuid.UUID) -> MedicalRecord | None:
        result = await self.session.execute(
            select(MedicalRecord).where(
                MedicalRecord.user_id == user_id,
                MedicalRecord.record_type_id == record_type_id,
                MedicalRecord.status == RecordStatus.VERIFIED,
            )
        )
        matches = result.scalars().all()
        if len(matches) != 1:
            return None
        return matches[0]

    async def detach_source_document(self, document_id: uuid.UUID) -> None:
        await self.session.execute(
            update(MedicalRecord)
            .where(MedicalRecord.source_document_id == document_id)
            .values(source_document_id=None)
        )
        await self.session.flush()
