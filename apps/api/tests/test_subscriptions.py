import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.quotation import Quotation, QuotationStatus
from app.models.subscription import (
    PendingBillingAdjustment,
    Subscription,
    SubscriptionCounter,
    SubscriptionEvent,
    SubscriptionRenewalRecord,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.modules.subscriptions.billing import (
    calculate_next_billing_date,
    calculate_normalized_monthly_value,
)


@pytest.fixture(autouse=True)
def default_seller_state(monkeypatch):
    monkeypatch.setattr(settings, "ORGANIZATION_STATE", "Maharashtra")


def setup_customer(
    db_session,
    name="Acme Corp",
    email="billing@acme.com",
    state="Maharashtra",
    user_id=None,
):
    cust = Customer(
        display_name=name,
        billing_email=email,
        billing_state=state,
        billing_country_code="IN",
        user_id=user_id,
        is_active=True,
    )
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)
    return cust


def setup_product_and_variants(
    db_session, name="Cloud Server", base_price="100.00"
):
    prod = Product(
        name=name,
        type="SOFTWARE",
        sales_price=base_price,
        cost_price="40.00",
        currency="INR",
        is_active=True,
    )
    v1 = ProductVariant(
        attribute_name="RAM",
        attribute_value="16GB",
        price_adjustment="20.00",
        is_active=True,
    )
    prod.variants.append(v1)
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod, v1


def setup_plan(
    db_session,
    name="Standard Plan",
    price="50.00",
    interval="MONTHLY",
    interval_count=1,
    min_quantity=1,
    from_date=None,
    until_date=None,
    allow_pause=True,
    allow_early_close=True,
    allow_renewal=True,
    auto_close_at_end=False,
    currency="INR",
):
    plan = Plan(
        name=name,
        price=price,
        currency=currency,
        billing_interval=interval,
        interval_count=interval_count,
        min_quantity=min_quantity,
        available_from=from_date,
        available_until=until_date,
        allow_pause=allow_pause,
        allow_early_close=allow_early_close,
        allow_renewal=allow_renewal,
        auto_close_at_end=auto_close_at_end,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


# ==============================================================================
# 1. SUBSCRIPTION CREATION & QUOTATION CONVERSION
# ==============================================================================


def test_direct_subscription_creation_success(client: TestClient, db_session):
    cust = setup_customer(db_session, "Direct Cust", "direct@test.com")
    prod, v1 = setup_product_and_variants(db_session, "Direct Prod", "150.00")
    plan = setup_plan(db_session, "Direct Plan", "75.00")

    payload = {
        "customerId": str(cust.id),
        "planId": str(plan.id),
        "startDate": "2026-11-01",
        "paymentTerms": "Immediate",
        "lines": [
            {
                "productId": str(prod.id),
                "quantity": 2,
                "selectedVariantIds": [str(v1.id)],
                "taxRuleIds": [],
            }
        ],
    }

    res = client.post("/api/v1/subscriptions", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["status"] == "CONFIRMED"
    assert data["customerId"] == str(cust.id)
    assert data["planId"] == str(plan.id)
    assert data["number"].startswith(f"SUB-{date.today().year}-")
    assert data["startDate"] == "2026-11-01"
    assert data["expiryDate"] == "2026-12-01"
    assert data["nextBillingDate"] == "2026-12-01"
    assert len(data["lines"]) == 2

    # Line 0 is Plan recurring fee, Line 1 is the product line
    line = data["lines"][1]
    # Unit price = 150.00 + 20.00 (variant) = 170.00; lineSubtotal = 170.00 * 2 = 340.00
    assert line["unitPrice"] == "170.00"
    assert line["lineSubtotal"] == "340.00"
    assert line["lineTotal"] == "340.00"

    # Recurring subtotal is the total recurring commitment pre-tax (75.00 plan + 340.00 product)
    assert data["recurringSubtotal"] == "415.00"


def test_subscription_creation_from_quotation_acceptance(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]
    prod, v1 = setup_product_and_variants(db_session, "Quote Prod", "100.00")
    plan = setup_plan(db_session, "Quote Plan", "60.00")

    # Staff creates quotation
    auth_as(role_users["staff"])
    res_q = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-15",
            "paymentTerms": "Net 15",
            "lines": [
                {
                    "productId": str(prod.id),
                    "quantity": 1,
                    "selectedVariantIds": [str(v1.id)],
                    "taxRuleIds": [],
                }
            ],
        },
    )
    assert res_q.status_code == 201
    q_id = res_q.json()["id"]

    # Customer accepts quotation
    auth_as(cust_user)
    res_accept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_accept.status_code == 200
    q_data = res_accept.json()
    assert q_data["status"] == "CONFIRMED"
    assert q_data["subscriptionId"] is not None

    sub_id = q_data["subscriptionId"]
    res_sub = client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res_sub.status_code == 200
    sub_data = res_sub.json()

    assert sub_data["status"] == "CONFIRMED"
    assert sub_data["quotationId"] == q_id
    assert sub_data["customerId"] == str(cust.id)
    assert sub_data["planId"] == str(plan.id)
    assert sub_data["startDate"] == "2026-11-15"
    assert sub_data["expiryDate"] == "2026-12-15"


