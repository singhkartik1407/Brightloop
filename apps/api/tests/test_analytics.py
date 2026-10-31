from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.plan import BillingInterval, Plan
from app.models.subscription import Subscription, SubscriptionStatus


def test_analytics_summary_calculation(client, role_users, db_session):
    customer = role_users["own_profile"]
    today = date.today()

    # 1. Active monthly plan subscription: 3000.00/month
    plan_m = Plan(
        name="Monthly Pro",
        billing_interval=BillingInterval.MONTHLY.value,
        interval_count=1,
        price=Decimal("3000.00"),
        currency="INR",
    )
    # 2. Active yearly plan subscription: 12000.00/year -> 1000.00/month
    plan_y = Plan(
        name="Enterprise Annual",
        billing_interval=BillingInterval.YEARLY.value,
        interval_count=1,
        price=Decimal("12000.00"),
        currency="INR",
    )
    db_session.add_all([plan_m, plan_y])
    db_session.flush()

    sub1 = Subscription(
        subscription_number="SUB-2026-0101",
        customer_id=customer.id,
        plan_id=plan_m.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=today - timedelta(days=10),
        expiry_date=today + timedelta(days=20),
        next_billing_date=today + timedelta(days=20),
        current_period_start=today - timedelta(days=10),
        current_period_end=today + timedelta(days=20),
        billing_interval=BillingInterval.MONTHLY.value,
        interval_count=1,
        recurring_subtotal=Decimal("3000.00"),
        currency="INR",
    )
    sub2 = Subscription(
        subscription_number="SUB-2026-0102",
        customer_id=customer.id,
        plan_id=plan_y.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=today - timedelta(days=60),
        expiry_date=today + timedelta(days=305),
        next_billing_date=today + timedelta(days=305),
        current_period_start=today - timedelta(days=60),
        current_period_end=today + timedelta(days=305),
        billing_interval=BillingInterval.YEARLY.value,
        interval_count=1,
        recurring_subtotal=Decimal("12000.00"),
        currency="INR",
    )
    db_session.add_all([sub1, sub2])

    # 3. Invoices: one confirmed with balance 1500, one overdue with balance 500
    inv1 = Invoice(
        invoice_number="INV-2026-1001",
        customer_id=customer.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today,
        due_date=today + timedelta(days=30),
        currency="INR",
        subtotal=Decimal("1500.00"),
        total=Decimal("1500.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("1500.00"),
    )
    inv_overdue = Invoice(
        invoice_number="INV-2026-1002",
        customer_id=customer.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
        currency="INR",
        subtotal=Decimal("500.00"),
        total=Decimal("500.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("500.00"),
    )
    db_session.add_all([inv1, inv_overdue])
    db_session.flush()

    # 4. Payment received: 2500.00
    pay = Payment(
        payment_reference="PAY-2026-1001",
        invoice_id=inv1.id,
        customer_id=customer.id,
        method="UPI",
        amount=Decimal("2500.00"),
        currency="INR",
        status=PaymentStatus.SUCCEEDED.value,
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(pay)
    db_session.commit()

    # Query summary
    res = client.get("/api/v1/analytics/summary", params={"currency": "INR"})
    assert res.status_code == 200
    data = res.json()

    assert data["activeSubscriptions"] == 2
    # MRR = 3000 (from monthly) + 1000 (from yearly 12000/12) = 4000.00
    assert data["mrr"] == "4000.00"
    assert data["arr"] == "48000.00"
    assert data["revenueReceived"] == "2500.00"
    assert data["outstandingAmount"] == "2000.00"  # 1500 + 500
    assert data["overdueInvoiceCount"] == 1
    assert data["upcomingRenewals"] == 1  # sub1 has renewal in 20 days (<= 30)
    assert data["currency"] == "INR"
    assert data["asOf"] is not None


def test_revenue_series_groupings(client, role_users, db_session):
    customer = role_users["own_profile"]
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    inv = Invoice(
        invoice_number="INV-2026-2001",
        customer_id=customer.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=date(2026, 10, 1),
        due_date=date(2026, 10, 30),
        currency="INR",
        subtotal=Decimal("1000.00"),
        total=Decimal("1000.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("1000.00"),
    )
    db_session.add(inv)
    db_session.flush()

    p1 = Payment(
        payment_reference="PAY-2026-2001",
        invoice_id=inv.id,
        customer_id=customer.id,
        method="CARD",
        amount=Decimal("400.00"),
        currency="INR",
        status=PaymentStatus.SUCCEEDED.value,
        paid_at=datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    p2 = Payment(
        payment_reference="PAY-2026-2002",
        invoice_id=inv.id,
        customer_id=customer.id,
        method="CARD",
        amount=Decimal("600.00"),
        currency="INR",
        status=PaymentStatus.SUCCEEDED.value,
        paid_at=datetime(2026, 10, 15, 14, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    # 1. Group by MONTH
    res_m = client.get(
        "/api/v1/analytics/revenue",
        params={"from": "2026-10-01", "to": "2026-10-31", "groupBy": "MONTH"},
    )
    assert res_m.status_code == 200
    points_m = res_m.json()["points"]
    assert len(points_m) == 1
    assert points_m[0]["period"] == "2026-10"
    assert points_m[0]["amount"] == "1000.00"

    # 2. Group by DAY
    res_d = client.get(
        "/api/v1/analytics/revenue",
        params={"from": "2026-10-01", "to": "2026-10-31", "groupBy": "DAY"},
    )
    assert res_d.status_code == 200
    points_d = res_d.json()["points"]
    assert len(points_d) == 2
    assert points_d[0]["period"] == "2026-10-10"
    assert points_d[0]["amount"] == "400.00"
    assert points_d[1]["period"] == "2026-10-15"
    assert points_d[1]["amount"] == "600.00"


def test_upcoming_renewals_and_overdue_endpoints(client, role_users, db_session):
    customer = role_users["own_profile"]
    today = date.today()

    plan = Plan(
        name="Standard",
        billing_interval="MONTHLY",
        interval_count=1,
        price=Decimal("500.00"),
        currency="INR",
    )
    db_session.add(plan)
    db_session.flush()

    sub = Subscription(
        subscription_number="SUB-2026-3001",
        customer_id=customer.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=today - timedelta(days=15),
        expiry_date=today + timedelta(days=15),
        next_billing_date=today + timedelta(days=15),
        current_period_start=today - timedelta(days=15),
        current_period_end=today + timedelta(days=15),
        billing_interval="MONTHLY",
        interval_count=1,
        recurring_subtotal=Decimal("500.00"),
        currency="INR",
    )
    inv_overdue = Invoice(
        invoice_number="INV-2026-3001",
        customer_id=customer.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today - timedelta(days=45),
        due_date=today - timedelta(days=15),
        currency="INR",
        subtotal=Decimal("750.00"),
        total=Decimal("750.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("750.00"),
    )
    db_session.add_all([sub, inv_overdue])
    db_session.commit()

    # Renewals list
    res_ren = client.get("/api/v1/analytics/renewals", params={"days": 30})
    assert res_ren.status_code == 200
    items_ren = res_ren.json()["items"]
    assert any(item["subscriptionNumber"] == "SUB-2026-3001" for item in items_ren)

    # Overdue list
    res_od = client.get("/api/v1/analytics/overdue")
    assert res_od.status_code == 200
    items_od = res_od.json()["items"]
    assert any(item["invoiceNumber"] == "INV-2026-3001" and item["daysOverdue"] == 15 for item in items_od)


def test_analytics_forbidden_for_customer(client, role_users, auth_as):
    # Customer user should be rejected with 403 Forbidden
    auth_as(role_users["customer"])
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN"
