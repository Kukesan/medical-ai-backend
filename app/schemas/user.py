from pydantic import EmailStr, Field
from uuid import UUID

from app.schemas.base import ORMBaseSchema


class UserProfileResponse(ORMBaseSchema):
    id: UUID
    email: EmailStr
    full_name: str
    age: int | None = None
    height: float | None = None
    weight: float | None = None
    blood_group: str | None = None
    pressure: str | None = None
    blood_sugar: float | None = None


class UserProfileCreateRequest(ORMBaseSchema):
    age: int = Field(gt=0, lt=150)
    height: float = Field(gt=0, description="Height in centimeters")
    weight: float = Field(gt=0, description="Weight in kilograms")
    blood_group: str = Field(min_length=1, max_length=5)
    pressure: str = Field(min_length=1, max_length=20, description="Blood pressure, e.g. 120/80")
    blood_sugar: float = Field(gt=0, description="Blood sugar in mg/dL")


class UserProfileUpdateRequest(ORMBaseSchema):
    age: int | None = Field(default=None, gt=0, lt=150)
    height: float | None = Field(default=None, gt=0, description="Height in centimeters")
    weight: float | None = Field(default=None, gt=0, description="Weight in kilograms")
    blood_group: str | None = Field(default=None, min_length=1, max_length=5)
    pressure: str | None = Field(default=None, min_length=1, max_length=20, description="Blood pressure, e.g. 120/80")
    blood_sugar: float | None = Field(default=None, gt=0, description="Blood sugar in mg/dL")
