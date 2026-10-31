from __future__ import annotations

import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.quotation import QuotationStatus
from app.modules.quotation_templates.schemas import SubscriptionLineInput


class InvoiceTax(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    code: str
    rate_percent: str = Field(
        validation_alias="rate_percent", serialization_alias="ratePercent"
    )
    amount: str


class InvoiceLine(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID | None = Field(
        default=None, validation_alias="product_id", serialization_alias="productId"
    )
    description: str
    quantity: int = Field(ge=1)
    unit_price: str = Field(
        validation_alias="unit_price", serialization_alias="unitPrice"
    )
    selected_variants: list[str] = Field(
        default_factory=list,
        validation_alias="selected_variants",
        serialization_alias="selectedVariants",
    )
    taxes: list[InvoiceTax] = Field(default_factory=list)
    line_subtotal: str = Field(
        validation_alias="line_subtotal", serialization_alias="lineSubtotal"
    )
    tax_amount: str = Field(
        validation_alias="tax_amount", serialization_alias="taxAmount"
    )
    discount_amount: str = Field(
        validation_alias="discount_amount", serialization_alias="discountAmount"
    )
    line_total: str = Field(
        validation_alias="line_total", serialization_alias="lineTotal"
    )


class QuotationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    customer_id: uuid.UUID = Field(
        validation_alias="customerId", serialization_alias="customerId"
    )
    template_id: uuid.UUID | None = Field(
        default=None, validation_alias="templateId", serialization_alias="templateId"
    )
    plan_id: uuid.UUID | None = Field(
        default=None, validation_alias="planId", serialization_alias="planId"
    )
    start_date: date = Field(
        validation_alias="startDate", serialization_alias="startDate"
    )
    payment_terms: str | None = Field(
        default=None, max_length=500, validation_alias="paymentTerms", serialization_alias="paymentTerms"
    )
    validity_days: int | None = Field(
        default=None, ge=1, validation_alias="validityDays", serialization_alias="validityDays"
    )
    lines: list[SubscriptionLineInput] | None = None
    discount_code: str | None = Field(
        default=None, validation_alias="discountCode", serialization_alias="discountCode"
    )


class QuotationUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    plan_id: uuid.UUID | None = Field(
        default=None, validation_alias="planId", serialization_alias="planId"
    )
    start_date: date | None = Field(
        default=None, validation_alias="startDate", serialization_alias="startDate"
    )
    payment_terms: str | None = Field(
        default=None, max_length=500, validation_alias="paymentTerms", serialization_alias="paymentTerms"
    )
    validity_days: int | None = Field(
        default=None, ge=1, validation_alias="validityDays", serialization_alias="validityDays"
    )
    lines: list[SubscriptionLineInput] | None = None
    discount_code: str | None = Field(
        default=None, validation_alias="discountCode", serialization_alias="discountCode"
    )


class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    number: str
    customer_id: uuid.UUID = Field(
        validation_alias="customer_id", serialization_alias="customerId"
    )
    customer_name: str = Field(
        validation_alias="customer_name", serialization_alias="customerName"
    )
    plan_id: uuid.UUID = Field(
        validation_alias="plan_id", serialization_alias="planId"
    )
    plan_name: str = Field(
        validation_alias="plan_name", serialization_alias="planName"
    )
    status: QuotationStatus
    start_date: date = Field(
        validation_alias="start_date", serialization_alias="startDate"
    )
    expires_at: datetime = Field(
        validation_alias="expires_at", serialization_alias="expiresAt"
    )
    payment_terms: str | None = Field(
        default=None, validation_alias="payment_terms", serialization_alias="paymentTerms"
    )
    lines: list[InvoiceLine]
    subtotal: str
    tax_total: str = Field(
        validation_alias="tax_total", serialization_alias="taxTotal"
    )
    discount_total: str = Field(
        validation_alias="discount_total", serialization_alias="discountTotal"
    )
    total: str
    currency: str
    subscription_id: uuid.UUID | None = Field(
        default=None, validation_alias="subscription_id", serialization_alias="subscriptionId"
    )
    created_at: datetime = Field(
        validation_alias="created_at", serialization_alias="createdAt"
    )
