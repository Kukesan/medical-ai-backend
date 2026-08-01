import uuid
from datetime import date, timedelta
from types import SimpleNamespace

from app.ai.interaction_checker.drug_interaction_service import DrugInteractionService


def _med(name: str, dosage: str = "10mg", end_days_offset: int = 10):
    visit = SimpleNamespace(document_id=uuid.uuid4())
    return SimpleNamespace(
        name=name,
        dosage=dosage,
        frequency="daily",
        visit=visit,
        end_date=date.today() + timedelta(days=end_days_offset),
    )


def test_detects_known_interaction() -> None:
    svc = DrugInteractionService()
    meds = [_med("Warfarin"), _med("Aspirin")]

    result = svc.analyze(meds, allergies=set())

    assert len(result["drug_interactions"]) == 1
    alert = result["drug_interactions"][0]
    assert "Warfarin" in alert["details"] or "Aspirin" in alert["details"]


def test_detects_allergy_conflict() -> None:
    svc = DrugInteractionService()
    meds = [_med("Penicillin")]

    result = svc.analyze(meds, allergies={"Penicillin"})

    assert len(result["allergy_alerts"]) == 1
