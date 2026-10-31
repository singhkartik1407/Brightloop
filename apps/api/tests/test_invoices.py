from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.plan import BillingInterval, Plan
from app.models.product import Product
from app.models.subscription import (
    PendingBillingAdjustment,
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
)
from app.modules.invoices.services import create_invoice_from_subscription


def test_manual_invoice_creation(client, role_users):
    customer = role_users["own_profile"]
    payload = {
        "customerId": str(customer.id),
        "currency": "INR",
        "paymentTerms": "NET_30",
        "notes": "Test service invoice",
        "lines": [
            {
                "description": "Consulting Services",
                "quantity": 2,
                "unitPrice": "5000.00",
                "discountAmount": "500.00",
                "taxRatePercent": "18.00",
                "taxCode": "GST18",
            },
            {
                "description": "Setup Fee",
                "quantity": 1,
                "unitPrice": "2000.00",
                "discountAmount": "0.00",
                "taxRatePercent": "0.00",
            },
        ],
    }

    res = client.post("/api/v1/invoices", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["number"].startswith("INV-")
    assert data["status"] == "DRAFT"
    assert data["customerId"] == str(customer.id)
    assert data["currency"] == "INR"
    assert len(data["lines"]) == 2

    # Line 1: sub = 10000, disc = 500, tax = (10000 - 500) * 18% = 1710.00, tot = 9500 + 1710 = 11210.00
    # Line 2: sub = 2000, disc = 0, tax = 0, tot = 2000.00
    # Totals: sub = 12000.00, disc = 500.00, tax = 1710.00, total = 13210.00
    assert data["subtotal"] == "12000.00"
    assert data["discountTotal"] == "500.00"
    assert data["taxTotal"] == "1710.00"
    assert data["total"] == "13210.00"
    assert data["amountPaid"] == "0.00"
    assert data["amountDue"] == "13210.00"


def test_invoice_sequential_numbering(client, role_users):
    customer = role_users["own_profile"]
    res1 = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Item 1", "quantity": 1, "unitPrice": "100.00"}],
        },
    )
    res2 = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Item 2", "quantity": 1, "unitPrice": "200.00"}],
        },
    )
    assert res1.status_code == 201
    assert res2.status_code == 201

    num1 = res1.json()["number"]
    num2 = res2.json()["number"]

    seq1 = int(num1.split("-")[-1])
    seq2 = int(num2.split("-")[-1])
    assert seq2 == seq1 + 1


def test_invoice_confirm_lifecycle(client, role_users):
    customer = role_users["own_profile"]
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Item", "quantity": 1, "unitPrice": "500.00"}],
        },
    )
    inv_id = res.json()["id"]

    # Confirm
    conf_res = client.post(f"/api/v1/invoices/{inv_id}/confirm")
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "CONFIRMED"

    # Confirm again raises 409
    dup_res = client.post(f"/api/v1/invoices/{inv_id}/confirm")
    assert dup_res.status_code == 409


def test_invoice_cancel_lifecycle(client, role_users):
    customer = role_users["own_profile"]
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Item", "quantity": 1, "unitPrice": "500.00"}],
        },
    )
    inv_id = res.json()["id"]

    cancel_res = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        json={"reason": "Customer changed mind"},
    )
    assert cancel_res.status_code == 200
    body = cancel_res.json()
    assert body["status"] == "CANCELLED"
    assert body["cancelReason"] == "Customer changed mind"


def test_invoice_send_endpoint(client, role_users):
    customer = role_users["own_profile"]
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Item", "quantity": 1, "unitPrice": "500.00"}],
        },
    )
    inv_id = res.json()["id"]

    send_res = client.post(f"/api/v1/invoices/{inv_id}/send")
    assert send_res.status_code == 202
    assert send_res.json()["message"] == "Invoice delivery queued."

    # Verify sentAt is populated
    detail_res = client.get(f"/api/v1/invoices/{inv_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["sentAt"] is not None


def test_invoice_pdf_download(client, role_users):
    customer = role_users["own_profile"]
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "lines": [{"description": "Design System", "quantity": 1, "unitPrice": "1500.00"}],
        },
    )
    inv_id = res.json()["id"]

    pdf_res = client.get(f"/api/v1/invoices/{inv_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-1.4")
    assert b"BRIGHTLOOP SUBSCRIPTION MANAGEMENT" in pdf_res.content
    assert b"Design System" in pdf_res.content


