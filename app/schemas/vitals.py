from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMBaseSchema


class VitalsCreateRequest(ORMBaseSchema):
    recorded_at: date
    height: float | None = Field(default=None, gt=0, description="Height in centimeters")
    weight: float | None = Field(default=None, gt=0, description="Weight in kilograms")
    blood_group: str | None = Field(default=None, min_length=1, max_length=5)
    pressure: str | None = Field(default=None, min_length=1, max_length=20, description="Blood pressure, e.g. 120/80")
    blood_sugar: float | None = Field(default=None, gt=0, description="Blood sugar in mg/dL")


class VitalsUpdateRequest(ORMBaseSchema):
    recorded_at: date | None = None
    height: float | None = Field(default=None, gt=0, description="Height in centimeters")
    weight: float | None = Field(default=None, gt=0, description="Weight in kilograms")
    blood_group: str | None = Field(default=None, min_length=1, max_length=5)
    pressure: str | None = Field(default=None, min_length=1, max_length=20, description="Blood pressure, e.g. 120/80")
    blood_sugar: float | None = Field(default=None, gt=0, description="Blood sugar in mg/dL")


class VitalsResponse(ORMBaseSchema):
    id: UUID
    recorded_at: date
    height: float | None = None
    weight: float | None = None
    blood_group: str | None = None
    pressure: str | None = None
    blood_sugar: float | None = None
    created_at: datetime
    updated_at: datetime
