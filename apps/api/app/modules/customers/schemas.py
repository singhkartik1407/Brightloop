
import uuid

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator
)


# -------------------------------
# CREATE CUSTOMER
# -------------------------------

class CustomerCreateRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    billing_email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    tax_identifier: str | None = Field(default=None, max_length=50)

    billing_address_line1: str | None = Field(default=None, max_length=255)
    billing_address_line2: str | None = Field(default=None, max_length=255)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_state: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=20)
    billing_country_code: str | None = Field(default=None, max_length=2)

    notes: str | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Customer name cannot be empty.")
        return value

    @field_validator(
        "company_name",
        "phone",
        "tax_identifier",
        "billing_address_line1",
        "billing_address_line2",
        "billing_city",
        "billing_state",
        "billing_postal_code",
        "notes"
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        return value.strip() or None

    @field_validator("billing_country_code")
    @classmethod
    def validate_country_code(cls, value):
        if value is None or not value.strip():
            return None

        value = value.strip().upper()

        if len(value) != 2:
            raise ValueError("Country code must contain exactly 2 characters.")

        return value


# -------------------------------
# UPDATE CUSTOMER
# -------------------------------

class CustomerUpdateFields(BaseModel):

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    billing_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    tax_identifier: str | None = Field(default=None, max_length=50)

    billing_address_line1: str | None = Field(default=None, max_length=255)
    billing_address_line2: str | None = Field(default=None, max_length=255)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_state: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=20)
    billing_country_code: str | None = Field(default=None, max_length=2)

    @field_validator("display_name", mode="before")
    @classmethod
    def validate_display_name(cls, value):
        if value is None:
            raise ValueError("Customer name cannot be null.")

        if not isinstance(value, str):
            raise ValueError("Customer name must be text.")

        value = value.strip()

        if not value:
            raise ValueError("Customer name cannot be empty.")

        return value

    @field_validator("billing_email", mode="before")
    @classmethod
    def validate_billing_email(cls, value):
        if value is None:
            raise ValueError("Billing email cannot be null.")
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "company_name",
        "phone",
        "tax_identifier",
        "billing_address_line1",
        "billing_address_line2",
        "billing_city",
        "billing_state",
        "billing_postal_code"
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        return value.strip() or None

    @field_validator("billing_country_code")
    @classmethod
    def validate_country_code(cls, value):
        if value is None or not value.strip():
            return None

        value = value.strip().upper()

        if len(value) != 2:
            raise ValueError("Country code must contain exactly 2 characters.")

        return value


class CustomerUpdateRequest(CustomerUpdateFields):

    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value):
        return value.strip() or None if value is not None else None


# Customer self-service cannot update internal notes.
class CustomerSelfUpdateRequest(CustomerUpdateFields):
    pass


# -------------------------------
# CUSTOMER RESPONSE
# -------------------------------

class CustomerRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None

    display_name: str
    company_name: str | None
    billing_email: EmailStr

    phone: str | None
    tax_identifier: str | None

    billing_address_line1: str | None
    billing_address_line2: str | None
    billing_city: str | None
    billing_state: str | None
    billing_postal_code: str | None
    billing_country_code: str | None

    notes: str | None

    is_active: bool

    created_at: datetime
    updated_at: datetime


# Customer portal response: excludes internal notes and user linkage.
class CustomerProfileRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    company_name: str | None
    billing_email: EmailStr

    phone: str | None
    tax_identifier: str | None

    billing_address_line1: str | None
    billing_address_line2: str | None
    billing_city: str | None
    billing_state: str | None
    billing_postal_code: str | None
    billing_country_code: str | None

    is_active: bool

    created_at: datetime
    updated_at: datetime


# -------------------------------
# PAGINATED CUSTOMER RESPONSE
# -------------------------------

class CustomerListResponse(BaseModel):

    items: list[CustomerRead]

    total: int
    page: int
    page_size: int
    pages: int
