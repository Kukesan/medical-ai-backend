from datetime import datetime

from pydantic import Field

from app.models.enums import DocumentType, ProcessingStatus
from app.schemas.base import ORMBaseSchema


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