def test_invoice_customer_isolation(client, role_users, auth_as):
    own_customer = role_users["own_profile"]
    other_customer = role_users["other_profile"]

    # Admin creates invoice for other_customer
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(other_customer.id),
            "lines": [{"description": "Confidential Line", "quantity": 1, "unitPrice": "999.00"}],
        },
    )
    other_inv_id = res.json()["id"]

    # Log in as own_customer
    auth_as(role_users["customer"])

    # Attempt to view other_customer's invoice -> 404
    forbidden_get = client.get(f"/api/v1/invoices/{other_inv_id}")
    assert forbidden_get.status_code == 404

    # List invoices for own customer -> does not contain other customer's invoice
    list_res = client.get("/api/v1/invoices")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert not any(item["id"] == other_inv_id for item in items)


def test_overdue_invoice_dynamic_status(client, role_users, db_session):
    customer = role_users["own_profile"]
    past_due = date.today() - timedelta(days=5)

    inv = Invoice(
        invoice_number="INV-2026-9999",
        customer_id=customer.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=past_due - timedelta(days=30),
        due_date=past_due,
        currency="INR",
        subtotal=Decimal("1000.00"),
        tax_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("1000.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("1000.00"),
    )
    db_session.add(inv)
    db_session.commit()

    # Detail view dynamically reflects OVERDUE
    res = client.get(f"/api/v1/invoices/{inv.id}")
    assert res.status_code == 200
    assert res.json()["status"] == "OVERDUE"

    # Filter overdueOnly=true
    overdue_res = client.get("/api/v1/invoices", params={"overdueOnly": True})
    assert overdue_res.status_code == 200
    item_ids = [item["id"] for item in overdue_res.json()["items"]]
    assert str(inv.id) in item_ids


def test_create_invoice_from_subscription_and_idempotency(db_session, role_users):
    customer = role_users["own_profile"]
    product = Product(
        name="API Gateway",
        type="SOFTWARE",
        sales_price=Decimal("250.00"),
        cost_price=Decimal("50.00"),
        currency="INR",
    )
    plan = Plan(
        name="Developer Monthly",
        billing_interval=BillingInterval.MONTHLY.value,
        interval_count=1,
        price=Decimal("100.00"),
        currency="INR",
    )
    db_session.add_all([product, plan])
    db_session.flush()

    sub = Subscription(
        subscription_number="SUB-2026-0001",
        customer_id=customer.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=date(2026, 1, 1),
        expiry_date=date(2026, 2, 1),
        next_billing_date=date(2026, 2, 1),
        current_period_start=date(2026, 1, 1),
        current_period_end=date(2026, 2, 1),
        billing_interval=BillingInterval.MONTHLY.value,
        interval_count=1,
        recurring_subtotal=Decimal("350.00"),
        currency="INR",
    )
    db_session.add(sub)
    db_session.flush()

    line1 = SubscriptionLine(
        subscription_id=sub.id,
        product_id=None,
        description="Plan: Developer Monthly",
        quantity=1,
        unit_price=Decimal("100.00"),
        line_subtotal=Decimal("100.00"),
        tax_amount=Decimal("18.00"),
        discount_amount=Decimal("0.00"),
        line_total=Decimal("118.00"),
        taxes_data=[{"name": "GST", "code": "GST18", "ratePercent": "18.00", "amount": "18.00"}],
    )
    line2 = SubscriptionLine(
        subscription_id=sub.id,
        product_id=product.id,
        description="API Gateway Add-on",
        quantity=1,
        unit_price=Decimal("250.00"),
        line_subtotal=Decimal("250.00"),
        tax_amount=Decimal("0.00"),
        discount_amount=Decimal("25.00"),
        line_total=Decimal("225.00"),
    )
    db_session.add_all([line1, line2])
    db_session.commit()

    # Generate invoice for cycle
    inv1 = create_invoice_from_subscription(
        db=db_session,
        subscription=sub,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
    )
    db_session.commit()

    assert inv1.subscription_id == sub.id
    assert inv1.status == InvoiceStatus.CONFIRMED.value
    assert len(inv1.lines) == 2
    assert inv1.total == Decimal("343.00")  # 118.00 + 225.00
    assert inv1.amount_due == Decimal("343.00")

    # Idempotency: calling again for same cycle returns the same invoice without creating a duplicate
    inv2 = create_invoice_from_subscription(
        db=db_session,
        subscription=sub,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
    )
    assert inv2.id == inv1.id
    assert inv2.invoice_number == inv1.invoice_number


def test_subscription_renewal_creates_recurring_invoice(client, role_users, db_session):
    customer = role_users["own_profile"]
    plan = Plan(
        name="Auto Renew Base",
        billing_interval="MONTHLY",
        interval_count=1,
        price=Decimal("150.00"),
        currency="INR",
        allow_renewal=True,
    )
    db_session.add(plan)
    db_session.flush()

    sub = Subscription(
        subscription_number="SUB-2026-9090",
        customer_id=customer.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=date(2026, 1, 1),
        expiry_date=date(2026, 2, 1),
        next_billing_date=date(2026, 2, 1),
        current_period_start=date(2026, 1, 1),
        current_period_end=date(2026, 2, 1),
        billing_interval="MONTHLY",
        interval_count=1,
        recurring_subtotal=Decimal("150.00"),
        currency="INR",
    )
    db_session.add(sub)
    db_session.commit()

    # Trigger renewal via endpoint
    res = client.post(f"/api/v1/subscriptions/{sub.id}/renew")
    assert res.status_code == 200

    # Verify recurring invoice created for the renewed cycle (2026-02-01 to 2026-03-01)
    renewed_inv = (
        db_session.query(Invoice)
        .filter(
            Invoice.subscription_id == sub.id,
            Invoice.period_start == date(2026, 2, 1),
            Invoice.period_end == date(2026, 3, 1),
        )
        .first()
    )
    assert renewed_inv is not None
    assert renewed_inv.status == InvoiceStatus.CONFIRMED.value
    assert renewed_inv.billing_reason == "SUBSCRIPTION_RENEWAL"


def test_plan_upgrade_creates_invoice_and_guards_duplicate_generation(client, role_users, db_session):
    customer = role_users["own_profile"]
    plan_basic = Plan(
        name="Tier Basic",
        billing_interval="MONTHLY",
        interval_count=1,
        price=Decimal("100.00"),
        currency="INR",
    )
    plan_pro = Plan(
        name="Tier Pro",
        billing_interval="MONTHLY",
        interval_count=1,
        price=Decimal("300.00"),
        currency="INR",
    )
    db_session.add_all([plan_basic, plan_pro])
    db_session.flush()

    sub = Subscription(
        subscription_number="SUB-2026-9091",
        customer_id=customer.id,
        plan_id=plan_basic.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=date(2026, 1, 1),
        expiry_date=date(2026, 2, 1),
        next_billing_date=date(2026, 2, 1),
        current_period_start=date(2026, 1, 1),
        current_period_end=date(2026, 2, 1),
        billing_interval="MONTHLY",
        interval_count=1,
        recurring_subtotal=Decimal("100.00"),
        currency="INR",
    )
    db_session.add(sub)
    db_session.commit()

    # Change plan to Tier Pro (Upgrade: diff = 200.00)
    res = client.post(
        f"/api/v1/subscriptions/{sub.id}/change-plan",
        json={"newPlanId": str(plan_pro.id)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["adjustmentType"] == "IMMEDIATE_UPGRADE_DIFFERENCE"
    assert data["adjustmentAmount"] == "200.00"
    assert data["invoiceId"] is not None

    inv_id = data["invoiceId"]
    upgrade_inv = db_session.get(Invoice, uuid.UUID(inv_id))
    assert upgrade_inv is not None
    assert upgrade_inv.total == Decimal("200.00")
    assert upgrade_inv.billing_reason == "PLAN_UPGRADE"

    # Verify pending billing adjustment is marked billed
    adj = (
        db_session.query(PendingBillingAdjustment)
        .filter(PendingBillingAdjustment.subscription_id == sub.id)
        .first()
    )
    assert adj is not None
    assert adj.is_billed is True
    assert str(adj.invoice_id) == inv_id

    # Duplicate guard: calling create_invoice_for_upgrade_adjustment again returns existing invoice
    from app.modules.invoices.services import create_invoice_for_upgrade_adjustment
    dup_inv = create_invoice_for_upgrade_adjustment(db_session, sub, adj)
    assert dup_inv.id == upgrade_inv.id
