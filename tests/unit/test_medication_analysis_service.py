import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.medication_analysis_service import MedicationAnalysisService


def _record(data: dict, source_document_id=None) -> SimpleNamespace:
    return SimpleNamespace(data=data, source_document_id=source_document_id)


@pytest.mark.asyncio
async def test_analyze_adapts_medical_records_into_interaction_check_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MedicationAnalysisService(AsyncMock())
    doc_id = uuid.uuid4()

    async def fake_list_data_by_type(user_id, record_type_code, exclude_status=None):
        if record_type_code == "MEDICATION":
            return [_record({"name": "Penicillin", "dosage": "500mg"}, source_document_id=doc_id)]
        if record_type_code == "ALLERGY":
            return [_record({"substance": "Penicillin"}, source_document_id=doc_id)]
        raise AssertionError(f"unexpected record type {record_type_code}")

    monkeypatch.setattr(service.record_service, "list_data_by_type", fake_list_data_by_type)

    result = await service.analyze(uuid.uuid4())

    assert len(result["allergy_alerts"]) == 1
    assert result["allergy_alerts"][0]["details"] == "Medication Penicillin matches recorded allergy."
    assert result["allergy_alerts"][0]["assessment"]["evidence"][0]["source_document_id"] == str(doc_id)


@pytest.mark.asyncio
async def test_analyze_parses_end_date_for_expired_prescriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MedicationAnalysisService(AsyncMock())

    async def fake_list_data_by_type(user_id, record_type_code, exclude_status=None):
        if record_type_code == "MEDICATION":
            return [_record({"name": "Amoxicillin", "end_date": "2020-01-01"})]
        return []

    monkeypatch.setattr(service.record_service, "list_data_by_type", fake_list_data_by_type)

    result = await service.analyze(uuid.uuid4())

    assert len(result["expired_prescriptions"]) == 1
    assert "Amoxicillin" in result["expired_prescriptions"][0]["details"]
