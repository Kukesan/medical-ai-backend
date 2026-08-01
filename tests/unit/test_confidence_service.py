from app.services.confidence_service import ConfidenceService


def test_normalize() -> None:
    svc = ConfidenceService()
    assert svc.normalize(None) == 0.0
    assert svc.normalize(-1) == 0.0
    assert svc.normalize(2.5) == 1.0
    assert svc.normalize(0.42) == 0.42


def test_warning_rule() -> None:
    svc = ConfidenceService()
    assert svc.requires_warning("high", 0.9)
    assert svc.requires_warning("low", 0.1)
    assert not svc.requires_warning("low", 0.8)
