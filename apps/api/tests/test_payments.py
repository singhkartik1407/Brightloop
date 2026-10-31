from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus


def create_test_invoice(client, customer_id: str, amount: str = "1000.00", currency: str = "INR") -> dict:
    res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": customer_id,
            "currency": currency,
            "lines": [{"description": "Service Package", "quantity": 1, "unitPrice": amount}],
        },
    )
    assert res.status_code == 201
    inv_data = res.json()

    # Confirm it so payments can be accepted
    conf = client.post(f"/api/v1/invoices/{inv_data['id']}/confirm")
    assert conf.status_code == 200
    return conf.json()


def test_record_payment_partial_and_full_settlement(client, role_users):
    customer = role_users["own_profile"]
    inv = create_test_invoice(client, str(customer.id), amount="1000.00")
    inv_id = inv["id"]

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Partial payment: 400.00
    res1 = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": inv_id,
            "method": "UPI",
            "amount": "400.00",
            "currency": "INR",
            "paidAt": now_iso,
            "note": "Initial advance payment via UPI",
            "reference": "UPI-REF-001",
        },
    )
    assert res1.status_code == 201
    pay1 = res1.json()
    assert pay1["paymentReference"].startswith("PAY-")
    assert pay1["amount"] == "400.00"
    assert pay1["method"] == "UPI"
    assert pay1["status"] == "SUCCEEDED"

    # Check invoice status updated to PARTIALLY_PAID
    inv_res1 = client.get(f"/api/v1/invoices/{inv_id}")
    assert inv_res1.status_code == 200
    body1 = inv_res1.json()
    assert body1["status"] == "PARTIALLY_PAID"
    assert body1["amountPaid"] == "400.00"
    assert body1["amountDue"] == "600.00"

    # 2. Final payment: 600.00
    res2 = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": inv_id,
            "method": "BANK_TRANSFER",
            "amount": "600.00",
            "currency": "INR",
            "paidAt": now_iso,
            "reference": "NEFT-998877",
        },
    )
    assert res2.status_code == 201
    pay2 = res2.json()
    assert pay2["amount"] == "600.00"

    # Check invoice status updated to PAID
    inv_res2 = client.get(f"/api/v1/invoices/{inv_id}")
    assert inv_res2.status_code == 200
    body2 = inv_res2.json()
    assert body2["status"] == "PAID"
    assert body2["amountPaid"] == "1000.00"
    assert body2["amountDue"] == "0.00"
    assert body2["paidAt"] is not None


def test_payment_overpayment_rejected(client, role_users):
    customer = role_users["own_profile"]
    inv = create_test_invoice(client, str(customer.id), amount="500.00")
    inv_id = inv["id"]

    now_iso = datetime.now(timezone.utc).isoformat()

    # Try to pay 600.00 against 500.00
    res = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": inv_id,
            "method": "CARD",
            "amount": "600.00",
            "currency": "INR",
            "paidAt": now_iso,
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "OVERPAYMENT_NOT_ALLOWED"


def test_payment_currency_mismatch_rejected(client, role_users):
    customer = role_users["own_profile"]
    inv = create_test_invoice(client, str(customer.id), amount="500.00", currency="INR")
    inv_id = inv["id"]

    now_iso = datetime.now(timezone.utc).isoformat()

    res = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": inv_id,
            "method": "CARD",
            "amount": "500.00",
            "currency": "USD",
            "paidAt": now_iso,
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "CURRENCY_MISMATCH"


