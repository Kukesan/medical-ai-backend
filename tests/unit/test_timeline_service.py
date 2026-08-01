import uuid
from datetime import date
from types import SimpleNamespace

from app.ai.timeline.service import TimelineService


def _visit(day: int):
    return SimpleNamespace(
        id=uuid.uuid4(),
        visit_date=date(2024, 1, day),
        doctor_name="Dr. Doe",
        hospital_name="City Hospital",
        medications=[SimpleNamespace(name="A")],
        lab_results=[SimpleNamespace(test_name="HbA1c")],
        clinical_notes=[SimpleNamespace(note_text="Follow up")],
    )


def test_timeline_sorted() -> None:
    svc = TimelineService()
    visits = [_visit(20), _visit(10)]

    timeline = svc.build(visits)

    assert len(timeline) == 2
    assert timeline[0]["visit_date"] == "2024-01-10"
