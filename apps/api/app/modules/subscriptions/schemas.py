from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.subscription import SubscriptionStatus
from app.modules.quotation_templates.schemas import SubscriptionLineInput
from app.modules.quotations.schemas import InvoiceLine


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    customer_id: uuid.UUID = Field(validation_alias="customerId", serialization_alias="customerId")
    plan_id: uuid.UUID = Field(validation_alias="planId", serialization_alias="planId")
    quotation_id: uuid.UUID | None = Field(
        default=None, validation_alias="quotationId", serialization_alias="quotationId"
    )
    start_date: date = Field(validation_alias="startDate", serialization_alias="startDate")
    payment_terms: str | None = Field(
        default=None, max_length=500, validation_alias="paymentTerms", serialization_alias="paymentTerms"
    )
    lines: list[SubscriptionLineInput] = Field(min_length=1)


class SubscriptionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    payment_terms: str | None = Field(
        default=None, max_length=500, validation_alias="paymentTerms", serialization_alias="paymentTerms"
    )
    cancel_at_period_end: bool | None = Field(
        default=None, validation_alias="cancelAtPeriodEnd", serialization_alias="cancelAtPeriodEnd"
    )


class CancelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class PlanChangeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    new_plan_id: uuid.UUID = Field(validation_alias="newPlanId", serialization_alias="newPlanId")
    effective_at: datetime | None = Field(
        default=None, validation_alias="effectiveAt", serialization_alias="effectiveAt"
    )


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    number: str
    customer_id: uuid.UUID = Field(validation_alias="customer_id", serialization_alias="customerId")
    customer_name: str = Field(validation_alias="customer_name", serialization_alias="customerName")
    plan_id: uuid.UUID = Field(validation_alias="plan_id", serialization_alias="planId")
    plan_name: str = Field(validation_alias="plan_name", serialization_alias="planName")
    quotation_id: uuid.UUID | None = Field(
        default=None, validation_alias="quotation_id", serialization_alias="quotationId"
    )
    pending_plan_id: uuid.UUID | None = Field(
        default=None, validation_alias="pending_plan_id", serialization_alias="pendingPlanId"
    )
    status: SubscriptionStatus
    start_date: date = Field(validation_alias="start_date", serialization_alias="startDate")
    expiry_date: date = Field(validation_alias="expiry_date", serialization_alias="expiryDate")
    next_billing_date: date = Field(validation_alias="next_billing_date", serialization_alias="nextBillingDate")
    billing_interval: str = Field(validation_alias="billing_interval", serialization_alias="billingInterval")
    payment_terms: str | None = Field(
        default=None, validation_alias="payment_terms", serialization_alias="paymentTerms"
    )
    lines: list[InvoiceLine]
    recurring_subtotal: str = Field(validation_alias="recurring_subtotal", serialization_alias="recurringSubtotal")
    currency: str
    cancel_at_period_end: bool = Field(validation_alias="cancel_at_period_end", serialization_alias="cancelAtPeriodEnd")
    cancellation_requested_at: datetime | None = Field(
        default=None, validation_alias="cancellation_requested_at", serialization_alias="cancellationRequestedAt"
    )
    paused_at: datetime | None = Field(
        default=None, validation_alias="paused_at", serialization_alias="pausedAt"
    )
    created_at: datetime = Field(validation_alias="created_at", serialization_alias="createdAt")


class PlanChangeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscription: SubscriptionResponse
    adjustment_amount: str = Field(validation_alias="adjustmentAmount", serialization_alias="adjustmentAmount")
    currency: str
    effective_at: datetime = Field(validation_alias="effectiveAt", serialization_alias="effectiveAt")
    adjustment_type: str = Field(validation_alias="adjustmentType", serialization_alias="adjustmentType")
    invoice_id: uuid.UUID | None = Field(
        default=None, validation_alias="invoiceId", serialization_alias="invoiceId"
    )
    message: str


class SubscriptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    subscription_id: uuid.UUID = Field(validation_alias="subscription_id", serialization_alias="subscriptionId")
    event_type: str = Field(validation_alias="event_type", serialization_alias="eventType")
    actor_id: uuid.UUID | None = Field(default=None, validation_alias="actor_id", serialization_alias="actorId")
    actor_role: str | None = Field(default=None, validation_alias="actor_role", serialization_alias="actorRole")
    description: str
    event_data: dict[str, Any] | None = Field(default=None, validation_alias="event_data", serialization_alias="eventData")
    created_at: datetime = Field(validation_alias="created_at", serialization_alias="createdAt")
