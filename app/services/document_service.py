import logging
import tempfile
import uuid
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.emdeddings_formater.service import EmbeddingsFormatterService
from app.ai.extraction.ocr_service import get_ocr_service
from app.ai.extraction.service import ExtractionService
from app.models.enums import ProcessingStatus
from app.models.medical_document import MedicalDocument
from app.models.patient_timeline import PatientTimeline
from app.repositories.document_repository import DocumentRepository
from app.repositories.timeline_repository import TimelineRepository
from app.schemas.document import DocumentResponse
from app.schemas.extraction import ExtractedAllergy, ExtractedLabResult, ExtractedMedicalVisit, ExtractedMedication
from app.services.analysis_service import AnalysisService
from app.services.medical_record_service import MedicalRecordService
from app.services.s3_service import S3Service
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)


class DocumentService:
    ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}

    def __init__(self, session: AsyncSession, storage: LocalStorageService) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.timeline_repo = TimelineRepository(session)
        self.record_service = MedicalRecordService(session)
        self.storage = storage

    async def upload_documents(
        self,
        user_id: uuid.UUID,
        files: Sequence[UploadFile],
    ) -> tuple[list[MedicalDocument], list[str]]:
        docs: list[MedicalDocument] = []
        failed: list[str] = []

        ocr_service = get_ocr_service()
        embedding_formatter_service = EmbeddingsFormatterService();
        analyze_service = AnalysisService(self.session);  # Assuming you have an analysis service for processing documents
        for file in files:
            if file.content_type not in self.ALLOWED_MIME_TYPES:
                failed.append(file.filename or "unknown")
                continue

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            saved_path: Path = await self.storage.save_upload(str(user_id), file)

            doc = MedicalDocument(
                user_id=user_id,
                file_name=file.filename or saved_path.name,
                file_path=str(saved_path),
                mime_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                processing_status=ProcessingStatus.UPLOADED,
            )

            await self.repo.create(doc)
            await self.session.flush()

            await self._extract_document(doc, saved_path, user_id, ocr_service, embedding_formatter_service)

            docs.append(doc)

        await self.session.commit()
        for doc in docs:
            await self.session.refresh(doc)

        # await analyze_service.analyze_medication_interactions(user_id)

        return docs, failed

    async def confirm_s3_upload(
        self, user_id: uuid.UUID, document_id: uuid.UUID, s3: S3Service
    ) -> MedicalDocument | None:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            return None

        file_bytes = await s3.download_object(doc.file_path)
        doc.file_size = len(file_bytes)

        suffix = Path(doc.file_name or "file").suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            ocr_service = get_ocr_service()
            embedding_formatter_service = EmbeddingsFormatterService()
            await self._extract_document(doc, tmp_path, user_id, ocr_service, embedding_formatter_service)
        finally:
            tmp_path.unlink(missing_ok=True)

        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def _extract_document(
        self,
        doc: MedicalDocument,
        file_path: Path,
        user_id: uuid.UUID,
        ocr_service,
        embedding_formatter_service: EmbeddingsFormatterService,
    ) -> None:
        ocr_result: dict = await ocr_service.extract_text(file_path)
        doc.ocr_text = ocr_result.get("text", "")
        doc.ocr_metadata = ocr_result.get("metadata", {})
        doc.embedding_text = await embedding_formatter_service.format_text_for_embedding(doc.ocr_text)

        if not doc.ocr_text:
            doc.processing_status = ProcessingStatus.FAILED
            return

        doc.processing_status = ProcessingStatus.OCR_COMPLETED

        extraction_service = ExtractionService()

        structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedMedicalVisit)
        validated_data = ExtractedMedicalVisit(**structured_data)
        timeline_entry = PatientTimeline(
                **validated_data.model_dump(exclude_none=True),
                user_id=user_id,
                document_id=doc.id
            )
        await self.timeline_repo.create(timeline_entry)

        structured_data = await extraction_service.extract_to_schema_list(doc.ocr_text, ExtractedAllergy)
        for item in structured_data:
            if item.substance:
                await self.record_service.create_from_extraction(
                    user_id=user_id,
                    record_type_code="ALLERGY",
                    data=item.model_dump(mode="json", exclude={"confidence"}, exclude_none=True),
                    source_document_id=doc.id,
                    recorded_at=timeline_entry.visit_date,
                )

        structured_data = await extraction_service.extract_to_schema_list(doc.ocr_text, ExtractedLabResult)
        for item in structured_data:
            if item.test_name:
                await self.record_service.create_from_extraction(
                    user_id=user_id,
                    record_type_code="LAB_RESULT",
                    data=item.model_dump(mode="json", exclude={"confidence"}, exclude_none=True),
                    source_document_id=doc.id,
                    recorded_at=item.observed_date or timeline_entry.visit_date,
                )

        structured_data = await extraction_service.extract_to_schema_list(doc.ocr_text, ExtractedMedication)
        for item in structured_data:
            if item.name:
                await self.record_service.create_from_extraction(
                    user_id=user_id,
                    record_type_code="MEDICATION",
                    data=item.model_dump(mode="json", exclude={"confidence"}, exclude_none=True),
                    source_document_id=doc.id,
                    recorded_at=item.start_date or timeline_entry.visit_date,
                )

        doc.processing_status = ProcessingStatus.EXTRACTED

    async def list_documents(self, user_id: uuid.UUID) -> list[MedicalDocument]:
        return list(await self.repo.list_by_user(user_id))

    async def get_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> DocumentResponse | None:
        document = await self.repo.get_by_user_and_id(user_id, document_id)
        if not document:
            return None

        timeline_entry = await self.timeline_repo.get_by_document_id(document.id)

        medication_records = await self.record_service.list_records(
            user_id, record_type_code="MEDICATION", document_id=document.id, limit=1000
        )
        lab_result_records = await self.record_service.list_records(
            user_id, record_type_code="LAB_RESULT", document_id=document.id, limit=1000
        )
        medications = [ExtractedMedication(**record.data) for record in medication_records]
        lab_results = [ExtractedLabResult(**record.data) for record in lab_result_records]

        return DocumentResponse(
            id=str(document.id),
            file_name=document.file_name,
            mime_type=document.mime_type,
            file_size=document.file_size,
            document_type=document.document_type,
            processing_status=document.processing_status,
            created_at=document.created_at,
            visit_date=timeline_entry.visit_date if timeline_entry else None,
            doctor_name=timeline_entry.doctor_name if timeline_entry else None,
            hospital_name=timeline_entry.hospital_name if timeline_entry else None,
            medications=medications,
            lab_results=lab_results,
            diagnosis_text=timeline_entry.diagnosis_text if timeline_entry else None,
        )
