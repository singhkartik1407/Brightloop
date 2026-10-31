from __future__ import annotations

import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    active_subscriptions: int = Field(
        validation_alias="active_subscriptions", serialization_alias="activeSubscriptions"
    )
    revenue_received: str = Field(
        validation_alias="revenue_received", serialization_alias="revenueReceived"
    )
    outstanding_amount: str = Field(
        validation_alias="outstanding_amount", serialization_alias="outstandingAmount"
    )
    overdue_invoice_count: int = Field(
        validation_alias="overdue_invoice_count", serialization_alias="overdueInvoiceCount"
    )
    mrr: str
    arr: str
    total_invoices: int = Field(
        validation_alias="total_invoices", serialization_alias="totalInvoices"
    )
    upcoming_renewals: int = Field(
        validation_alias="upcoming_renewals", serialization_alias="upcomingRenewals"
    )
    currency: str
    as_of: datetime = Field(
        validation_alias="as_of", serialization_alias="asOf"
    )


class RevenuePoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    period: str
    amount: str


class RevenueSeriesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    currency: str
    points: list[RevenuePoint]


class RenewalItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscription_id: uuid.UUID = Field(
        validation_alias="subscription_id", serialization_alias="subscriptionId"
    )
    subscription_number: str = Field(
        validation_alias="subscription_number", serialization_alias="subscriptionNumber"
    )
    customer_name: str = Field(
        validation_alias="customer_name", serialization_alias="customerName"
    )
    renewal_date: date = Field(
        validation_alias="renewal_date", serialization_alias="renewalDate"
    )
    expected_amount: str = Field(
        validation_alias="expected_amount", serialization_alias="expectedAmount"
    )
    currency: str


class OverdueInvoiceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    invoice_id: uuid.UUID = Field(
        validation_alias="invoice_id", serialization_alias="invoiceId"
    )
    invoice_number: str = Field(
        validation_alias="invoice_number", serialization_alias="invoiceNumber"
    )
    customer_name: str = Field(
        validation_alias="customer_name", serialization_alias="customerName"
    )
    due_date: date = Field(
        validation_alias="due_date", serialization_alias="dueDate"
    )
    amount_due: str = Field(
        validation_alias="amount_due", serialization_alias="amountDue"
    )
    currency: str
    days_overdue: int = Field(
        validation_alias="days_overdue", serialization_alias="daysOverdue"
    )
