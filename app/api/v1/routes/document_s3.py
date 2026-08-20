import uuid
from http import HTTPStatus

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_session
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.s3_document import (
    ConfirmUploadBatchResponse,
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    PresignedEditRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
    PresignedUrlResponse,
)
from app.services.document_s3_service import DocumentS3Service
from app.services.document_service import DocumentService
from app.services.s3_service import S3Service
from app.services.storage_service import LocalStorageService

router = APIRouter(prefix="/documents/s3")


@router.post("/upload-url", response_model=PresignedUploadResponse)
async def create_upload_url(
    data: PresignedUploadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresignedUploadResponse:
    service = DocumentS3Service(session, S3Service())
    doc, upload_url = await service.create_upload_url(user.id, data)

    return PresignedUploadResponse(
        document_id=str(doc.id),
        upload_url=upload_url,
        key=doc.file_path,
        expires_in=settings.presigned_url_expire_seconds,
    )


@router.post("/confirm-upload", response_model=ConfirmUploadBatchResponse)
async def confirm_upload(
    data: ConfirmUploadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConfirmUploadBatchResponse:
    service = DocumentService(session, LocalStorageService())
    docs, failed = await service.confirm_s3_uploads(user.id, data.document_ids, S3Service())
    if not docs and not failed:
        raise NotFoundException("Document not found")

    return ConfirmUploadBatchResponse(
        documents=[
            ConfirmUploadResponse(
                document_id=str(doc.id),
                processing_status=doc.processing_status,
                file_size=doc.file_size,
            )
            for doc in docs
        ],
        failed=failed,
    )


@router.get("/{document_id}/view-url", response_model=PresignedUrlResponse)
async def create_view_url(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresignedUrlResponse:
    service = DocumentS3Service(session, S3Service())
    result = await service.create_view_url(user.id, document_id)
    if not result:
        raise NotFoundException("Document not found")

    _, url = result
    return PresignedUrlResponse(url=url, expires_in=settings.presigned_url_expire_seconds)


@router.put("/{document_id}/edit-url", response_model=PresignedUrlResponse)
async def create_edit_url(
    document_id: uuid.UUID,
    data: PresignedEditRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresignedUrlResponse:
    service = DocumentS3Service(session, S3Service())
    result = await service.create_edit_url(user.id, document_id, data)
    if not result:
        raise NotFoundException("Document not found")

    _, url = result
    return PresignedUrlResponse(url=url, expires_in=settings.presigned_url_expire_seconds)


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = DocumentS3Service(session, S3Service())
    deleted = await service.delete_document(user.id, document_id)
    if not deleted:
        raise NotFoundException("Document not found")

    return Response(status_code=HTTPStatus.NO_CONTENT)