def test_explicit_conversion_endpoint_and_duplicate_prevention(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]
    prod, _ = setup_product_and_variants(db_session, "Explicit Prod", "80.00")
    plan = setup_plan(db_session, "Explicit Plan", "40.00")

    # Staff creates quotation
    auth_as(role_users["staff"])
    res_q = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    q_id = res_q.json()["id"]

    # Customer accepts quotation (which automatically creates subscription)
    auth_as(cust_user)
    res_accept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_accept.status_code == 200
    initial_sub_id = res_accept.json()["subscriptionId"]

    # Staff explicitly calls from-quotation endpoint on same quotation -> idempotent
    auth_as(role_users["staff"])
    res_from_q = client.post(f"/api/v1/subscriptions/from-quotation/{q_id}")
    assert res_from_q.status_code == 201
    assert res_from_q.json()["id"] == initial_sub_id


def test_quotation_conversion_rejected_for_unconfirmed(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust = role_users["own_profile"]
    prod, _ = setup_product_and_variants(db_session, "Draft Prod", "50.00")
    plan = setup_plan(db_session, "Draft Plan", "30.00")

    auth_as(role_users["staff"])
    res_q = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    q_id = res_q.json()["id"]

    # Quotation is still DRAFT
    res_conv = client.post(f"/api/v1/subscriptions/from-quotation/{q_id}")
    assert res_conv.status_code == 409
    assert "CONFIRMED" in res_conv.json()["detail"]["message"]


def test_plan_availability_constraints_on_subscription(
    client: TestClient, db_session
):
    cust = setup_customer(db_session, "Avail Cust", "avail@test.com")
    prod, _ = setup_product_and_variants(db_session, "Avail Prod", "100.00")

    # Future plan
    future_plan = setup_plan(
        db_session,
        "Future Plan",
        "50.00",
        from_date=date.today() + timedelta(days=10),
    )
    res_future = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(future_plan.id),
            "startDate": str(date.today()),
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res_future.status_code == 400
    assert "not yet available" in res_future.json()["detail"]["message"].lower()

    # Expired plan
    expired_plan = setup_plan(
        db_session,
        "Expired Plan",
        "50.00",
        until_date=date.today() - timedelta(days=2),
    )
    res_expired = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(expired_plan.id),
            "startDate": str(date.today()),
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res_expired.status_code == 400
    assert "expired" in res_expired.json()["detail"]["message"].lower()


def test_plan_min_quantity_constraint(client: TestClient, db_session):
    cust = setup_customer(db_session, "MinQty Cust", "minqty@test.com")
    prod, _ = setup_product_and_variants(db_session, "MinQty Prod", "100.00")
    plan = setup_plan(db_session, "MinQty Plan", "50.00", min_quantity=5)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 2, "taxRuleIds": []}],
        },
    )
    assert res.status_code == 400
    assert "minimum quantity" in res.json()["detail"]["message"].lower()


