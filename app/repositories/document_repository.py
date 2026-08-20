import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProcessingStatus
from app.models.medical_document import MedicalDocument
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[MedicalDocument]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MedicalDocument)

    async def list_by_status(self, status: ProcessingStatus) -> Sequence[MedicalDocument]:
        result = await self.session.execute(
            select(MedicalDocument)
            .where(MedicalDocument.processing_status == status)
            .order_by(MedicalDocument.created_at.asc())
        )
        return result.scalars().all()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[MedicalDocument]:
        result = await self.session.execute(
            select(MedicalDocument)
            .where(MedicalDocument.user_id == user_id)
            .order_by(MedicalDocument.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_user_and_id(self, user_id: uuid.UUID, document_id: uuid.UUID) -> MedicalDocument | None:
        result = await self.session.execute(
            select(MedicalDocument).where(
                MedicalDocument.user_id == user_id,
                MedicalDocument.id == document_id,
            )
        )
        return result.scalar_one_or_none()
