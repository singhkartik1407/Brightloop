from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_policy import validate_password_policy


class StaffCreateRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=9,
        max_length=128
    )

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_policy(value)