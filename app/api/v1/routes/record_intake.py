import uuid

from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.medical_record import MedicalRecord
from app.models.record_intake_session import RecordIntakeSession
from app.models.record_type import RecordType
from app.models.user import User
from app.schemas.medical_record import MedicalRecordListItem
from app.schemas.record_intake import (
    RecordIntakeAnswerRequest,
    RecordIntakeConfirmRequest,
    RecordIntakeResponse,
    RecordIntakeStartRequest,
)
from app.services.record_intake_service import RecordIntakeService
from app.services.record_type_service import RecordTypeService

router = APIRouter(prefix="/record-intake")


def _to_response(intake: RecordIntakeSession, record_type: RecordType | None) -> RecordIntakeResponse:
    return RecordIntakeResponse(
        id=intake.id,
        status=intake.status,
        record_type=record_type.code if record_type else None,
        record_type_name=record_type.name if record_type else None,
        is_new_record_type=intake.is_new_record_type,
        data=intake.draft_data,
        missing_fields=intake.missing_fields,
        pending_question=intake.pending_question,
        questions_asked=intake.questions_asked,
        recorded_at=intake.recorded_at,
        resulting_record_id=intake.resulting_record_id,
        created_at=intake.created_at,
        updated_at=intake.updated_at,
    )


def _to_record_item(record: MedicalRecord, record_type: RecordType) -> MedicalRecordListItem:
    return MedicalRecordListItem(
        id=record.id,
        record_type=record_type.code,
        status=record.status,
        data=record.data,
        recorded_at=record.recorded_at,
        current_version=record.current_version,
        conflict_with_record_id=record.conflict_with_record_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("", response_model=RecordIntakeResponse)
async def start_record_intake(
    payload: RecordIntakeStartRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    intake_service = RecordIntakeService(session)
    type_service = RecordTypeService(session)

    intake = await intake_service.start(user.id, payload.text)
    record_type = await type_service.get_by_id(intake.record_type_id) if intake.record_type_id else None
    return _to_response(intake, record_type)


@router.get("/{intake_id}", response_model=RecordIntakeResponse)
async def get_record_intake(
    intake_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    intake_service = RecordIntakeService(session)
    type_service = RecordTypeService(session)

    intake = await intake_service.get(user.id, intake_id)
    record_type = await type_service.get_by_id(intake.record_type_id) if intake.record_type_id else None
    return _to_response(intake, record_type)


@router.post("/{intake_id}/answer", response_model=RecordIntakeResponse)
async def answer_record_intake(
    intake_id: uuid.UUID,
    payload: RecordIntakeAnswerRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    intake_service = RecordIntakeService(session)
    type_service = RecordTypeService(session)

    intake = await intake_service.answer(user.id, intake_id, payload.answer)
    record_type = await type_service.get_by_id(intake.record_type_id) if intake.record_type_id else None
    return _to_response(intake, record_type)


@router.post("/{intake_id}/confirm", response_model=MedicalRecordListItem)
async def confirm_record_intake(
    intake_id: uuid.UUID,
    payload: RecordIntakeConfirmRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    intake_service = RecordIntakeService(session)
    type_service = RecordTypeService(session)

    record = await intake_service.confirm(user.id, intake_id, payload.data)
    record_type = await type_service.get_by_id(record.record_type_id)
    return _to_record_item(record, record_type)


@router.post("/{intake_id}/abandon", response_model=RecordIntakeResponse)
async def abandon_record_intake(
    intake_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    intake_service = RecordIntakeService(session)
    type_service = RecordTypeService(session)

    intake = await intake_service.abandon(user.id, intake_id)
    record_type = await type_service.get_by_id(intake.record_type_id) if intake.record_type_id else None
    return _to_response(intake, record_type)
