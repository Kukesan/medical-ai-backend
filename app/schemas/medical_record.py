from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from app.models.enums import RecordStatus
from app.schemas.base import ORMBaseSchema


class RecordTypeResponse(ORMBaseSchema):
    id: UUID
    code: str
    name: str
    description: str | None = None
    json_schema: dict[str, Any]
    is_active: bool


class MedicalRecordListItem(ORMBaseSchema):
    id: UUID
    record_type: str
    status: RecordStatus
    data: dict[str, Any]
    source_document_id: UUID | None = None
    recorded_at: date | None = None
    current_version: int
    conflict_with_record_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MedicalRecordPatchRequest(ORMBaseSchema):
    data: dict[str, Any]


class ResolveConflictRequest(ORMBaseSchema):
    resolution: Literal["keep_existing", "accept_incoming"]
