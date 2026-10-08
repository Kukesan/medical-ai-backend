from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field

from app.schemas.base import ORMBaseSchema

# Emails are stored and compared lowercase so "John@x.com" and "john@x.com" are the same account.
NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda value: value.strip().lower())]
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]


def _require_true(value: bool) -> bool:
    if value is not True:
        raise ValueError("You must accept the Terms of Use and Privacy Policy")
    return value


class UserCreate(ORMBaseSchema):
    email: NormalizedEmail
    full_name: str = Field(min_length=2, max_length=255)
    password: NewPassword
    accept_terms: Annotated[bool, AfterValidator(_require_true)]


class UserLogin(ORMBaseSchema):
    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(ORMBaseSchema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: NewPassword


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
    refresh_token: str = Field(max_length=4096)
