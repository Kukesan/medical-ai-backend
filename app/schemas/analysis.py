from app.schemas.base import ORMBaseSchema
from app.schemas.common import RiskAssessment, SafetyWarning


class AnalysisRunRequest(ORMBaseSchema):
    document_ids: list[str]


class AlertItem(ORMBaseSchema):
    category: str
    details: str
    assessment: RiskAssessment


class MedicationAnalysisResponse(ORMBaseSchema):
    duplicate_medications: list[AlertItem]
    drug_interactions: list[AlertItem]
    conflicting_dosages: list[AlertItem]
    expired_prescriptions: list[AlertItem]
    medication_changes: list[AlertItem]
    warning: SafetyWarning


class AnalysisRunResponse(ORMBaseSchema):
    status: str
    message: str
