from datetime import date

from pydantic import EmailStr, Field
from uuid import UUID

from app.schemas.base import ORMBaseSchema


class UserProfileResponse(ORMBaseSchema):
    id: UUID
    email: EmailStr
    full_name: str
    date_of_birth: date | None = None
    bio: str | None = None
    notes: str | None = None


class UserProfileCreateRequest(ORMBaseSchema):
    date_of_birth: date | None = None
    bio: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class AccountDeleteRequest(ORMBaseSchema):
    password: str = Field(min_length=1, max_length=128)


class UserProfileUpdateRequest(ORMBaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    bio: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
