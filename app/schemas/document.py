from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.models.enums import DocumentType, ProcessingStatus
from app.schemas.base import ORMBaseSchema
from app.schemas.extraction import ExtractedLabResult, ExtractedMedication


class DocumentOut(ORMBaseSchema):
    id: str
    file_name: str
    mime_type: str
    file_size: int
    document_type: DocumentType
    processing_status: ProcessingStatus
    created_at: datetime


class DocumentUploadItem(ORMBaseSchema):
    file_name: str
    document_id: str
    status: ProcessingStatus


class DocumentUploadResponse(ORMBaseSchema):
    uploaded: list[DocumentUploadItem]
    failed: list[str] = Field(default_factory=list)

class DocumentExtractResponse(ORMBaseSchema):
    status: str
    message: str


class DocumentExtractionUpdateRequest(ORMBaseSchema):
    extraction_result: dict[str, Any]


class DocumentResponse(ORMBaseSchema):
    id: str
    file_name: str
    mime_type: str
    file_size: int
    document_type: DocumentType
    processing_status: ProcessingStatus
    created_at: datetime
    visit_date: date | None = None
    doctor_name: str | None = None
    hospital_name: str | None = None
    # medications: list[ExtractedMedication]
    # lab_results: list[ExtractedLabResult]
    # diagnosis_text: str | None = None
    extraction_result: dict | None = None