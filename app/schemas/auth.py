from pydantic import EmailStr, Field

from app.schemas.base import ORMBaseSchema


class UserCreate(ORMBaseSchema):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(ORMBaseSchema):
    email: EmailStr
    password: str


class UserOut(ORMBaseSchema):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool


class TokenPair(ORMBaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(ORMBaseSchema):
    refresh_token: str