def test_price_snapshot_preservation(client: TestClient, db_session):
    cust = setup_customer(db_session, "Snap Cust", "snap@test.com")
    prod, _ = setup_product_and_variants(db_session, "Snap Prod", "200.00")
    plan = setup_plan(db_session, "Snap Plan", "100.00")

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]

    # Mutate source product and plan prices
    prod.sales_price = Decimal("999.00")
    plan.price = Decimal("888.00")
    db_session.commit()

    # Re-fetch subscription: lines and snapshots must be immutable
    res_get = client.get(f"/api/v1/subscriptions/{sub_id}")
    data = res_get.json()
    assert data["lines"][1]["unitPrice"] == "200.00"
    assert data["lines"][0]["unitPrice"] == "100.00"
    assert data["recurringSubtotal"] == "300.00"


# ==============================================================================
# 2. BILLING CALCULATIONS (ANCHOR-PRESERVING & CALENDAR-AWARE)
# ==============================================================================


def test_billing_calculator_intervals():
    # DAILY
    assert calculate_next_billing_date(
        date(2026, 1, 1), date(2026, 1, 1), "DAILY", 1
    ) == date(2026, 1, 2)
    assert calculate_next_billing_date(
        date(2026, 1, 1), date(2026, 1, 1), "DAILY", 7
    ) == date(2026, 1, 8)

    # WEEKLY
    assert calculate_next_billing_date(
        date(2026, 1, 1), date(2026, 1, 1), "WEEKLY", 1
    ) == date(2026, 1, 8)
    assert calculate_next_billing_date(
        date(2026, 1, 1), date(2026, 1, 1), "WEEKLY", 2
    ) == date(2026, 1, 15)

    # MONTHLY
    assert calculate_next_billing_date(
        date(2026, 1, 15), date(2026, 1, 15), "MONTHLY", 1
    ) == date(2026, 2, 15)
    # Quarterly (3 months)
    assert calculate_next_billing_date(
        date(2026, 1, 15), date(2026, 1, 15), "MONTHLY", 3
    ) == date(2026, 4, 15)

    # YEARLY
    assert calculate_next_billing_date(
        date(2026, 5, 20), date(2026, 5, 20), "YEARLY", 1
    ) == date(2027, 5, 20)
    assert calculate_next_billing_date(
        date(2026, 5, 20), date(2026, 5, 20), "YEARLY", 2
    ) == date(2028, 5, 20)


def test_billing_calculator_leap_year_handling():
    # Leap year leap day: 2024-02-29 + 1 year -> 2025-02-28
    assert calculate_next_billing_date(
        date(2024, 2, 29), date(2024, 2, 29), "YEARLY", 1
    ) == date(2025, 2, 28)

    # 2024-02-29 + 4 years -> 2028-02-29 (leap year again)
    assert calculate_next_billing_date(
        date(2024, 2, 29), date(2024, 2, 29), "YEARLY", 4
    ) == date(2028, 2, 29)


def test_billing_calculator_month_end_anchor_preservation():
    anchor = date(2026, 1, 31)

    # Jan 31 -> Feb 28
    cycle_1 = calculate_next_billing_date(
        anchor_date=anchor, from_date=anchor, interval="MONTHLY", interval_count=1
    )
    assert cycle_1 == date(2026, 2, 28)

    # Next cycle from Feb 28 must preserve the Jan 31 anchor -> Mar 31 (NOT Mar 28!)
    cycle_2 = calculate_next_billing_date(
        anchor_date=anchor,
        from_date=cycle_1,
        interval="MONTHLY",
        interval_count=1,
    )
    assert cycle_2 == date(2026, 3, 31)

    # Next cycle -> Apr 30
    cycle_3 = calculate_next_billing_date(
        anchor_date=anchor,
        from_date=cycle_2,
        interval="MONTHLY",
        interval_count=1,
    )
    assert cycle_3 == date(2026, 4, 30)

    # Next cycle -> May 31
    cycle_4 = calculate_next_billing_date(
        anchor_date=anchor,
        from_date=cycle_3,
        interval="MONTHLY",
        interval_count=1,
    )
    assert cycle_4 == date(2026, 5, 31)


