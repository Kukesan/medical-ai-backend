from app.models.enums import RiskLevel
from app.schemas.base import ORMBaseSchema


class Citation(ORMBaseSchema):
    source_document_id: str
    snippet: str
    page: int | None = None


class ConfidenceField(ORMBaseSchema):
    confidence: float
    evidence: str | None = None


class SafetyWarning(ORMBaseSchema):
    message: str
    recommend_doctor_consult: bool = True


class RiskAssessment(ORMBaseSchema):
    risk_level: RiskLevel
    explanation: str
    evidence: list[Citation]
    confidence: float
