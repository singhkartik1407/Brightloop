import uuid

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator
)

from app.core.password_policy import validate_password_policy
from app.models.user import UserRole


class RegisterRequest(BaseModel):

    email: EmailStr
    password: str = Field(min_length=9, max_length=128)

    display_name: str = Field(min_length=1, max_length=200)

    company_name: str | None = Field(default=None, max_length=200)

    billing_email: EmailStr | None = None

    phone: str | None = Field(default=None, max_length=30)

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_policy(value)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Display name cannot be empty.")

        return value


class LoginRequest(BaseModel):

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class CustomerRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    company_name: str | None
    billing_email: EmailStr


class RegisterResponse(BaseModel):

    user: UserRead
    customer: CustomerRead


class LoginResponse(BaseModel):

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead