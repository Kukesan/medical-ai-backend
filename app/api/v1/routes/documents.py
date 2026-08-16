import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.exceptions import NotFoundException
from app.core.templates import templates
from app.models.user import User
from app.schemas.document import DocumentOut, DocumentUploadItem, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.storage_service import LocalStorageService

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    service = DocumentService(session, LocalStorageService())
    docs, failed = await service.upload_documents(user.id, files)

    return DocumentUploadResponse(
        uploaded=[
            DocumentUploadItem(file_name=d.file_name, document_id=str(d.id), status=d.processing_status)
            for d in docs
        ],
        failed=failed,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentOut]:
    service = DocumentService(session, LocalStorageService())
    docs = await service.list_documents(user.id)
    return [DocumentOut.model_validate({
        "id": str(d.id),
        "file_name": d.file_name,
        "mime_type": d.mime_type,
        "file_size": d.file_size,
        "document_type": d.document_type,
        "processing_status": d.processing_status,
        "created_at": d.created_at,
    }) for d in docs]


@router.get("/{document_id}", response_class=HTMLResponse)
async def get_document(
    request: Request,
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    service = DocumentService(session, LocalStorageService())
    doc = await service.get_document(user.id, document_id)
    if not doc:
        raise NotFoundException("Document not found")

    return templates.TemplateResponse(
        request=request,
        name="document_detail.html",
        context={"document": doc},
    )