def test_payment_idempotency(client, role_users):
    customer = role_users["own_profile"]
    inv = create_test_invoice(client, str(customer.id), amount="1000.00")
    inv_id = inv["id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    idemp_key = f"test-idemp-{uuid.uuid4()}"

    payload = {
        "invoiceId": inv_id,
        "method": "UPI",
        "amount": "300.00",
        "currency": "INR",
        "paidAt": now_iso,
    }

    # First call
    res1 = client.post("/api/v1/payments", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 201
    pay1 = res1.json()

    # Second call with same idempotency key
    res2 = client.post("/api/v1/payments", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 201
    pay2 = res2.json()

    assert pay1["id"] == pay2["id"]
    assert pay1["paymentReference"] == pay2["paymentReference"]

    # Verify balance was only deducted ONCE
    inv_res = client.get(f"/api/v1/invoices/{inv_id}")
    assert inv_res.json()["amountPaid"] == "300.00"
    assert inv_res.json()["amountDue"] == "700.00"


def test_payment_rejected_on_draft_or_cancelled_invoice(client, role_users):
    customer = role_users["own_profile"]

    # 1. Draft invoice
    draft_res = client.post(
        "/api/v1/invoices",
        json={
            "customerId": str(customer.id),
            "currency": "INR",
            "lines": [{"description": "Draft Line", "quantity": 1, "unitPrice": "200.00"}],
        },
    )
    draft_id = draft_res.json()["id"]

    pay_res1 = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": draft_id,
            "method": "CASH",
            "amount": "200.00",
            "currency": "INR",
            "paidAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert pay_res1.status_code == 409
    assert pay_res1.json()["detail"]["code"] == "INVOICE_NOT_CONFIRMED"

    # 2. Cancelled invoice
    client.post(f"/api/v1/invoices/{draft_id}/cancel")
    pay_res2 = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": draft_id,
            "method": "CASH",
            "amount": "200.00",
            "currency": "INR",
            "paidAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert pay_res2.status_code == 409
    assert pay_res2.json()["detail"]["code"] == "INVOICE_CANCELLED"


def test_cannot_cancel_invoice_with_recorded_payments(client, role_users):
    customer = role_users["own_profile"]
    inv = create_test_invoice(client, str(customer.id), amount="800.00")
    inv_id = inv["id"]

    client.post(
        "/api/v1/payments",
        json={
            "invoiceId": inv_id,
            "method": "CASH",
            "amount": "100.00",
            "currency": "INR",
            "paidAt": datetime.now(timezone.utc).isoformat(),
        },
    )

    cancel_res = client.post(f"/api/v1/invoices/{inv_id}/cancel")
    assert cancel_res.status_code == 409
    assert cancel_res.json()["detail"]["code"] == "CANNOT_CANCEL_PAID_INVOICE"


def test_payment_customer_isolation(client, role_users, auth_as):
    own_customer = role_users["own_profile"]
    other_customer = role_users["other_profile"]

    # Invoice for other customer
    other_inv = create_test_invoice(client, str(other_customer.id), amount="500.00")
    other_inv_id = other_inv["id"]

    # Payment for other customer by Admin
    pay_res = client.post(
        "/api/v1/payments",
        json={
            "invoiceId": other_inv_id,
            "method": "BANK_TRANSFER",
            "amount": "500.00",
            "currency": "INR",
            "paidAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    other_pay_id = pay_res.json()["id"]

    # Switch to customer
    auth_as(role_users["customer"])

    # Cannot view other's payment detail -> 404
    assert client.get(f"/api/v1/payments/{other_pay_id}").status_code == 404

    # List payments -> does not contain other's payment
    list_res = client.get("/api/v1/payments")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert not any(item["id"] == other_pay_id for item in items)


def test_gateway_and_webhook_endpoints(client):
    # Gateway intents returns 501
    gw_res = client.post(
        "/api/v1/payments/gateway-intents",
        json={"invoiceId": str(uuid.uuid4())},
    )
    assert gw_res.status_code == 501
    assert gw_res.json()["detail"]["code"] == "GATEWAY_NOT_CONFIGURED"

    # Webhook endpoint returns 501 when unconfigured
    hook_res = client.post(
        "/api/v1/payments/webhooks/stripe",
        json={"event": "payment_intent.succeeded", "id": "evt_123"},
    )
    assert hook_res.status_code == 501
    assert hook_res.json()["detail"]["code"] == "GATEWAY_PROVIDER_NOT_CONFIGURED"