def test_normalized_monthly_value_calculation(db_session):
    plan_monthly = setup_plan(db_session, "P_Monthly", "100.00", "MONTHLY", 1)
    assert calculate_normalized_monthly_value(plan_monthly) == Decimal("100.00")

    plan_quarterly = setup_plan(db_session, "P_Quarterly", "300.00", "MONTHLY", 3)
    assert calculate_normalized_monthly_value(plan_quarterly) == Decimal("100.00")

    plan_yearly = setup_plan(db_session, "P_Yearly", "1200.00", "YEARLY", 1)
    assert calculate_normalized_monthly_value(plan_yearly) == Decimal("100.00")


# ==============================================================================
# 3. LIFECYCLE STATE TRANSITIONS
# ==============================================================================


def test_activation_flow_and_invalid_transitions(client: TestClient, db_session):
    cust = setup_customer(db_session, "Act Cust", "act@test.com")
    prod, _ = setup_product_and_variants(db_session, "Act Prod", "100.00")
    plan = setup_plan(db_session, "Act Plan", "50.00")

    res_create = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res_create.json()["id"]
    assert res_create.json()["status"] == "CONFIRMED"

    # Activate
    res_act = client.post(f"/api/v1/subscriptions/{sub_id}/activate")
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "ACTIVE"

    # Activate again should raise conflict
    res_act2 = client.post(f"/api/v1/subscriptions/{sub_id}/activate")
    assert res_act2.status_code == 409

    # Close subscription
    res_close = client.post(f"/api/v1/subscriptions/{sub_id}/close")
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"

    # Closed subscription cannot be activated or paused
    res_act_closed = client.post(f"/api/v1/subscriptions/{sub_id}/activate")
    assert res_act_closed.status_code == 409

    res_pause_closed = client.post(f"/api/v1/subscriptions/{sub_id}/pause")
    assert res_pause_closed.status_code == 409


def test_archived_plan_preservation(client: TestClient, db_session):
    cust = setup_customer(db_session, "Arch Cust", "arch@test.com")
    prod, _ = setup_product_and_variants(db_session, "Arch Prod", "100.00")
    plan = setup_plan(db_session, "Arch Plan", "50.00")

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # Deactivate / archive plan
    plan.is_active = False
    db_session.commit()

    # Subscription must still function and remain accessible
    res_get = client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "ACTIVE"


# ==============================================================================
# 4. PAUSE AND RESUME
# ==============================================================================


def test_pause_and_resume_shifts_billing_date(client: TestClient, db_session):
    cust = setup_customer(db_session, "Pause Cust", "pause@test.com")
    prod, _ = setup_product_and_variants(db_session, "Pause Prod", "100.00")
    plan = setup_plan(db_session, "Pause Plan", "50.00", allow_pause=True)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # Pause
    res_pause = client.post(f"/api/v1/subscriptions/{sub_id}/pause")
    assert res_pause.status_code == 200
    sub_data = res_pause.json()
    assert sub_data["status"] == "PAUSED"
    assert sub_data["pausedAt"] is not None

    # Simulate pause duration by modifying paused_at backwards 5 days
    sub = db_session.get(Subscription, uuid.UUID(sub_id))
    original_billing_date = sub.next_billing_date
    sub.paused_at = datetime.now(timezone.utc) - timedelta(days=5)
    db_session.commit()

    # Resume
    res_resume = client.post(f"/api/v1/subscriptions/{sub_id}/resume")
    assert res_resume.status_code == 200
    resumed_data = res_resume.json()
    assert resumed_data["status"] == "ACTIVE"
    assert resumed_data["pausedAt"] is None

    # Shifted billing date
    expected_new_billing = original_billing_date + timedelta(days=5)
    assert resumed_data["nextBillingDate"] == str(expected_new_billing)


def test_pause_rejected_when_not_allowed(client: TestClient, db_session):
    cust = setup_customer(db_session, "NoPause Cust", "nopause@test.com")
    prod, _ = setup_product_and_variants(db_session, "NoPause Prod", "100.00")
    plan = setup_plan(db_session, "NoPause Plan", "50.00", allow_pause=False)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_pause = client.post(f"/api/v1/subscriptions/{sub_id}/pause")
    assert res_pause.status_code == 409
    assert "does not permit pausing" in res_pause.json()["detail"]["message"].lower()


