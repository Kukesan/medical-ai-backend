from datetime import datetime
from uuid import UUID

from app.models.enums import ChatContextType
from app.schemas.base import ORMBaseSchema
from app.schemas.common import Citation, SafetyWarning


class ConsultantAskRequest(ORMBaseSchema):
    question: str
    session_id: str | None = None
    context_type: ChatContextType | None = None
    context_id: str | None = None


class ConsultantResponse(ORMBaseSchema):
    session_id: str
    answer: str
    confidence: float
    citations: list[Citation]
    warning: SafetyWarning | None = None
    context_type: ChatContextType | None = None
    context_label: str | None = None


class ConsultantMessageOut(ORMBaseSchema):
    role: str
    content: str
    confidence: float
    created_at: datetime


class ConsultantHistoryResponse(ORMBaseSchema):
    session_id: str
    messages: list[ConsultantMessageOut]

class ConversationListResponse(ORMBaseSchema):
    title: str
    session_id: UUID
    updated_at: datetime
    context_type: ChatContextType | None = None
    context_label: str | None = None