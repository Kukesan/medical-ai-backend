import httpx
import pytest
import respx

from app.services import doctor_recommendation_service as module
from app.services.doctor_recommendation_service import (
    NOT_CONFIGURED_MESSAGE,
    UNAVAILABLE_MESSAGE,
    DoctorRecommendationService,
)

GEOCODE_URL = module.GEOCODE_URL
PLACES_URL = module.PLACES_SEARCH_TEXT_URL


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module.settings, "google_places_api_key", "test-key")


@pytest.mark.asyncio
async def test_missing_api_key_returns_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module.settings, "google_places_api_key", "")
    svc = DoctorRecommendationService()

    doctors, message = await svc.search("Cardiologist", "Colombo")

    assert doctors == []
    assert message == NOT_CONFIGURED_MESSAGE


@pytest.mark.asyncio
@respx.mock
async def test_geocode_zero_results_returns_message() -> None:
    respx.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json={"status": "ZERO_RESULTS", "results": []})
    )
    svc = DoctorRecommendationService()

    doctors, message = await svc.search("Cardiologist", "Nowhereville")

    assert doctors == []
    assert message is not None
    assert "Nowhereville" in message


@pytest.mark.asyncio
@respx.mock
async def test_places_zero_results_returns_message() -> None:
    respx.get(GEOCODE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "OK",
                "results": [{"geometry": {"location": {"lat": 6.9, "lng": 79.8}}}],
            },
        )
    )
    respx.post(PLACES_URL).mock(return_value=httpx.Response(200, json={"places": []}))
    svc = DoctorRecommendationService()

    doctors, message = await svc.search("Cardiologist", "Colombo")

    assert doctors == []
    assert message is not None
    assert "cardiologists" in message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_happy_path_returns_doctors_sorted_by_distance() -> None:
    respx.get(GEOCODE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "OK",
                "results": [{"geometry": {"location": {"lat": 6.9271, "lng": 79.8612}}}],
            },
        )
    )
    respx.post(PLACES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "places": [
                    {
                        "displayName": {"text": "Far Clinic"},
                        "formattedAddress": "Far Away St",
                        "location": {"latitude": 7.5, "longitude": 80.5},
                        "rating": 4.2,
                        "userRatingCount": 30,
                        "nationalPhoneNumber": "011-000-0000",
                        "businessStatus": "OPERATIONAL",
                        "googleMapsUri": "https://maps.google.com/far",
                    },
                    {
                        "displayName": {"text": "Near Clinic"},
                        "formattedAddress": "Near St",
                        "location": {"latitude": 6.93, "longitude": 79.86},
                        "rating": 4.8,
                        "userRatingCount": 120,
                        "nationalPhoneNumber": "011-111-1111",
                        "businessStatus": "OPERATIONAL",
                        "googleMapsUri": "https://maps.google.com/near",
                    },
                    {
                        "displayName": {"text": "Closed Clinic"},
                        "formattedAddress": "Closed St",
                        "location": {"latitude": 6.93, "longitude": 79.86},
                        "businessStatus": "CLOSED_PERMANENTLY",
                    },
                ]
            },
        )
    )
    svc = DoctorRecommendationService()

    doctors, message = await svc.search("Cardiologist", "Colombo")

    assert message is None
    assert [doctor.name for doctor in doctors] == ["Near Clinic", "Far Clinic"]
    assert doctors[0].distance_km < doctors[1].distance_km
    assert doctors[0].specialty == "Cardiologist"
    assert doctors[0].phone == "011-111-1111"


@pytest.mark.asyncio
@respx.mock
async def test_upstream_error_returns_unavailable_message() -> None:
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(500))
    svc = DoctorRecommendationService()

    doctors, message = await svc.search("Cardiologist", "Colombo")

    assert doctors == []
    assert message == UNAVAILABLE_MESSAGE