# ==============================================================================
# 5. PLAN CHANGES
# ==============================================================================


def test_plan_change_same_value(client: TestClient, db_session):
    cust = setup_customer(db_session, "PC Same Cust", "pcsame@test.com")
    prod, _ = setup_product_and_variants(db_session, "PC Prod", "100.00")
    plan1 = setup_plan(db_session, "Monthly A", "100.00", "MONTHLY", 1)
    plan2 = setup_plan(db_session, "Monthly B", "100.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan1.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_change = client.post(
        f"/api/v1/subscriptions/{sub_id}/change-plan",
        json={"newPlanId": str(plan2.id)},
    )
    assert res_change.status_code == 200
    data = res_change.json()
    assert data["adjustmentType"] == "NO_CHARGE"
    assert data["adjustmentAmount"] == "0.00"
    assert data["subscription"]["planId"] == str(plan2.id)


def test_plan_change_upgrade_immediate_difference(client: TestClient, db_session):
    cust = setup_customer(db_session, "PC Up Cust", "pcup@test.com")
    prod, _ = setup_product_and_variants(db_session, "PC Prod Up", "100.00")
    plan1 = setup_plan(db_session, "Starter", "50.00", "MONTHLY", 1)
    plan2 = setup_plan(db_session, "Enterprise", "150.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan1.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_change = client.post(
        f"/api/v1/subscriptions/{sub_id}/change-plan",
        json={"newPlanId": str(plan2.id)},
    )
    assert res_change.status_code == 200
    data = res_change.json()
    assert data["adjustmentType"] == "IMMEDIATE_UPGRADE_DIFFERENCE"
    assert data["adjustmentAmount"] == "100.00"
    assert data["subscription"]["planId"] == str(plan2.id)

    # Verify PendingBillingAdjustment created in database
    adj = (
        db_session.query(PendingBillingAdjustment)
        .filter(PendingBillingAdjustment.subscription_id == uuid.UUID(sub_id))
        .first()
    )
    assert adj is not None
    assert adj.adjustment_type == "IMMEDIATE_UPGRADE_DIFFERENCE"
    assert adj.amount == Decimal("100.00")


def test_plan_change_downgrade_deferred(client: TestClient, db_session):
    cust = setup_customer(db_session, "PC Down Cust", "pcdown@test.com")
    prod, _ = setup_product_and_variants(db_session, "PC Prod Down", "100.00")
    plan1 = setup_plan(db_session, "Enterprise", "200.00", "MONTHLY", 1)
    plan2 = setup_plan(db_session, "Basic", "50.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan1.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_change = client.post(
        f"/api/v1/subscriptions/{sub_id}/change-plan",
        json={"newPlanId": str(plan2.id)},
    )
    assert res_change.status_code == 200
    data = res_change.json()
    assert data["adjustmentType"] == "DEFERRED_DOWNGRADE"
    assert data["adjustmentAmount"] == "0.00"
    # Plan remains plan1 until next renewal!
    assert data["subscription"]["planId"] == str(plan1.id)
    assert data["subscription"]["pendingPlanId"] == str(plan2.id)


def test_plan_change_currency_mismatch_rejected(client: TestClient, db_session):
    cust = setup_customer(db_session, "PC Curr Cust", "pccurr@test.com")
    prod, _ = setup_product_and_variants(db_session, "PC Curr Prod", "100.00")
    plan_inr = setup_plan(db_session, "INR Plan", "100.00", currency="INR")
    plan_usd = setup_plan(db_session, "USD Plan", "50.00", currency="USD")

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan_inr.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]

    res_change = client.post(
        f"/api/v1/subscriptions/{sub_id}/change-plan",
        json={"newPlanId": str(plan_usd.id)},
    )
    assert res_change.status_code == 409
    assert "currency mismatch" in res_change.json()["detail"]["message"].lower()


# ==============================================================================
# 6. AUTOMATIC RENEWALS & IDEMPOTENCY
# ==============================================================================


