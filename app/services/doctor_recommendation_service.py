import logging
import math

import httpx

from app.core.config import settings
from app.schemas.doctor_recommendation import DoctorResult

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.location,places.rating,"
    "places.userRatingCount,places.nationalPhoneNumber,places.businessStatus,places.googleMapsUri"
)
SEARCH_RADIUS_METERS = 20000.0
MAX_RESULTS = 10

NOT_CONFIGURED_MESSAGE = "Doctor search is not configured."
UNAVAILABLE_MESSAGE = "Doctor search is temporarily unavailable. Please try again."


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DoctorRecommendationService:
    async def search(self, specialty: str, location: str) -> tuple[list[DoctorResult], str | None]:
        if not settings.google_places_api_key:
            return [], NOT_CONFIGURED_MESSAGE

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                origin = await self._geocode(client, location)
                if origin is None:
                    return [], (
                        f"Could not find '{location}'. Try a nearby city or a more specific area."
                    )

                places = await self._search_places(client, specialty, origin)
        except httpx.HTTPError:
            logger.exception("Doctor recommendation search failed")
            return [], UNAVAILABLE_MESSAGE

        if not places:
            return [], (
                f"No {specialty.lower()}s found near {location}. Try widening your search area."
            )

        lat, lng = origin
        doctors = [self._to_doctor_result(place, specialty, lat, lng) for place in places]
        doctors.sort(key=lambda doctor: (doctor.distance_km is None, doctor.distance_km))
        return doctors[:MAX_RESULTS], None

    async def _geocode(
        self, client: httpx.AsyncClient, location: str
    ) -> tuple[float, float] | None:
        response = await client.get(
            GEOCODE_URL,
            params={"address": location, "key": settings.google_places_api_key},
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return None

        geo_location = data["results"][0]["geometry"]["location"]
        return geo_location["lat"], geo_location["lng"]

    async def _search_places(
        self, client: httpx.AsyncClient, specialty: str, origin: tuple[float, float]
    ) -> list[dict]:
        lat, lng = origin
        response = await client.post(
            PLACES_SEARCH_TEXT_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.google_places_api_key,
                "X-Goog-FieldMask": PLACES_FIELD_MASK,
            },
            json={
                "textQuery": f"{specialty} near {lat},{lng}",
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": SEARCH_RADIUS_METERS,
                    }
                },
            },
        )
        response.raise_for_status()
        places = response.json().get("places", [])
        return [place for place in places if place.get("businessStatus") != "CLOSED_PERMANENTLY"]

    @staticmethod
    def _to_doctor_result(
        place: dict, specialty: str, origin_lat: float, origin_lng: float
    ) -> DoctorResult:
        place_location = place.get("location") or {}
        distance_km: float | None = None
        if "latitude" in place_location and "longitude" in place_location:
            distance_km = round(
                _haversine_km(
                    origin_lat, origin_lng, place_location["latitude"], place_location["longitude"]
                ),
                1,
            )

        return DoctorResult(
            name=(place.get("displayName") or {}).get("text", "Unknown"),
            specialty=specialty,
            address=place.get("formattedAddress", ""),
            distance_km=distance_km,
            rating=place.get("rating"),
            user_ratings_total=place.get("userRatingCount"),
            phone=place.get("nationalPhoneNumber"),
            maps_url=place.get("googleMapsUri"),
        )
