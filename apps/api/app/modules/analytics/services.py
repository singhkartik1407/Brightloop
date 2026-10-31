from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.modules.analytics.schemas import (
    DashboardSummary,
    OverdueInvoiceItem,
    RenewalItem,
    RevenuePoint,
    RevenueSeriesResponse,
)
from app.modules.invoices.services import round_money


def get_dashboard_summary(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
    currency: str = "INR",
) -> DashboardSummary:
    curr = currency.upper().strip()
    today = date.today()

    # 1. Active subscriptions in currency
    active_subs_stmt = select(Subscription).where(
        Subscription.status == SubscriptionStatus.ACTIVE.value,
        Subscription.currency == curr,
    )
    active_subs = db.scalars(active_subs_stmt).all()
    active_subscriptions_count = len(active_subs)

    # 2. MRR and ARR
    mrr_accum = Decimal("0.00")
    for sub in active_subs:
        interval = sub.billing_interval.upper()
        count = Decimal(str(max(1, sub.interval_count)))
        sub_tot = Decimal(str(sub.recurring_subtotal))

        if interval == "MONTHLY":
            mrr_accum += sub_tot / count
        elif interval == "YEARLY":
            mrr_accum += sub_tot / (Decimal("12") * count)
        elif interval == "WEEKLY":
            mrr_accum += (sub_tot * Decimal("52")) / (Decimal("12") * count)
        elif interval == "DAILY":
            mrr_accum += (sub_tot * Decimal("365")) / (Decimal("12") * count)
        else:
            mrr_accum += sub_tot

    mrr = round_money(mrr_accum)
    arr = round_money(mrr * Decimal("12"))

    # 3. Revenue received
    pay_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == PaymentStatus.SUCCEEDED.value,
        Payment.currency == curr,
    )
    if from_date:
        start_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        pay_query = pay_query.where(Payment.paid_at >= start_dt)
    if to_date:
        end_dt = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        pay_query = pay_query.where(Payment.paid_at <= end_dt)

    revenue_received = round_money(Decimal(str(db.scalar(pay_query) or 0)))

    # 4. Outstanding amount
    out_query = select(func.coalesce(func.sum(Invoice.amount_due), 0)).where(
        Invoice.status.in_([
            InvoiceStatus.CONFIRMED.value,
            InvoiceStatus.PARTIALLY_PAID.value,
            InvoiceStatus.OVERDUE.value,
        ]),
        Invoice.currency == curr,
    )
    outstanding_amount = round_money(Decimal(str(db.scalar(out_query) or 0)))

    # 5. Overdue invoice count
    overdue_count_query = select(func.count(Invoice.id)).where(
        Invoice.due_date < today,
        Invoice.amount_due > 0,
        Invoice.status.notin_([InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value]),
        Invoice.currency == curr,
    )
    overdue_invoice_count = db.scalar(overdue_count_query) or 0

    # 6. Total invoices
    total_inv_query = select(func.count(Invoice.id)).where(Invoice.currency == curr)
    total_invoices = db.scalar(total_inv_query) or 0

    # 7. Upcoming renewals (next 30 days)
    renewal_window_end = today + timedelta(days=30)
    renewals_query = select(func.count(Subscription.id)).where(
        Subscription.status == SubscriptionStatus.ACTIVE.value,
        Subscription.currency == curr,
        Subscription.next_billing_date >= today,
        Subscription.next_billing_date <= renewal_window_end,
    )
    upcoming_renewals = db.scalar(renewals_query) or 0

    return DashboardSummary(
        active_subscriptions=active_subscriptions_count,
        revenue_received=f"{revenue_received:.2f}",
        outstanding_amount=f"{outstanding_amount:.2f}",
        overdue_invoice_count=overdue_invoice_count,
        mrr=f"{mrr:.2f}",
        arr=f"{arr:.2f}",
        total_invoices=total_invoices,
        upcoming_renewals=upcoming_renewals,
        currency=curr,
        as_of=datetime.now(timezone.utc),
    )


def get_revenue_series(
    db: Session,
    from_date: date,
    to_date: date,
    group_by: str = "MONTH",
    currency: str = "INR",
) -> RevenueSeriesResponse:
    curr = currency.upper().strip()
    start_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

    stmt = (
        select(Payment)
        .where(
            Payment.status == PaymentStatus.SUCCEEDED.value,
            Payment.currency == curr,
            Payment.paid_at >= start_dt,
            Payment.paid_at <= end_dt,
        )
        .order_by(Payment.paid_at.asc())
    )
    payments = db.scalars(stmt).all()

    buckets: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    group_upper = (group_by or "MONTH").upper()

    for p in payments:
        p_date = p.paid_at.date()
        if group_upper == "DAY":
            key = p_date.strftime("%Y-%m-%d")
        elif group_upper == "WEEK":
            iso_year, iso_week, _ = p_date.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        else:  # MONTH
            key = p_date.strftime("%Y-%m")

        buckets[key] += Decimal(str(p.amount))

    points = [
        RevenuePoint(period=k, amount=f"{round_money(v):.2f}")
        for k, v in sorted(buckets.items())
    ]

    return RevenueSeriesResponse(
        currency=curr,
        points=points,
    )


def get_upcoming_renewals_list(
    db: Session,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RenewalItem], int]:
    today = date.today()
    limit_date = today + timedelta(days=days)

    query = (
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.next_billing_date >= today,
            Subscription.next_billing_date <= limit_date,
        )
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    subs = (
        db.scalars(
            query.order_by(Subscription.next_billing_date.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [
        RenewalItem(
            subscription_id=sub.id,
            subscription_number=sub.subscription_number,
            customer_name=sub.customer.display_name if sub.customer else "Customer",
            renewal_date=sub.next_billing_date,
            expected_amount=f"{Decimal(str(sub.recurring_subtotal)):.2f}",
            currency=sub.currency,
        )
        for sub in subs
    ]

    return items, total


def get_overdue_invoices_list(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[OverdueInvoiceItem], int]:
    today = date.today()

    query = (
        select(Invoice)
        .where(
            Invoice.due_date < today,
            Invoice.amount_due > 0,
            Invoice.status.notin_([InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value]),
        )
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    invoices = (
        db.scalars(
            query.order_by(Invoice.due_date.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [
        OverdueInvoiceItem(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            customer_name=inv.customer.display_name if inv.customer else "Customer",
            due_date=inv.due_date,
            amount_due=f"{Decimal(str(inv.amount_due)):.2f}",
            currency=inv.currency,
            days_overdue=max(1, (today - inv.due_date).days),
        )
        for inv in invoices
    ]

    return items, total
