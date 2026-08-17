from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.models.enums import IntakeStatus
from app.schemas.base import ORMBaseSchema


class RecordIntakeStartRequest(ORMBaseSchema):
    text: str


class RecordIntakeAnswerRequest(ORMBaseSchema):
    answer: str


class RecordIntakeConfirmRequest(ORMBaseSchema):
    data: dict[str, Any] | None = None


class RecordIntakeResponse(ORMBaseSchema):
    id: UUID
    status: IntakeStatus
    record_type: str | None = None
    record_type_name: str | None = None
    is_new_record_type: bool
    data: dict[str, Any]
    missing_fields: list[str]
    pending_question: str | None = None
    questions_asked: int
    recorded_at: date | None = None
    resulting_record_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
