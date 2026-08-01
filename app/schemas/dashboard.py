from app.schemas.analysis import AlertItem
from app.schemas.base import ORMBaseSchema
from app.schemas.chat import ChatMessageOut
from app.schemas.document import DocumentOut
from app.schemas.lab import LabTrendItem
from app.schemas.timeline import TimelineEntry


class DashboardResponse(ORMBaseSchema):
    timeline: list[TimelineEntry]
    medications: list[str]
    drug_alerts: list[AlertItem]
    lab_trends: list[LabTrendItem]
    allergy_alerts: list[AlertItem]
    recent_uploads: list[DocumentOut]
    chat_history: list[ChatMessageOut]
