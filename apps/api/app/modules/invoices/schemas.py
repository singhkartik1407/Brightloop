from __future__ import annotations

import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.invoice import InvoiceStatus


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
    quantity: int = Field(default=1, ge=1)
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


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    number: str
    customer_id: uuid.UUID = Field(
        validation_alias="customer_id", serialization_alias="customerId"
    )
    customer_name: str | None = Field(
        default=None, validation_alias="customer_name", serialization_alias="customerName"
    )
    subscription_id: uuid.UUID | None = Field(
        default=None, validation_alias="subscription_id", serialization_alias="subscriptionId"
    )
    quotation_id: uuid.UUID | None = Field(
        default=None, validation_alias="quotation_id", serialization_alias="quotationId"
    )
    status: InvoiceStatus
    issue_date: date = Field(
        validation_alias="issue_date", serialization_alias="issueDate"
    )
    due_date: date = Field(
        validation_alias="due_date", serialization_alias="dueDate"
    )
    period_start: date | None = Field(
        default=None, validation_alias="period_start", serialization_alias="periodStart"
    )
    period_end: date | None = Field(
        default=None, validation_alias="period_end", serialization_alias="periodEnd"
    )
    lines: list[InvoiceLine] = Field(default_factory=list)
    subtotal: str
    tax_total: str = Field(
        validation_alias="tax_total", serialization_alias="taxTotal"
    )
    discount_total: str = Field(
        validation_alias="discount_total", serialization_alias="discountTotal"
    )
    total: str
    amount_paid: str = Field(
        validation_alias="amount_paid", serialization_alias="amountPaid"
    )
    amount_due: str = Field(
        validation_alias="amount_due", serialization_alias="amountDue"
    )
    currency: str
    payment_terms: str | None = Field(
        default=None, validation_alias="payment_terms", serialization_alias="paymentTerms"
    )
    billing_reason: str | None = Field(
        default=None, validation_alias="billing_reason", serialization_alias="billingReason"
    )
    sent_at: datetime | None = Field(
        default=None, validation_alias="sent_at", serialization_alias="sentAt"
    )
    paid_at: datetime | None = Field(
        default=None, validation_alias="paid_at", serialization_alias="paidAt"
    )
    cancel_reason: str | None = Field(
        default=None, validation_alias="cancel_reason", serialization_alias="cancelReason"
    )
    notes: str | None = None
    created_at: datetime = Field(
        validation_alias="created_at", serialization_alias="createdAt"
    )


class InvoiceCancelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reason: str | None = Field(default=None, max_length=500)


class InvoiceLineCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID | None = Field(
        default=None, validation_alias="productId"
    )
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: str = Field(validation_alias="unitPrice")
    selected_variants: list[str] = Field(
        default_factory=list, validation_alias="selectedVariants"
    )
    tax_rate_percent: str = Field(default="0.00", validation_alias="taxRatePercent")
    tax_code: str | None = Field(default=None, validation_alias="taxCode")
    discount_amount: str = Field(default="0.00", validation_alias="discountAmount")


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: uuid.UUID = Field(validation_alias="customerId")
    subscription_id: uuid.UUID | None = Field(default=None, validation_alias="subscriptionId")
    quotation_id: uuid.UUID | None = Field(default=None, validation_alias="quotationId")
    issue_date: date | None = Field(default=None, validation_alias="issueDate")
    due_date: date | None = Field(default=None, validation_alias="dueDate")
    currency: str = "INR"
    payment_terms: str | None = Field(default=None, validation_alias="paymentTerms")
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(default_factory=list)
