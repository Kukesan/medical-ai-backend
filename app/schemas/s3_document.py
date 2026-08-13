from app.models.enums import DocumentType, ProcessingStatus
from app.schemas.base import ORMBaseSchema


class PresignedUploadRequest(ORMBaseSchema):
    file_name: str
    mime_type: str
    file_size: int


class PresignedUploadResponse(ORMBaseSchema):
    document_id: str
    upload_url: str
    key: str
    expires_in: int


class PresignedEditRequest(ORMBaseSchema):
    mime_type: str
    file_size: int


class PresignedUrlResponse(ORMBaseSchema):
    url: str
    expires_in: int


class ConfirmUploadResponse(ORMBaseSchema):
    document_id: str
    processing_status: ProcessingStatus
    ocr_text: str
    file_size: int
