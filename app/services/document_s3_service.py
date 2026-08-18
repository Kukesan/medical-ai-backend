import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProcessingStatus
from app.models.medical_document import MedicalDocument
from app.repositories.document_repository import DocumentRepository
from app.schemas.s3_document import PresignedEditRequest, PresignedUploadRequest
from app.services.s3_service import S3Service


class DocumentS3Service:
    def __init__(self, session: AsyncSession, s3: S3Service) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.s3 = s3

    async def create_upload_url(
        self, user_id: uuid.UUID, data: PresignedUploadRequest
    ) -> tuple[MedicalDocument, str]:
        document_id = uuid.uuid4()
        key = self.s3.build_key(str(user_id), str(document_id), data.file_name)
        doc = MedicalDocument(
            id=document_id,
            user_id=user_id,
            file_name=data.file_name,
            file_path=key,
            mime_type=data.mime_type,
            file_size=data.file_size,
            processing_status=ProcessingStatus.UPLOADED,
        )
        await self.repo.create(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        upload_url = self.s3.generate_upload_url(key, data.mime_type)
        return doc, upload_url

    async def create_view_url(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[MedicalDocument, str] | None:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            return None

        return doc, self.s3.generate_view_url(doc.file_path)

    async def create_edit_url(
        self, user_id: uuid.UUID, document_id: uuid.UUID, data: PresignedEditRequest
    ) -> tuple[MedicalDocument, str] | None:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            return None

        doc.mime_type = data.mime_type
        doc.file_size = data.file_size
        doc.processing_status = ProcessingStatus.UPLOADED
        await self.session.commit()
        await self.session.refresh(doc)

        upload_url = self.s3.generate_upload_url(doc.file_path, data.mime_type)
        return doc, upload_url

    async def delete_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> bool:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            return False

        await self.s3.delete_object(doc.file_path)
        await self.repo.delete(doc)
        await self.session.commit()
        return True
