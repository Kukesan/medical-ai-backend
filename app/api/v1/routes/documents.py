import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session, verify_service_api_key
from app.core.exceptions import NotFoundException
from app.core.templates import templates
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.document import (
    DocumentExtractionUpdateRequest,
    DocumentExtractResponse,
    DocumentOut,
    DocumentRecordItem,
    DocumentResponse,
)
from app.services.document_record_service import DocumentRecordService
from app.services.document_service import DocumentService
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/{document_id}/extract", response_model=DocumentExtractResponse)
async def extract_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_service_api_key),
) -> DocumentExtractResponse:
    async def _runner() -> None:
        async with SessionLocal() as session:
            service = DocumentService(session, LocalStorageService())
            try:
                await service.extract_from_existing_ocr(document_id)
            except Exception:
                logger.exception("Background extraction failed for document %s", document_id)

    background_tasks.add_task(_runner)
    return DocumentExtractResponse(status="accepted", message="Extraction started")


@router.patch("/{document_id}/extraction", response_model=DocumentResponse)
async def update_document_extraction(
    document_id: uuid.UUID,
    payload: DocumentExtractionUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    service = DocumentService(session, LocalStorageService())
    return await service.update_extraction_result(user.id, document_id, payload.extraction_result)


@router.post("/{document_id}/accept", response_model=DocumentResponse)
async def accept_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    service = DocumentService(session, LocalStorageService())
    return await service.accept_document(user.id, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = DocumentService(session, LocalStorageService())
    await service.delete_document(user.id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/records", response_model=list[DocumentRecordItem])
async def list_document_records(
    record_type: str | None = Query(None),
    document_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentRecordItem]:
    service = DocumentRecordService(session)
    records = await service.list_records(user.id, record_type_code=record_type, document_id=document_id)
    return [
        DocumentRecordItem(
            record_type=r.record_type_code,
            data=r.data,
            document_id=r.document_id,
            recorded_at=r.recorded_at,
        )
        for r in records
    ]


@router.get("/{document_id}/detail", response_model=DocumentResponse)
async def get_document_detail(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    service = DocumentService(session, LocalStorageService())
    doc = await service.get_document(user.id, document_id)
    if not doc:
        raise NotFoundException("Document not found")
    return doc


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
