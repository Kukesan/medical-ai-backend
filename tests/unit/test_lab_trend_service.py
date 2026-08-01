from datetime import date
from types import SimpleNamespace

from app.ai.trend_analysis.lab_trend_service import LabTrendService


def _lab(test_name: str, value: float):
    return SimpleNamespace(
        test_name=test_name,
        value=value,
        reference_range="70-100",
        observed_date=date.today(),
    )


def test_increasing_trend() -> None:
    svc = LabTrendService()
    rows = [_lab("Blood Sugar", 90.0), _lab("Blood Sugar", 130.0)]

    trends = svc.build_trends(rows)

    assert len(trends) == 1
    assert trends[0]["trend_direction"] == "increasing"
