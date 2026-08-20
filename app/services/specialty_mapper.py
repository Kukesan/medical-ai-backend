from app.models.enums import AlertCategory

_KEYWORD_SPECIALTIES: list[tuple[tuple[str, ...], str]] = [
    (("heart", "cardiac", "cardio"), "Cardiologist"),
    (("kidney", "renal"), "Nephrologist"),
    (("liver", "hepatic"), "Gastroenterologist"),
    (("lung", "respiratory", "pulmonary"), "Pulmonologist"),
    (("thyroid", "diabetes", "glucose", "endocrine"), "Endocrinologist"),
    (("blood", "anemia", "hemoglobin"), "Hematologist"),
    (("skin", "dermat"), "Dermatologist"),
    (("bone", "joint", "ortho"), "Orthopedist"),
    (("neuro", "brain", "nerve"), "Neurologist"),
    (("mental", "psych"), "Psychiatrist"),
    (("cancer", "tumor", "oncol"), "Oncologist"),
]

_CATEGORY_SPECIALTIES: dict[AlertCategory, str] = {
    AlertCategory.DRUG_INTERACTION: "Pharmacist",
    AlertCategory.DUPLICATE_MEDICATION: "Pharmacist",
    AlertCategory.DOSAGE_CONFLICT: "Pharmacist",
    AlertCategory.ALLERGY_CONFLICT: "Allergist",
    AlertCategory.MEDICATION_CHANGE: "General Physician",
    AlertCategory.LAB_ABNORMALITY: "General Physician",
}

_DEFAULT_SPECIALTY = "General Physician"


def map_to_specialty(category: AlertCategory, *text_fields: str | None) -> str:
    combined = " ".join(field for field in text_fields if field).lower()

    for keywords, specialty in _KEYWORD_SPECIALTIES:
        if any(keyword in combined for keyword in keywords):
            return specialty

    return _CATEGORY_SPECIALTIES.get(category, _DEFAULT_SPECIALTY)
