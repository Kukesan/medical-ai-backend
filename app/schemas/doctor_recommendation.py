import uuid

from pydantic import Field

from app.schemas.base import ORMBaseSchema


class DoctorSearchRequest(ORMBaseSchema):
    analysis_result_id: uuid.UUID | None = None
    specialty_override: str | None = None
    location: str = Field(min_length=1, max_length=200)
    availability: str = Field(min_length=1, max_length=200)


class DoctorResult(ORMBaseSchema):
    name: str
    specialty: str
    address: str
    distance_km: float | None = None
    rating: float | None = None
    user_ratings_total: int | None = None
    phone: str | None = None
    maps_url: str | None = None


class DoctorSearchResponse(ORMBaseSchema):
    specialty: str
    availability: str
    doctors: list[DoctorResult]
    message: str | None = None
