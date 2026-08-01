import uuid
from collections.abc import Sequence

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_document import MedicalDocument
from app.models.enums import ProcessingStatus
from app.repositories.document_repository import DocumentRepository
from app.services.storage_service import LocalStorageService


class DocumentService:
    ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}

    def __init__(self, session: AsyncSession, storage: LocalStorageService) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.storage = storage

    async def upload_documents(self, user_id: uuid.UUID, files: Sequence[UploadFile]) -> list[MedicalDocument]:
        docs: list[MedicalDocument] = []
        for file in files:
            if file.content_type not in self.ALLOWED_MIME_TYPES:
                continue

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            saved_path = await self.storage.save_upload(str(user_id), file)
            doc = MedicalDocument(
                user_id=user_id,
                file_name=file.filename or saved_path.name,
                file_path=str(saved_path),
                mime_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                processing_status=ProcessingStatus.UPLOADED,
            )
            await self.repo.create(doc)
            docs.append(doc)

        await self.session.commit()
        for doc in docs:
            await self.session.refresh(doc)
        return docs

    async def list_documents(self, user_id: uuid.UUID) -> list[MedicalDocument]:
        return list(await self.repo.list_by_user(user_id))

    async def get_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> MedicalDocument | None:
        return await self.repo.get_by_user_and_id(user_id, document_id)
