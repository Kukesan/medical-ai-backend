import uuid
from collections.abc import Sequence
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.extraction.ocr_service import OCRService
from app.ai.extraction.service import ExtractionService
from app.models.allergy import Allergy
from app.models.medication import Medication
from app.models.lab_result import LabResult
from app.models.clinical_note import ClinicalNote
from app.repositories.clinic_note_repository import ClinicalNoteRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.lab_result_repository import LabResultRepository
from app.repositories.allergy_repository import AllergyRepository
from app.schemas.extraction import ExtractedAllergy, ExtractedClinicalNote, ExtractedLabResult, ExtractedMedicalVisit, ExtractedMedication
from app.models.medical_document import MedicalDocument
from app.models.enums import ProcessingStatus
from app.models.medical_visit import MedicalVisit
from app.repositories.document_repository import DocumentRepository
from app.repositories.visit_repository import VisitRepository
from app.services.storage_service import LocalStorageService
from app.services.structured_mapper import StructuredDataMapper


class DocumentService:
    ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}

    def __init__(self, session: AsyncSession, storage: LocalStorageService) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.visit_repo = VisitRepository(session) 
        self.medication_repo = MedicationRepository(session)
        self.lab_result_repo = LabResultRepository(session)
        self.clinical_note_repo = ClinicalNoteRepository(session)
        self.allergy_repo = AllergyRepository(session)
        self.storage = storage

    async def upload_documents(
        self,
        user_id: uuid.UUID,
        files: Sequence[UploadFile],
    ) -> tuple[list[MedicalDocument], list[str]]:
        docs: list[MedicalDocument] = []
        failed: list[str] = []

        ocr_service = OCRService();  # Assuming you have an OCR service for processing documents

        for file in files:
            if file.content_type not in self.ALLOWED_MIME_TYPES:
                failed.append(file.filename or "unknown")
                continue

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            saved_path: Path = await self.storage.save_upload(str(user_id), file)
            ocr_result: dict = await ocr_service.extract_text(saved_path)

            doc = MedicalDocument(
                user_id=user_id,
                file_name=file.filename or saved_path.name,
                file_path=str(saved_path),
                mime_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                ocr_text=ocr_result.get("text", ""),
                ocr_metadata=ocr_result.get("metadata", {}),
                processing_status=ProcessingStatus.OCR_COMPLETED if ocr_result.get("text", "") else ProcessingStatus.FAILED,
            )

            await self.repo.create(doc)
            await self.session.flush()

            extraction_service = ExtractionService();
            if doc.ocr_text:
                structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedMedicalVisit)
                validated_data = ExtractedMedicalVisit(**structured_data)
                visit = MedicalVisit(
                        **validated_data.model_dump(exclude_none=True),
                        user_id=user_id,
                        document_id=doc.id
                    )
                await self.visit_repo.create(visit)

                structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedAllergy)
                validated_data = ExtractedAllergy(**structured_data)
                if validated_data.substance:
                    allergy = Allergy(
                            **validated_data.model_dump(exclude_none=True),
                            user_id=user_id,
                        )
                    await self.allergy_repo.create(allergy)

                structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedClinicalNote)
                validated_data = ExtractedClinicalNote(**structured_data)
                if validated_data.note_text:
                    clinical_note = ClinicalNote(
                            **validated_data.model_dump(exclude_none=True),
                            visit_id=visit.id,
                        )
                    await self.clinical_note_repo.create(clinical_note)

                structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedLabResult)
                validated_data = ExtractedLabResult(**structured_data)
                if validated_data.test_name:
                    lab_result = LabResult(
                            **validated_data.model_dump(exclude_none=True),
                            visit_id=visit.id,
                        )
                    await self.lab_result_repo.create(lab_result)

                structured_data = await extraction_service.extract_to_schema(doc.ocr_text, ExtractedMedication)
                validated_data = ExtractedMedication(**structured_data)
                if validated_data.name:
                    medication = Medication(
                            **validated_data.model_dump(exclude_none=True),
                            visit_id=visit.id,
                        )
                    await self.medication_repo.create(medication)

                doc.processing_status = ProcessingStatus.EXTRACTED
            else:
                doc.processing_status = ProcessingStatus.FAILED

            docs.append(doc)

        await self.session.commit()
        for doc in docs:
            await self.session.refresh(doc)
        return docs, failed

    async def list_documents(self, user_id: uuid.UUID) -> list[MedicalDocument]:
        return list(await self.repo.list_by_user(user_id))

    async def get_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> MedicalDocument | None:
        return await self.repo.get_by_user_and_id(user_id, document_id)
