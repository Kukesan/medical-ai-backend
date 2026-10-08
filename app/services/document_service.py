import logging
import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.emdeddings_formater.service import EmbeddingsFormatterService
from app.ai.extraction.service import ExtractionService
from app.core.exceptions import NotFoundException, ValidationException
from app.models.enums import ProcessingStatus
from app.models.medical_document import MedicalDocument
from app.models.patient_timeline import PatientTimeline
from app.models.record_type import RecordType
from app.repositories.document_repository import DocumentRepository
from app.repositories.timeline_repository import TimelineRepository
from app.schemas.document import DocumentResponse
from app.schemas.extraction import ExtractedMedicalVisit
from app.schemas.s3_document import ALLOWED_UPLOAD_MIME_TYPES, max_upload_bytes
from app.services.embedding_service import EmbeddingService
from app.services.record_type_service import RecordTypeService
from app.services.s3_service import S3Service
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)


class DocumentService:
    NOT_YET_EXTRACTED_STATUSES = (
        ProcessingStatus.UPLOADED,
        ProcessingStatus.OCR_COMPLETED,
        ProcessingStatus.FAILED,
    )

    def __init__(self, session: AsyncSession, storage: LocalStorageService) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.timeline_repo = TimelineRepository(session)
        self.record_type_service = RecordTypeService(session)
        self.embedding_service = EmbeddingService(session)
        self.storage = storage

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

            # The presigned PUT cannot cap the size and the client could ignore the declared type,
            # so check what actually landed in the bucket and discard anything out of bounds.
            actual_size = head.get("ContentLength", 0)
            actual_type = head.get("ContentType", "")
            if actual_size > max_upload_bytes() or actual_type not in ALLOWED_UPLOAD_MIME_TYPES:
                logger.warning(
                    "Rejecting S3 upload for document %s (size=%s, type=%s)", document_id, actual_size, actual_type
                )
                await s3.delete_object(doc.file_path)
                await self.repo.delete(doc)
                failed.append(str(document_id))
                continue

            doc.file_size = actual_size
            doc.processing_status = ProcessingStatus.UPLOADED

            docs.append(doc)

        await self.session.commit()
        for doc in docs:
            await self.session.refresh(doc)

        return docs, failed

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

        known_record_types = await self.record_type_service.list_active()
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

        classified: list[dict] = []
        for entry in classified_records:
            code = str(entry.get("record_type_code") or "").strip().upper()
            data = entry.get("data")
            if not code or not isinstance(data, dict) or not data:
                continue

            if entry.get("is_new_type"):
                record_type = await self.record_type_service.get_or_create(
                    code=code,
                    name=entry.get("name") or code.replace("_", " ").title(),
                    description=entry.get("description"),
                    json_schema=entry.get("json_schema")
                    or {"type": "object", "properties": {}, "additionalProperties": True},
                    identity_field=entry.get("identity_field"),
                )
            else:
                record_type = await self.record_type_service.get_by_code_any_status(code)
                if record_type is None:
                    logger.warning("Extraction referenced unknown record type code '%s', skipping", code)
                    continue

            filtered_data = self._filter_data_to_schema(record_type, data)
            if not filtered_data:
                continue

            try:
                self.record_type_service.validate_data(record_type, filtered_data)
            except ValidationException:
                logger.warning("Skipping '%s' record that failed schema validation", code)
                continue

            recorded_at = self._parse_date(entry.get("recorded_at")) or default_recorded_at

            classified.append(
                {
                    "record_type_code": record_type.code,
                    "data": filtered_data,
                    "recorded_at": recorded_at.isoformat() if recorded_at else None,
                }
            )

        doc.classified_records = classified

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

        try:
            await self.embedding_service.embed_document(user_id, doc)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Embedding failed for document %s", document_id)

        response = await self.get_document(user_id, document_id)
        if response is None:
            raise NotFoundException(f"Document {document_id} not found")
        return response

    async def delete_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        doc = await self.repo.get_by_user_and_id(user_id, document_id)
        if not doc:
            raise NotFoundException(f"Document {document_id} not found")

        file_path = doc.file_path
        # Remove the stored file first: if that fails the row survives and the delete can be retried,
        # instead of leaving an orphaned file holding patient data.
        if S3Service.is_s3_key(file_path):
            await S3Service().delete_object(file_path)
        else:
            self.storage.delete(file_path)

        await self.repo.delete(doc)
        await self.session.commit()
