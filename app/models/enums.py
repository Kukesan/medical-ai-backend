from enum import StrEnum


class DocumentType(StrEnum):
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    CLINICAL_NOTE = "clinical_note"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    OCR_COMPLETED = "ocr_completed"
    EXTRACTED = "extracted"
    ANALYZED = "analyzed"
    FAILED = "failed"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertCategory(StrEnum):
    DRUG_INTERACTION = "drug_interaction"
    DUPLICATE_MEDICATION = "duplicate_medication"
    ALLERGY_CONFLICT = "allergy_conflict"
    DOSAGE_CONFLICT = "dosage_conflict"
    MEDICATION_CHANGE = "medication_change"
    LAB_ABNORMALITY = "lab_abnormality"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
