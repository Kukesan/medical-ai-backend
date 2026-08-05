from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime as DateTime

from app.models.enums import RiskLevel


class AlertCategory(str, Enum):
    DRUG_INTERACTION = "drug_interaction"
    DUPLICATE_MEDICATION = "duplicate_medication"
    ALLERGY_CONFLICT = "allergy_conflict"
    DOSAGE_CONFLICT = "dosage_conflict"
    MEDICATION_CHANGE = "medication_change"
    LAB_ABNORMALITY = "lab_abnormality"


class MedicationEvidence(BaseModel):
    document_id: str | None = None
    snippet: str


class MedicationTimeline(BaseModel):
    document_id: str | None = None
    date: str | None = None
    finding: str


class MedicationAlert(BaseModel):
    category: AlertCategory
    risk_level: RiskLevel
    title: str
    description: str
    clinical_reason: str
    confidence: float = Field(
        ge=0,
        le=1,
        description="AI confidence score between 0 and 1"
    )
    timeline: list[MedicationTimeline] = []
    evidence: list[MedicationEvidence] = []
    recommendation: str


class MedicationReviewResult(BaseModel):
    overall_risk: RiskLevel
    summary: str
    alerts: list[MedicationAlert] = []

class MedicalDocumentInput(BaseModel):
    document_id: UUID
    document_date: str | None = None
    ocr_text: str

class MedicalAnalysisReponse(BaseModel):
    id: UUID
    user_id: UUID
    category: AlertCategory
    risk_level: RiskLevel
    title: str
    description: str
    clinical_reason: str
    confidence: float = Field(
        ge=0,
        le=1,
        description="AI confidence score between 0 and 1"
    )
    timeline: list[MedicationTimeline] = []
    evidence: list[MedicationEvidence] = []
    recommendation: str
    created_at: DateTime