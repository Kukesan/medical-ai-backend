import uuid

from fastapi import APIRouter, Query
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.enums import RecordStatus
from app.models.medical_record import MedicalRecord
from app.models.record_type import RecordType
from app.models.user import User
from app.schemas.medical_record import (
    MedicalRecordGroup,
    MedicalRecordListItem,
    MedicalRecordPatchRequest,
    ResolveConflictRequest,
)
from app.services.medical_record_service import MedicalRecordService
from app.services.record_type_service import RecordTypeService

router = APIRouter(prefix="/medical-records")


def _to_list_item(record: MedicalRecord, record_type: RecordType) -> MedicalRecordListItem:
    return MedicalRecordListItem(
        id=record.id,
        record_type=record_type.code,
        status=record.status,
        data=record.data,
        source_document_id=record.source_document_id,
        recorded_at=record.recorded_at,
        current_version=record.current_version,
        conflict_with_record_id=record.conflict_with_record_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=list[MedicalRecordListItem])
async def list_medical_records(
    status: RecordStatus | None = Query(None),
    record_type: str | None = Query(None),
    document_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    records = await record_service.list_records(
        user.id, status=status, record_type_code=record_type, document_id=document_id, limit=limit, offset=offset
    )

    type_cache: dict[uuid.UUID, RecordType] = {}
    items = []
    for record in records:
        if record.record_type_id not in type_cache:
            type_cache[record.record_type_id] = await type_service.get_by_id(record.record_type_id)
        items.append(_to_list_item(record, type_cache[record.record_type_id]))
    return items


@router.get("/grouped", response_model=list[MedicalRecordGroup])
async def list_medical_records_grouped(
    status: RecordStatus | None = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)

    grouped = await record_service.list_grouped_by_type(user.id, status=status)
    return [
        MedicalRecordGroup(
            record_type=record_type.code,
            record_type_name=record_type.name,
            records=[_to_list_item(record, record_type) for record in records],
        )
        for record_type, records in grouped.items()
    ]


@router.get("/{record_id}", response_model=MedicalRecordListItem)
async def get_medical_record(
    record_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    record = await record_service.get(user.id, record_id)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_list_item(record, record_type)


@router.patch("/{record_id}", response_model=MedicalRecordListItem)
async def patch_medical_record(
    record_id: uuid.UUID,
    payload: MedicalRecordPatchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    record = await record_service.patch(user.id, record_id, payload.data)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_list_item(record, record_type)


@router.post("/{record_id}/verify", response_model=MedicalRecordListItem)
async def verify_medical_record(
    record_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    record = await record_service.verify(user.id, record_id)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_list_item(record, record_type)


@router.post("/{record_id}/reject", response_model=MedicalRecordListItem)
async def reject_medical_record(
    record_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    record = await record_service.reject(user.id, record_id)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_list_item(record, record_type)


@router.post("/{record_id}/resolve-conflict", response_model=MedicalRecordListItem)
async def resolve_medical_record_conflict(
    record_id: uuid.UUID,
    payload: ResolveConflictRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record_service = MedicalRecordService(session)
    type_service = RecordTypeService(session)

    record = await record_service.resolve_conflict(user.id, record_id, payload.resolution)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_list_item(record, record_type)
