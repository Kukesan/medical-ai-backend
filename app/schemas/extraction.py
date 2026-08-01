from datetime import date

from app.schemas.base import ORMBaseSchema
from app.schemas.common import ConfidenceField


class ExtractedMedication(ORMBaseSchema):
    name: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    confidence: float


class ExtractedLabResult(ORMBaseSchema):
    test_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    confidence: float


class StructuredExtraction(ORMBaseSchema):
    visit_date: date | None = None
    visit_date_meta: ConfidenceField | None = None
    doctor: str | None = None
    doctor_meta: ConfidenceField | None = None
    hospital: str | None = None
    hospital_meta: ConfidenceField | None = None
    medications: list[ExtractedMedication]
    lab_results: list[ExtractedLabResult]
    diagnosis_if_explicit: str | None = None
    diagnosis_meta: ConfidenceField | None = None
    allergies: list[str]
    clinical_notes: list[str]
