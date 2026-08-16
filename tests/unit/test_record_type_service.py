import pytest

from app.core.exceptions import ValidationException
from app.models.record_type import RecordType
from app.services.record_type_service import RecordTypeService


def _allergy_type() -> RecordType:
    return RecordType(
        code="ALLERGY",
        name="Allergy",
        json_schema={
            "type": "object",
            "required": ["substance"],
            "additionalProperties": False,
            "properties": {
                "substance": {"type": "string"},
                "reaction": {"type": ["string", "null"]},
                "severity": {"type": ["string", "null"], "enum": ["Mild", "Moderate", "Severe", None]},
            },
        },
        is_active=True,
        identity_field="substance",
    )


def _service() -> RecordTypeService:
    return RecordTypeService.__new__(RecordTypeService)


def test_valid_data_passes() -> None:
    service = _service()
    service.validate_data(_allergy_type(), {"substance": "Penicillin", "reaction": "Rash", "severity": "Severe"})


def test_missing_required_field_raises() -> None:
    service = _service()
    with pytest.raises(ValidationException):
        service.validate_data(_allergy_type(), {"reaction": "Rash"})


def test_bad_enum_value_raises() -> None:
    service = _service()
    with pytest.raises(ValidationException):
        service.validate_data(_allergy_type(), {"substance": "Penicillin", "severity": "Extreme"})


def test_unexpected_property_raises() -> None:
    service = _service()
    with pytest.raises(ValidationException):
        service.validate_data(_allergy_type(), {"substance": "Penicillin", "unexpected_field": "x"})


def test_wrong_type_raises() -> None:
    service = _service()
    with pytest.raises(ValidationException):
        service.validate_data(_allergy_type(), {"substance": 12345})
