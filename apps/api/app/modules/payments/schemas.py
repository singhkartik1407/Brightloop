from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    invoice_id: uuid.UUID = Field(validation_alias="invoiceId")
    method: PaymentMethod
    amount: str
    currency: str
    paid_at: datetime = Field(validation_alias="paidAt")
    note: str | None = Field(default=None, max_length=500)
    reference: str | None = Field(default=None, max_length=120)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    reference: str | None = None
    payment_reference: str = Field(
        validation_alias="payment_reference", serialization_alias="paymentReference"
    )
    invoice_id: uuid.UUID = Field(
        validation_alias="invoice_id", serialization_alias="invoiceId"
    )
    invoice_number: str | None = Field(
        default=None, validation_alias="invoice_number", serialization_alias="invoiceNumber"
    )
    customer_id: uuid.UUID = Field(
        validation_alias="customer_id", serialization_alias="customerId"
    )
    customer_name: str | None = Field(
        default=None, validation_alias="customer_name", serialization_alias="customerName"
    )
    method: PaymentMethod
    amount: str
    currency: str
    status: PaymentStatus
    paid_at: datetime = Field(
        validation_alias="paid_at", serialization_alias="paidAt"
    )
    note: str | None = None
    created_at: datetime = Field(
        validation_alias="created_at", serialization_alias="createdAt"
    )


class GatewayIntent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    provider_intent_id: str = Field(
        validation_alias="provider_intent_id", serialization_alias="providerIntentId"
    )
    checkout_url: str = Field(
        validation_alias="checkout_url", serialization_alias="checkoutUrl"
    )
    status: str
