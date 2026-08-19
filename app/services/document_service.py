import logging
import uuid
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.emdeddings_formater.service import EmbeddingsFormatterService
from app.ai.extraction.ocr_service import get_ocr_service
from app.ai.extraction.service import ExtractionService
from app.core.exceptions import NotFoundException, ValidationException
from app.models.enums import ProcessingStatus
from app.models.medical_document import MedicalDocument
from app.models.patient_timeline import PatientTimeline
from app.models.record_type import RecordType
from app.repositories.document_repository import DocumentRepository
from app.repositories.timeline_repository import TimelineRepository
from app.schemas.document import DocumentResponse
from app.schemas.extraction import ExtractedLabResult, ExtractedMedicalVisit, ExtractedMedication
from app.services.analysis_service import AnalysisService
from app.services.medical_record_service import MedicalRecordService
from app.services.s3_service import S3Service
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)


class DocumentService:
    ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
    NOT_YET_EXTRACTED_STATUSES = (
        ProcessingStatus.UPLOADED,
        ProcessingStatus.OCR_COMPLETED,
        ProcessingStatus.FAILED,
    )

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

            document_id = uuid.uuid4()
            saved_path: Path = await self.storage.save_upload(str(user_id), str(document_id), file)

            doc = MedicalDocument(
                id=document_id,
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

    async def confirm_s3_uploads(
        self, user_id: uuid.UUID, document_ids: Sequence[uuid.UUID], s3: S3Service
    ) -> tuple[list[MedicalDocument], list[str]]:
        docs: list[MedicalDocument] = []
        failed: list[str] = []

        for document_id in document_ids:
            doc = await self.repo.get_by_user_and_id(user_id, document_id)
            if not doc:
                failed.append(str(document_id))
                continue

            head = await s3.head_object(doc.file_path)
            if head is None:
                failed.append(str(document_id))
                continue

            doc.file_size = head.get("ContentLength", doc.file_size)
            doc.processing_status = ProcessingStatus.UPLOADED

            docs.append(doc)

        await self.session.commit()
        for doc in docs:
            await self.session.refresh(doc)

        return docs, failed

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

        if not doc.ocr_text:
            doc.processing_status = ProcessingStatus.FAILED
            return

        await self._run_extraction_pipeline(doc, user_id, embedding_formatter_service)

    async def _run_extraction_pipeline(
        self,
        doc: MedicalDocument,
        user_id: uuid.UUID,
        embedding_formatter_service: EmbeddingsFormatterService | None = None,
    ) -> None:
        embedding_formatter_service = embedding_formatter_service or EmbeddingsFormatterService()
        extraction_service = ExtractionService()

        doc.embedding_text = await embedding_formatter_service.format_text_for_embedding(doc.ocr_text)
        doc.extraction_result = await extraction_service.extract_to_schema_free(doc.ocr_text)
        doc.processing_status = ProcessingStatus.OCR_COMPLETED

        structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedMedicalVisit)
        validated_data = ExtractedMedicalVisit(**structured_data)
        timeline_entry = PatientTimeline(
                **validated_data.model_dump(exclude_none=True),
                user_id=user_id,
                document_id=doc.id
            )
        await self.timeline_repo.create(timeline_entry)

        await self._create_records_from_extraction(
            doc=doc,
            user_id=user_id,
            extraction_service=extraction_service,
            default_recorded_at=timeline_entry.visit_date,
        )

        doc.processing_status = ProcessingStatus.EXTRACTED

    async def extract_from_existing_ocr(self, document_id: uuid.UUID) -> MedicalDocument:
        doc = await self.repo.get(document_id)
        if doc is None:
            raise NotFoundException(f"Document {document_id} not found")

        if doc.processing_status in (
            ProcessingStatus.EXTRACTED,
            ProcessingStatus.ANALYZED,
            ProcessingStatus.USER_EDITED,
            ProcessingStatus.ACCEPTED,
        ):
            logger.info(
                "Document %s already extracted (status=%s); skipping", document_id, doc.processing_status
            )
            return doc

        if not doc.ocr_text:
            doc.processing_status = ProcessingStatus.FAILED
            await self.session.commit()
            raise ValidationException(f"Document {document_id} has no OCR text to extract from")

        await self._run_extraction_pipeline(doc, doc.user_id)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def _create_records_from_extraction(
        self,
        doc: MedicalDocument,
        user_id: uuid.UUID,
        extraction_service: ExtractionService,
        default_recorded_at: date | None,
    ) -> None:
        if not doc.extraction_result:
            return

        record_type_service = self.record_service.record_type_service
        known_record_types = await record_type_service.list_active()
        known_record_types_payload = [
            {
                "code": record_type.code,
                "name": record_type.name,
                "description": record_type.description,
                "identity_field": record_type.identity_field,
                "schema": record_type.json_schema,
            }
            for record_type in known_record_types
        ]

        classified_records = await extraction_service.classify_extraction_result(
            doc.extraction_result, known_record_types_payload
        )

        for entry in classified_records:
            code = str(entry.get("record_type_code") or "").strip().upper()
            data = entry.get("data")
            if not code or not isinstance(data, dict) or not data:
                continue

            if entry.get("is_new_type"):
                record_type = await record_type_service.get_or_create(
                    code=code,
                    name=entry.get("name") or code.replace("_", " ").title(),
                    description=entry.get("description"),
                    json_schema=entry.get("json_schema")
                    or {"type": "object", "properties": {}, "additionalProperties": True},
                    identity_field=entry.get("identity_field"),
                )
            else:
                record_type = await record_type_service.get_by_code_any_status(code)
                if record_type is None:
                    logger.warning("Extraction referenced unknown record type code '%s', skipping", code)
                    continue

            filtered_data = self._filter_data_to_schema(record_type, data)
            if not filtered_data:
                continue

            try:
                record_type_service.validate_data(record_type, filtered_data)
            except ValidationException:
                logger.warning("Skipping '%s' record that failed schema validation", code)
                continue

            recorded_at = self._parse_date(entry.get("recorded_at")) or default_recorded_at

            await self.record_service.create_from_extraction(
                user_id=user_id,
                record_type_code=record_type.code,
                data=filtered_data,
                source_document_id=doc.id,
                recorded_at=recorded_at,
            )

    @staticmethod
    def _filter_data_to_schema(record_type: RecordType, data: dict) -> dict:
        schema = record_type.json_schema or {}
        if schema.get("additionalProperties") is False:
            allowed_fields = set(schema.get("properties", {}))
            return {key: value for key, value in data.items() if key in allowed_fields}
        return data

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

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
            # medications=medications,
            # lab_results=lab_results,
            # diagnosis_text=timeline_entry.diagnosis_text if timeline_entry else None,
            extraction_result=document.extraction_result,
        )

    async def update_extraction_result(
        self, user_id: uuid.UUID, document_id: uuid.UUID, extraction_result: dict
    ) -> DocumentResponse:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            raise NotFoundException(f"Document {document_id} not found")
        if doc.processing_status in self.NOT_YET_EXTRACTED_STATUSES:
            raise ValidationException("Document has not been extracted yet")

        doc.extraction_result = extraction_result
        doc.processing_status = ProcessingStatus.USER_EDITED
        await self.session.commit()

        response = await self.get_document(user_id, document_id)
        if response is None:
            raise NotFoundException(f"Document {document_id} not found")
        return response

    async def accept_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> DocumentResponse:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            raise NotFoundException(f"Document {document_id} not found")
        if doc.processing_status in self.NOT_YET_EXTRACTED_STATUSES:
            raise ValidationException("Document has not been extracted yet")

        doc.processing_status = ProcessingStatus.ACCEPTED
        await self.session.commit()

        response = await self.get_document(user_id, document_id)
        if response is None:
            raise NotFoundException(f"Document {document_id} not found")
        return response
