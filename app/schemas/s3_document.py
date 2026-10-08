import uuid
from typing import Annotated

from pydantic import AfterValidator, Field

from app.core.config import settings
from app.models.enums import DocumentType, ProcessingStatus
from app.schemas.base import ORMBaseSchema

ALLOWED_UPLOAD_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


def max_upload_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


def _validate_mime_type(value: str) -> str:
    if value not in ALLOWED_UPLOAD_MIME_TYPES:
        raise ValueError("Only PDF, PNG and JPEG files are supported")
    return value


def _validate_file_size(value: int) -> int:
    if value > max_upload_bytes():
        raise ValueError(f"File is larger than the {settings.max_upload_size_mb} MB limit")
    return value


UploadMimeType = Annotated[str, AfterValidator(_validate_mime_type)]
UploadFileSize = Annotated[int, Field(gt=0), AfterValidator(_validate_file_size)]


class PresignedUploadRequest(ORMBaseSchema):
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: UploadMimeType
    file_size: UploadFileSize


class PresignedUploadResponse(ORMBaseSchema):
    document_id: str
    upload_url: str
    key: str
    expires_in: int


class PresignedEditRequest(ORMBaseSchema):
    mime_type: UploadMimeType
    file_size: UploadFileSize


class PresignedUrlResponse(ORMBaseSchema):
    url: str
    expires_in: int


class ConfirmUploadRequest(ORMBaseSchema):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class ConfirmUploadResponse(ORMBaseSchema):
    document_id: str
    processing_status: ProcessingStatus
    file_size: int


class ConfirmUploadBatchResponse(ORMBaseSchema):
    documents: list[ConfirmUploadResponse]
    failed: list[str]
