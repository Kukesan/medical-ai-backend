from fastapi.testclient import TestClient

from app.main import app


def test_app_boots() -> None:
    assert app.title == "Yarlit Medical AI Backend"


def test_scalar_docs_endpoint_available() -> None:
    client = TestClient(app)
    response = client.get("/scalar")

    assert response.status_code == 200
    assert "scalar" in response.text.lower()