def test_renewal_cycle_advancement_and_idempotency(client: TestClient, db_session):
    cust = setup_customer(db_session, "Renew Cust", "renew@test.com")
    prod, _ = setup_product_and_variants(db_session, "Renew Prod", "100.00")
    plan = setup_plan(db_session, "Renew Plan", "50.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # Cycle 1 ends at 2026-12-01
    res_renew = client.post(f"/api/v1/subscriptions/{sub_id}/renew")
    assert res_renew.status_code == 200
    renewed_data = res_renew.json()
    assert renewed_data["startDate"] == "2026-11-01"
    assert renewed_data["expiryDate"] == "2027-01-01"
    assert renewed_data["nextBillingDate"] == "2027-01-01"

    # Verify renewal record created
    records = (
        db_session.query(SubscriptionRenewalRecord)
        .filter(SubscriptionRenewalRecord.subscription_id == uuid.UUID(sub_id))
        .all()
    )
    assert len(records) == 1
    assert records[0].period_start == date(2026, 12, 1)
    assert records[0].period_end == date(2027, 1, 1)
    assert records[0].cycle_number == 2

    # Re-invoking renewal for the same billing date returns 409 DUPLICATE_RENEWAL_CYCLE
    res_renew_dup = client.post(
        f"/api/v1/subscriptions/{sub_id}/renew?expectedRenewalDate=2026-12-01"
    )
    assert res_renew_dup.status_code == 409
    assert res_renew_dup.json()["detail"]["code"] == "DUPLICATE_RENEWAL_CYCLE"


def test_renewal_applies_deferred_downgrade(client: TestClient, db_session):
    cust = setup_customer(db_session, "Renew Down Cust", "renewdown@test.com")
    prod, _ = setup_product_and_variants(db_session, "Renew Down Prod", "100.00")
    plan_high = setup_plan(db_session, "High Plan", "200.00", "MONTHLY", 1)
    plan_low = setup_plan(db_session, "Low Plan", "50.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan_high.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # Schedule downgrade
    client.post(
        f"/api/v1/subscriptions/{sub_id}/change-plan",
        json={"newPlanId": str(plan_low.id)},
    )

    # Perform renewal: must switch to low plan and clear pending_plan_id
    res_renew = client.post(f"/api/v1/subscriptions/{sub_id}/renew")
    assert res_renew.status_code == 200
    data = res_renew.json()
    assert data["planId"] == str(plan_low.id)
    assert data["pendingPlanId"] is None


def test_renewal_with_scheduled_cancellation_closes_subscription(
    client: TestClient, db_session
):
    cust = setup_customer(db_session, "CancelEnd Cust", "cancelend@test.com")
    prod, _ = setup_product_and_variants(db_session, "CancelEnd Prod", "100.00")
    plan = setup_plan(db_session, "CancelEnd Plan", "50.00", "MONTHLY", 1)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # Customer/staff schedules cancellation at period end
    res_cancel = client.post(
        f"/api/v1/subscriptions/{sub_id}/cancel",
        json={"reason": "Customer migrating systems"},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["cancelAtPeriodEnd"] is True
    # Still ACTIVE during period
    assert res_cancel.json()["status"] == "ACTIVE"

    # When renewal executes at period end, subscription transitions to CLOSED
    res_renew = client.post(f"/api/v1/subscriptions/{sub_id}/renew")
    assert res_renew.status_code == 200
    assert res_renew.json()["status"] == "CLOSED"


def test_renewal_rejected_when_not_allowed_by_plan(client: TestClient, db_session):
    cust = setup_customer(db_session, "NoRenew Cust", "norenew@test.com")
    prod, _ = setup_product_and_variants(db_session, "NoRenew Prod", "100.00")
    plan = setup_plan(db_session, "NoRenew Plan", "50.00", allow_renewal=False)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_renew = client.post(f"/api/v1/subscriptions/{sub_id}/renew")
    assert res_renew.status_code == 409
    assert "does not permit renewal" in res_renew.json()["detail"]["message"].lower()


# ==============================================================================
# 7. EARLY CLOSURE POLICY & PATCH METADATA
# ==============================================================================


def test_early_close_policy_disallowed(client: TestClient, db_session):
    cust = setup_customer(db_session, "NoClose Cust", "noclose@test.com")
    prod, _ = setup_product_and_variants(db_session, "NoClose Prod", "100.00")
    plan = setup_plan(db_session, "NoClose Plan", "50.00", allow_early_close=False)

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    res_close = client.post(f"/api/v1/subscriptions/{sub_id}/close")
    assert res_close.status_code == 409
    assert "does not permit early close" in res_close.json()["detail"]["message"].lower()


def test_patch_subscription_metadata(client: TestClient, db_session):
    cust = setup_customer(db_session, "Patch Cust", "patch@test.com")
    prod, _ = setup_product_and_variants(db_session, "Patch Prod", "100.00")
    plan = setup_plan(db_session, "Patch Plan", "50.00")

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "paymentTerms": "Immediate",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]

    res_patch = client.patch(
        f"/api/v1/subscriptions/{sub_id}",
        json={"paymentTerms": "Net 45", "cancelAtPeriodEnd": True},
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["paymentTerms"] == "Net 45"
    assert data["cancelAtPeriodEnd"] is True


# ==============================================================================
# 8. AUTHORIZATION & TENANT ISOLATION
# ==============================================================================


def test_customer_isolation_and_permissions(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust_own = role_users["own_profile"]
    cust_other = role_users["other_profile"]

    prod, _ = setup_product_and_variants(db_session, "Iso Prod", "100.00")
    plan = setup_plan(db_session, "Iso Plan", "50.00")

    # Staff creates a subscription for own customer
    auth_as(role_users["staff"])
    res_own = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust_own.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    own_sub_id = res_own.json()["id"]
    client.post(f"/api/v1/subscriptions/{own_sub_id}/activate")

    # Staff creates a subscription for other customer
    res_other = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust_other.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    other_sub_id = res_other.json()["id"]

    # Customer logs in
    auth_as(cust_user)

    # 1. Can view own subscription
    res_get_own = client.get(f"/api/v1/subscriptions/{own_sub_id}")
    assert res_get_own.status_code == 200

    # 2. Cannot view other customer's subscription (404 for isolation)
    res_get_other = client.get(f"/api/v1/subscriptions/{other_sub_id}")
    assert res_get_other.status_code == 404

    # 3. List only shows own subscriptions
    res_list = client.get("/api/v1/subscriptions")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    sub_ids = [item["id"] for item in items]
    assert own_sub_id in sub_ids
    assert other_sub_id not in sub_ids

    # 4. Customer cannot activate, pause, or renew
    assert client.post(f"/api/v1/subscriptions/{own_sub_id}/activate").status_code == 403
    assert client.post(f"/api/v1/subscriptions/{own_sub_id}/pause").status_code == 403
    assert client.post(f"/api/v1/subscriptions/{own_sub_id}/renew").status_code == 403
    assert client.post(f"/api/v1/subscriptions/{own_sub_id}/close").status_code == 403

    # 5. Customer CAN request cancellation of own subscription
    res_cancel_own = client.post(
        f"/api/v1/subscriptions/{own_sub_id}/cancel",
        json={"reason": "Self-service cancellation"},
    )
    assert res_cancel_own.status_code == 200
    assert res_cancel_own.json()["cancelAtPeriodEnd"] is True

    # 6. Customer cannot cancel someone else's subscription
    res_cancel_other = client.post(
        f"/api/v1/subscriptions/{other_sub_id}/cancel",
        json={"reason": "Attempt cancel other"},
    )
    assert res_cancel_other.status_code == 403


def test_subscription_audit_history(client: TestClient, db_session):
    cust = setup_customer(db_session, "Hist Cust", "hist@test.com")
    prod, _ = setup_product_and_variants(db_session, "Hist Prod", "100.00")
    plan = setup_plan(db_session, "Hist Plan", "50.00")

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]

    client.post(f"/api/v1/subscriptions/{sub_id}/activate")
    client.post(f"/api/v1/subscriptions/{sub_id}/pause")
    client.post(f"/api/v1/subscriptions/{sub_id}/resume")

    res_history = client.get(f"/api/v1/subscriptions/{sub_id}/history")
    assert res_history.status_code == 200
    events = res_history.json()
    event_types = [e["eventType"] for e in events]

    assert "CREATED" in event_types
    assert "ACTIVATED" in event_types
    assert "PAUSED" in event_types
    assert "RESUMED" in event_types


def test_auto_close_at_end_policy_closes_subscription_at_expiry(
    client: TestClient, db_session
):
    cust = setup_customer(db_session, "AutoClose Cust", "autoclose@test.com")
    prod, _ = setup_product_and_variants(db_session, "AutoClose Prod", "100.00")
    plan = setup_plan(
        db_session,
        "AutoClose Plan",
        "50.00",
        auto_close_at_end=True,
        allow_renewal=True,
    )

    res = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    sub_id = res.json()["id"]
    client.post(f"/api/v1/subscriptions/{sub_id}/activate")

    # When renewal executes at period end, plan-level autoCloseAtEnd closes subscription
    res_renew = client.post(f"/api/v1/subscriptions/{sub_id}/renew")
    assert res_renew.status_code == 200
    assert res_renew.json()["status"] == "CLOSED"

    # Verify event audit trail records autoCloseAtEnd reason
    res_hist = client.get(f"/api/v1/subscriptions/{sub_id}/history")
    assert res_hist.status_code == 200
    latest_event = res_hist.json()[0]
    assert latest_event["eventType"] == "CLOSED"
    assert "autoCloseAtEnd" in latest_event["description"]


def test_subscription_counter_first_time_atomic_initialization(
    client: TestClient, db_session
):
    current_year = datetime.now(timezone.utc).year
    # Clean up counter for this test
    existing_counter = db_session.get(SubscriptionCounter, current_year)
    if existing_counter:
        db_session.delete(existing_counter)
        db_session.commit()

    cust = setup_customer(db_session, "Atomic Counter Cust", "atomic@test.com")
    prod, _ = setup_product_and_variants(db_session, "Atomic Prod", "100.00")
    plan = setup_plan(db_session, "Atomic Plan", "50.00")

    # First subscription creation when counter row does not exist
    res1 = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res1.status_code == 201
    sub1_number = res1.json()["number"]
    assert sub1_number.startswith(f"SUB-{current_year}-")
    seq1 = int(sub1_number.split("-")[-1])

    # Counter row must now exist in database with next_seq incremented
    counter = db_session.get(SubscriptionCounter, current_year)
    assert counter is not None
    assert counter.next_seq == seq1 + 1

    # Second subscription creation immediately increments
    res2 = client.post(
        "/api/v1/subscriptions",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res2.status_code == 201
    sub2_number = res2.json()["number"]
    seq2 = int(sub2_number.split("-")[-1])
    assert seq2 == seq1 + 1

    db_session.refresh(counter)
    assert counter.next_seq == seq2 + 1


def test_quotation_acceptance_transactional_integrity(
    client: TestClient, role_users: dict, auth_as, db_session
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]
    prod, _ = setup_product_and_variants(db_session, "Tx Prod", "100.00")
    plan = setup_plan(db_session, "Tx Plan", "50.00")

    # Staff creates quotation
    auth_as(role_users["staff"])
    res_q = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res_q.status_code == 201
    q_id = res_q.json()["id"]

    # Customer accepts quotation
    auth_as(cust_user)
    res_accept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_accept.status_code == 200
    q_data = res_accept.json()
    assert q_data["status"] == "CONFIRMED"
    sub_id = q_data["subscriptionId"]
    assert sub_id is not None

    # Verify reciprocal references
    sub = db_session.get(Subscription, uuid.UUID(sub_id))
    q = db_session.get(Quotation, uuid.UUID(q_id))
    assert q.subscription_id == sub.id
    assert sub.quotation_id == q.id
    assert sub.status == "CONFIRMED"

    # Attempt duplicate acceptance returns 409 and does NOT duplicate subscription
    res_reaccept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_reaccept.status_code == 409

    # Total subscriptions with this quotation_id is exactly 1
    total_subs = (
        db_session.query(Subscription)
        .filter(Subscription.quotation_id == q.id)
        .count()
    )
    assert total_subs == 1
