from datetime import date

from app.schemas.base import ORMBaseSchema
from app.schemas.common import ConfidenceField


class ExtractedMedication(ORMBaseSchema):
    name: str | None = None
    dosage: str | None = None
    dosage_value: float | None = None
    dosage_unit: str | None = None
    frequency: str | None = None
    duration: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float | None = None


class ExtractedLabResult(ORMBaseSchema):
    test_name: str | None = None
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    observed_date: date | None = None
    confidence: float | None = None

class ExtractedAllergy(ORMBaseSchema):
    substance: str | None = None
    reaction: str | None = None
    severity: str | None = None
    confidence: float  | None = None

class ExtractedMedicalVisit(ORMBaseSchema):
    visit_date: date | None = None
    doctor_name: str | None = None
    hospital_name: str | None = None
    diagnosis_text: str | None = None

class StructuredExtraction(ORMBaseSchema):
    visit_date: date | None = None
    visit_date_meta: ConfidenceField | None = None
    doctor_name: str | None = None
    doctor_name_meta: ConfidenceField | None = None
    hospital_name: str | None = None
    hospital_name_meta: ConfidenceField | None = None
    medications: list[ExtractedMedication]
    lab_results: list[ExtractedLabResult]
    diagnosis_text: str | None = None
    diagnosis_text_meta: ConfidenceField | None = None
    allergies: list[str]
    clinical_notes: list[str]
