from datetime import datetime

from app.schemas.base import ORMBaseSchema
from app.schemas.common import Citation, SafetyWarning


class ConsultantAskRequest(ORMBaseSchema):
    question: str
    session_id: str | None = None


class ConsultantResponse(ORMBaseSchema):
    session_id: str
    answer: str
    confidence: float
    citations: list[Citation]
    warning: SafetyWarning | None = None


class ConsultantMessageOut(ORMBaseSchema):
    role: str
    content: str
    confidence: float
    created_at: datetime


class ConsultantHistoryResponse(ORMBaseSchema):
    session_id: str
    messages: list[ConsultantMessageOut]
