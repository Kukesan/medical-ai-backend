from app.main import app


def test_app_boots() -> None:
    assert app.title == "Yarlit Medical AI Backend"
