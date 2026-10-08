from datetime import datetime

from pydantic import Field

from app.schemas.base import ORMBaseSchema
from app.schemas.common import Citation, SafetyWarning


class ChatAskRequest(ORMBaseSchema):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(ORMBaseSchema):
    session_id: str
    answer: str
    confidence: float
    citations: list[Citation]
    warning: SafetyWarning | None = None


class ChatMessageOut(ORMBaseSchema):
    role: str
    content: str
    confidence: float
    created_at: datetime


class ChatHistoryResponse(ORMBaseSchema):
    session_id: str
    messages: list[ChatMessageOut]
