from app.models.enums import AlertCategory
from app.services.specialty_mapper import map_to_specialty


def test_keyword_match_overrides_category() -> None:
    specialty = map_to_specialty(
        AlertCategory.LAB_ABNORMALITY, "Elevated troponin", "Possible cardiac event", "", ""
    )
    assert specialty == "Cardiologist"


def test_category_fallback_when_no_keyword_match() -> None:
    specialty = map_to_specialty(AlertCategory.DRUG_INTERACTION, "Warfarin + Aspirin", "", "", "")
    assert specialty == "Pharmacist"


def test_default_fallback_for_unmapped_category_and_text() -> None:
    specialty = map_to_specialty(AlertCategory.MEDICATION_CHANGE, "Dosage updated", "", "", "")
    assert specialty == "General Physician"


def test_keyword_match_is_case_insensitive() -> None:
    specialty = map_to_specialty(
        AlertCategory.LAB_ABNORMALITY, "ELEVATED KIDNEY MARKERS", "", "", ""
    )
    assert specialty == "Nephrologist"
