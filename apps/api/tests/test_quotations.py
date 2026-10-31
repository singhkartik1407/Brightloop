import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.customer import Customer
from app.models.discount import DiscountRule, DiscountScope, DiscountTarget, DiscountType
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.quotation import Quotation, QuotationCounter, QuotationStatus
from app.models.quote_template import QuoteTemplate, QuoteTemplateLine
from app.models.tax import TaxRule, TaxType
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def default_seller_state(monkeypatch):
    monkeypatch.setattr(settings, "ORGANIZATION_STATE", "Maharashtra")



def setup_customer(db_session, name="Acme Corp", email="billing@acme.com", state="Maharashtra", user_id=None):
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


def setup_product_and_variants(db_session, name="Cloud Server", base_price="100.00"):
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


def setup_plan(db_session, name="Standard Plan", price="50.00", from_date=None, until_date=None):
    plan = Plan(
        name=name,
        price=price,
        currency="INR",
        billing_interval="MONTHLY",
        interval_count=1,
        min_quantity=1,
        available_from=from_date,
        available_until=until_date,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_create_quotation_from_scratch_with_calculations(client: TestClient, db_session):
    cust = setup_customer(db_session, "Test Corp 1", "corp1@test.com")
    prod, v1 = setup_product_and_variants(db_session, "Compute", "100.00")
    plan = setup_plan(db_session, "Pro Plan", "50.00")

    payload = {
        "customerId": str(cust.id),
        "planId": str(plan.id),
        "startDate": "2026-11-01",
        "paymentTerms": "Net 30",
        "validityDays": 14,
        "lines": [
            {
                "productId": str(prod.id),
                "quantity": 2,
                "selectedVariantIds": [str(v1.id)],
                "taxRuleIds": [],
            }
        ],
    }

    res = client.post("/api/v1/quotations", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["number"].startswith("QUO-")
    assert data["customerId"] == str(cust.id)
    assert data["customerName"] == "Test Corp 1"
    assert data["planId"] == str(plan.id)
    assert data["planName"] == "Pro Plan"
    assert data["status"] == "DRAFT"
    assert data["currency"] == "INR"

    # Plan line: 50.00; Product line: (100.00 + 20.00) * 2 = 240.00
    # Subtotal = 290.00
    assert data["subtotal"] == "290.00"
    assert len(data["lines"]) == 2  # Plan line + Product line
    assert Decimal(data["total"]) >= Decimal("290.00")


def test_create_quotation_from_template(client: TestClient, db_session):
    cust = setup_customer(db_session, "Template Cust", "temp@cust.com")
    prod, v1 = setup_product_and_variants(db_session, "Template Item", "200.00")
    plan = setup_plan(db_session, "Template Plan", "80.00")

    # Create template
    t_res = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Quick Starter Template",
            "validityDays": 21,
            "planId": str(plan.id),
            "lines": [
                {
                    "productId": str(prod.id),
                    "quantity": 3,
                    "selectedVariantIds": [str(v1.id)],
                }
            ],
        },
    )
    assert t_res.status_code == 201
    template_id = t_res.json()["id"]

    # Create quotation using templateId without duplicating plan/lines
    q_res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "templateId": template_id,
            "startDate": "2026-11-15",
        },
    )
    assert q_res.status_code == 201
    q_data = q_res.json()
    assert q_data["planId"] == str(plan.id)
    # Unit price = 200 + 20 = 220; qty 3 = 660; plan = 80 -> subtotal = 740.00
    assert q_data["subtotal"] == "740.00"


def test_customer_quotation_isolation_and_permissions(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust1 = role_users["own_profile"]
    cust2 = role_users["other_profile"]

    prod, _ = setup_product_and_variants(db_session, "Shared Item", "100.00")
    plan = setup_plan(db_session, "Shared Plan", "25.00")

    # Admin creates quotes for both customers
    auth_as(role_users["admin"])
    q1 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust1.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    ).json()

    q2 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust2.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    ).json()

    # Customer cannot create quotations
    auth_as(cust_user)
    res_cust_create = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust1.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res_cust_create.status_code == 403

    # Customer can view own quote
    res_get_own = client.get(f"/api/v1/quotations/{q1['id']}")
    assert res_get_own.status_code == 200

    # Customer CANNOT view other customer's quote
    res_get_other = client.get(f"/api/v1/quotations/{q2['id']}")
    assert res_get_other.status_code == 404

    # Customer list shows only own quote
    res_list = client.get("/api/v1/quotations")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert all(item["customerId"] == str(cust1.id) for item in items)


def test_quotation_lifecycle_send_accept_and_reject(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]

    prod, _ = setup_product_and_variants(db_session, "Life Prod", "150.00")
    plan = setup_plan(db_session, "Life Plan", "50.00")

    # Create discount to verify redemption tracking upon acceptance
    now_utc = datetime.now(timezone.utc)
    disc = DiscountRule(
        name="Launch Discount",
        code="LAUNCH10",
        discount_type=DiscountType.PERCENTAGE.value,
        value="10.00",
        scope=DiscountScope.SUBSCRIPTION.value,
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        used_count=0,
        is_active=True,
    )
    db_session.add(disc)
    db_session.commit()

    auth_as(role_users["admin"])
    q_res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "discountCode": "LAUNCH10",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    q_id = q_res.json()["id"]

    # Verify initial creation did NOT increment discount usedCount
    db_session.refresh(disc)
    assert disc.used_count == 0

    # Staff sends quote
    auth_as(role_users["staff"])
    res_send = client.post(f"/api/v1/quotations/{q_id}/send")
    assert res_send.status_code == 200
    assert res_send.json()["status"] == "QUOTATION"

    # Customer accepts quote
    auth_as(cust_user)
    res_accept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "CONFIRMED"

    # Discount used_count incremented upon acceptance
    db_session.refresh(disc)
    assert disc.used_count == 1

    # Cannot accept again
    res_reaccept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_reaccept.status_code == 409

    # Cannot reject confirmed quotation
    res_reject = client.post(f"/api/v1/quotations/{q_id}/reject")
    assert res_reject.status_code == 409


def test_quotation_reject_flow(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]

    prod, _ = setup_product_and_variants(db_session, "Item-R", "100.00")
    plan = setup_plan(db_session, "Plan-R", "20.00")

    auth_as(role_users["admin"])
    q_res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    q_id = q_res.json()["id"]

    client.post(f"/api/v1/quotations/{q_id}/send")

    # Customer rejects own quotation
    auth_as(cust_user)
    res_reject = client.post(f"/api/v1/quotations/{q_id}/reject")
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"


def test_discount_highest_saving_non_stacking(client: TestClient, db_session):
    cust = setup_customer(db_session, "Discount Corp", "disc@corp.com")
    prod, _ = setup_product_and_variants(db_session, "Database License", "500.00")
    plan = setup_plan(db_session, "Enterprise Plan", "100.00")

    now_utc = datetime.now(timezone.utc)

    # Rule 1: 5% subscription discount -> saving = 5% of 600.00 = 30.00
    r1 = DiscountRule(
        name="Small 5%",
        discount_type=DiscountType.PERCENTAGE.value,
        value="5.00",
        scope=DiscountScope.SUBSCRIPTION.value,
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        is_active=True,
    )
    # Rule 2: Fixed 80.00 subscription discount -> saving = 80.00 (HIGHEST)
    r2 = DiscountRule(
        name="Big 80 Fixed",
        discount_type=DiscountType.FIXED.value,
        value="80.00",
        scope=DiscountScope.SUBSCRIPTION.value,
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        is_active=True,
    )
    # Rule 3: 10% product discount on prod -> saving = 10% of 500.00 = 50.00
    r3 = DiscountRule(
        name="Prod 10%",
        discount_type=DiscountType.PERCENTAGE.value,
        value="10.00",
        scope=DiscountScope.PRODUCT.value,
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        is_active=True,
    )
    r3.targets.append(DiscountTarget(product_id=prod.id))

    db_session.add_all([r1, r2, r3])
    db_session.commit()

    # Create quotation without specifying code (automatic candidate evaluation)
    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res.status_code == 201
    data = res.json()

    # Subtotal = 500 + 100 = 600.00
    # Rule 2 produces highest saving (80.00)
    # NO STACKING: discountTotal MUST be exactly 80.00, NOT 80 + 50 + 30
    assert data["discountTotal"] == "80.00"
    assert Decimal(data["total"]) == Decimal(data["subtotal"]) - Decimal("80.00") + Decimal(data["taxTotal"])


def test_gst_intra_and_inter_state_place_of_supply(client: TestClient, db_session):
    # Setup GST tax rules
    cgst = TaxRule(
        name="Central GST 9%",
        code="CGST9",
        tax_type=TaxType.CGST.value,
        rate_percent="9.00",
        jurisdiction="Maharashtra",
        is_inclusive=False,
        is_active=True,
    )
    sgst = TaxRule(
        name="State GST 9%",
        code="SGST9",
        tax_type=TaxType.SGST.value,
        rate_percent="9.00",
        jurisdiction="Maharashtra",
        is_inclusive=False,
        is_active=True,
    )
    igst = TaxRule(
        name="Integrated GST 18%",
        code="IGST18",
        tax_type=TaxType.IGST.value,
        rate_percent="18.00",
        jurisdiction="InterState",
        is_inclusive=False,
        is_active=True,
    )
    db_session.add_all([cgst, sgst, igst])
    db_session.commit()

    prod, _ = setup_product_and_variants(db_session, "GST Hardware", "1000.00")
    plan = setup_plan(db_session, "GST Plan", "0.00")

    # 1. Intra-state supply: Customer state == Maharashtra (same as organization state)
    intra_cust = setup_customer(db_session, "MH Customer", "mh@cust.com", state="Maharashtra")
    intra_res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(intra_cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert intra_res.status_code == 201
    intra_data = intra_res.json()
    prod_line = [l for l in intra_data["lines"] if l["productId"] == str(prod.id)][0]
    tax_codes = [t["code"] for t in prod_line["taxes"]]
    assert "CGST9" in tax_codes
    assert "SGST9" in tax_codes
    assert "IGST18" not in tax_codes
    # 9% of 1000 + 9% of 1000 = 180.00
    assert intra_data["taxTotal"] == "180.00"

    # 2. Inter-state supply: Customer state == Karnataka (different state)
    inter_cust = setup_customer(db_session, "KA Customer", "ka@cust.com", state="Karnataka")
    inter_res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(inter_cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert inter_res.status_code == 201
    inter_data = inter_res.json()
    prod_line_inter = [l for l in inter_data["lines"] if l["productId"] == str(prod.id)][0]
    inter_tax_codes = [t["code"] for t in prod_line_inter["taxes"]]
    assert "IGST18" in inter_tax_codes
    assert "CGST9" not in inter_tax_codes
    assert "SGST9" not in inter_tax_codes
    # 18% of 1000 = 180.00
    assert inter_data["taxTotal"] == "180.00"


def test_quotation_historical_snapshot_consistency(client: TestClient, db_session):
    cust = setup_customer(db_session, "Snapshot Client", "snap@client.com")
    prod, _ = setup_product_and_variants(db_session, "Original Product", "100.00")
    plan = setup_plan(db_session, "Original Plan", "50.00")

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res.status_code == 201
    quote = res.json()
    q_id = quote["id"]
    assert quote["subtotal"] == "150.00"

    # Later: Product price doubles, plan price changes
    prod.sales_price = "200.00"
    plan.price = "100.00"
    db_session.commit()

    # Retrieve existing quotation - must remain EXACTLY at 150.00!
    res_get = client.get(f"/api/v1/quotations/{q_id}")
    assert res_get.status_code == 200
    unchanged_quote = res_get.json()
    assert unchanged_quote["subtotal"] == "150.00"
    assert unchanged_quote["planName"] == "Original Plan"


def test_quotation_update_draft_and_conflict(client: TestClient, db_session):
    cust = setup_customer(db_session, "Patch Cust", "patch@cust.com")
    prod, _ = setup_product_and_variants(db_session, "Patch Prod", "100.00")
    plan1 = setup_plan(db_session, "Patch Plan 1", "50.00")
    plan2 = setup_plan(db_session, "Patch Plan 2", "70.00")

    q = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan1.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    ).json()
    q_id = q["id"]

    # Empty patch returns 400
    res_empty = client.patch(f"/api/v1/quotations/{q_id}", json={})
    assert res_empty.status_code == 400

    # Valid patch
    res_patch = client.patch(
        f"/api/v1/quotations/{q_id}",
        json={"planId": str(plan2.id), "paymentTerms": "Due on receipt"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["planId"] == str(plan2.id)
    assert res_patch.json()["paymentTerms"] == "Due on receipt"
    # New subtotal = 100 + 70 = 170.00
    assert res_patch.json()["subtotal"] == "170.00"

    # Send quotation (moves to QUOTATION status)
    client.post(f"/api/v1/quotations/{q_id}/send")

    # Cannot patch sent quotation
    res_conflict = client.patch(
        f"/api/v1/quotations/{q_id}",
        json={"paymentTerms": "Net 60"},
    )
    assert res_conflict.status_code == 409


def test_plan_availability_date_validation(client: TestClient, db_session):
    cust = setup_customer(db_session, "Date Cust", "date@cust.com")
    prod, _ = setup_product_and_variants(db_session, "Date Prod", "100.00")

    today = date.today()
    future_plan = setup_plan(
        db_session, "Future Plan", "50.00", from_date=today + timedelta(days=10)
    )
    expired_plan = setup_plan(
        db_session, "Expired Plan", "50.00", until_date=today - timedelta(days=1)
    )

    # Future plan fails
    res_future = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(future_plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res_future.status_code == 400

    # Expired plan fails
    res_exp = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(expired_plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res_exp.status_code == 400


def test_inclusive_tax_calculation(client: TestClient, db_session):
    cust = setup_customer(db_session, "Tax Cust", "tax@cust.com", state="Delhi")
    prod, _ = setup_product_and_variants(db_session, "Inclusive Product", "118.00")
    plan = setup_plan(db_session, "Free Base", "0.00")

    inc_tax = TaxRule(
        name="VAT 18% Inclusive",
        code="VAT18INC",
        tax_type=TaxType.GENERIC.value,
        rate_percent="18.00",
        is_inclusive=True,
        is_active=True,
    )
    db_session.add(inc_tax)
    db_session.commit()

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [
                {
                    "productId": str(prod.id),
                    "quantity": 1,
                    "taxRuleIds": [str(inc_tax.id)],
                }
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    # 118 with 18% inclusive tax:
    # Tax amount = 118 * 18 / 118 = 18.00
    # Line total = 118.00 (tax is included)
    assert data["subtotal"] == "118.00"
    assert data["taxTotal"] == "18.00"
    assert data["total"] == "118.00"


def test_discount_thresholds_and_caps(client: TestClient, db_session):
    cust = setup_customer(db_session, "Threshold Cust", "thresh@cust.com")
    prod, _ = setup_product_and_variants(db_session, "Thresh Prod", "100.00")
    plan = setup_plan(db_session, "Thresh Plan", "0.00")

    now_utc = datetime.now(timezone.utc)
    disc = DiscountRule(
        name="Spend 500 Get 50",
        code="SPEND500",
        discount_type=DiscountType.FIXED.value,
        value="50.00",
        scope=DiscountScope.SUBSCRIPTION.value,
        minimum_purchase="500.00",
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        is_active=True,
    )
    db_session.add(disc)
    db_session.commit()

    # Purchase below 500.00 (qty 2 = 200.00)
    res_below = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 2}],
        },
    )
    assert res_below.status_code == 201
    assert res_below.json()["discountTotal"] == "0.00"

    # Purchase above 500.00 (qty 6 = 600.00)
    res_above = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 6}],
        },
    )
    assert res_above.status_code == 201
    assert res_above.json()["discountTotal"] == "50.00"


def test_missing_seller_state_raises_error(client: TestClient, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ORGANIZATION_STATE", None)
    cust = setup_customer(db_session, "No Seller Corp", "noseller@corp.com", state="Maharashtra")
    prod, _ = setup_product_and_variants(db_session, "Basic Widget", "100.00")
    plan = setup_plan(db_session, "Basic Plan", "50.00")

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "SELLER_STATE_NOT_CONFIGURED"


def test_explicit_tax_rules_work_without_organization_state(client: TestClient, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ORGANIZATION_STATE", None)
    cust = setup_customer(db_session, "Explicit Tax Corp", "explicit@corp.com", state="Maharashtra")
    prod, _ = setup_product_and_variants(db_session, "Explicit Tax Widget", "100.00")
    plan = setup_plan(db_session, "Explicit Plan", "50.00")

    tax = TaxRule(
        name="Custom Service Tax",
        code="CST10",
        tax_type=TaxType.GENERIC.value,
        rate_percent="10.00",
        is_inclusive=False,
        is_active=True,
    )
    db_session.add(tax)
    db_session.commit()

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [
                {
                    "productId": str(prod.id),
                    "quantity": 1,
                    "taxRuleIds": [str(tax.id)],
                }
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["taxTotal"] == "10.00"
    assert data["total"] == "160.00"


def test_missing_customer_billing_state_raises_error(client: TestClient, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ORGANIZATION_STATE", "Maharashtra")
    cust = setup_customer(db_session, "No State Cust", "nostate@cust.com", state=None)
    prod, _ = setup_product_and_variants(db_session, "State Check Widget", "100.00")
    plan = setup_plan(db_session, "State Plan", "50.00")

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1}],
        },
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "CUSTOMER_BILLING_STATE_REQUIRED"


def test_multi_component_inclusive_cgst_sgst_extraction(client: TestClient, db_session):
    cust = setup_customer(db_session, "Inclusive Cust", "inclusive@cust.com", state="Maharashtra")
    prod, _ = setup_product_and_variants(db_session, "Inclusive Suite", "118.00")
    plan = setup_plan(db_session, "Inclusive Free Base", "0.00")

    cgst_inc = TaxRule(
        name="Central GST 9% Inclusive",
        code="CGST9INC",
        tax_type=TaxType.CGST.value,
        rate_percent="9.00",
        is_inclusive=True,
        is_active=True,
    )
    sgst_inc = TaxRule(
        name="State GST 9% Inclusive",
        code="SGST9INC",
        tax_type=TaxType.SGST.value,
        rate_percent="9.00",
        is_inclusive=True,
        is_active=True,
    )
    db_session.add_all([cgst_inc, sgst_inc])
    db_session.commit()

    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [
                {
                    "productId": str(prod.id),
                    "quantity": 1,
                    "taxRuleIds": [str(cgst_inc.id), str(sgst_inc.id)],
                }
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    prod_line = [l for l in data["lines"] if l["productId"] == str(prod.id)][0]
    tax_items = {t["code"]: Decimal(t["amount"]) for t in prod_line["taxes"]}
    assert tax_items["CGST9INC"] == Decimal("9.00")
    assert tax_items["SGST9INC"] == Decimal("9.00")
    assert data["taxTotal"] == "18.00"
    assert data["total"] == "118.00"
    assert data["subtotal"] == "118.00"


def test_discount_acceptance_cap_concurrency_guard(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]

    prod, _ = setup_product_and_variants(db_session, "Cap Product", "100.00")
    plan = setup_plan(db_session, "Cap Plan", "50.00")

    now_utc = datetime.now(timezone.utc)
    disc = DiscountRule(
        name="Single Use Cap",
        code="ONETIME10",
        discount_type=DiscountType.PERCENTAGE.value,
        value="10.00",
        scope=DiscountScope.SUBSCRIPTION.value,
        starts_at=now_utc - timedelta(days=1),
        ends_at=now_utc + timedelta(days=30),
        max_uses=1,
        used_count=0,
        is_active=True,
    )
    db_session.add(disc)
    db_session.commit()

    auth_as(role_users["admin"])
    q1 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "discountCode": "ONETIME10",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    ).json()

    q2 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "discountCode": "ONETIME10",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    ).json()

    auth_as(role_users["staff"])
    client.post(f"/api/v1/quotations/{q1['id']}/send")
    client.post(f"/api/v1/quotations/{q2['id']}/send")

    auth_as(cust_user)
    res_accept1 = client.post(f"/api/v1/quotations/{q1['id']}/accept")
    assert res_accept1.status_code == 200
    assert res_accept1.json()["status"] == "CONFIRMED"

    db_session.refresh(disc)
    assert disc.used_count == 1

    res_accept2 = client.post(f"/api/v1/quotations/{q2['id']}/accept")
    assert res_accept2.status_code == 409
    assert res_accept2.json()["detail"]["code"] == "DISCOUNT_CAP_REACHED"

    db_session.refresh(disc)
    assert disc.used_count == 1


def test_sequential_quotation_numbering_counter(client: TestClient, db_session):
    cust = setup_customer(db_session, "Sequential Corp", "seq@corp.com")
    prod, _ = setup_product_and_variants(db_session, "Seq Item", "100.00")
    plan = setup_plan(db_session, "Seq Plan", "50.00")

    numbers = []
    for _ in range(3):
        res = client.post(
            "/api/v1/quotations",
            json={
                "customerId": str(cust.id),
                "planId": str(plan.id),
                "startDate": "2026-11-01",
                "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
            },
        )
        assert res.status_code == 201
        numbers.append(res.json()["number"])

    seqs = [int(n.split("-")[-1]) for n in numbers]
    assert seqs[1] == seqs[0] + 1
    assert seqs[2] == seqs[1] + 1

    current_year = datetime.now(timezone.utc).year
    counter = db_session.get(QuotationCounter, current_year)
    assert counter is not None
    assert counter.next_seq == seqs[-1] + 1


def test_quotation_counter_first_time_atomic_initialization(client: TestClient, db_session):
    # Verify behavior when no counter row exists for a calendar year
    current_year = datetime.now(timezone.utc).year
    # Ensure counter row does not exist
    existing_counter = db_session.get(QuotationCounter, current_year)
    if existing_counter:
        db_session.delete(existing_counter)
        db_session.commit()

    cust = setup_customer(db_session, "First Time Corp", "first@corp.com")
    prod, _ = setup_product_and_variants(db_session, "First Widget", "100.00")
    plan = setup_plan(db_session, "First Plan", "50.00")

    # Creating the very first quotation when no counter row exists
    res1 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res1.status_code == 201
    quote1_number = res1.json()["number"]
    assert quote1_number.startswith(f"QUO-{current_year}-")
    seq1 = int(quote1_number.split("-")[-1])

    # Counter row must now exist in database
    counter = db_session.get(QuotationCounter, current_year)
    assert counter is not None
    assert counter.next_seq == seq1 + 1

    # Creating the second quotation immediately increments from existing row
    res2 = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res2.status_code == 201
    quote2_number = res2.json()["number"]
    seq2 = int(quote2_number.split("-")[-1])
    assert seq2 == seq1 + 1

    db_session.refresh(counter)
    assert counter.next_seq == seq2 + 1



def test_expired_quotation_cannot_be_patched_or_accepted(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    cust_user = role_users["customer"]
    cust = role_users["own_profile"]
    prod, _ = setup_product_and_variants(db_session, "Expiry Prod", "100.00")
    plan = setup_plan(db_session, "Expiry Plan", "50.00")

    auth_as(role_users["admin"])
    res = client.post(
        "/api/v1/quotations",
        json={
            "customerId": str(cust.id),
            "planId": str(plan.id),
            "startDate": "2026-11-01",
            "lines": [{"productId": str(prod.id), "quantity": 1, "taxRuleIds": []}],
        },
    )
    assert res.status_code == 201
    q_id = res.json()["id"]

    q_record = db_session.get(Quotation, uuid.UUID(q_id))
    q_record.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()

    res_patch = client.patch(
        f"/api/v1/quotations/{q_id}",
        json={"paymentTerms": "Immediate"},
    )
    assert res_patch.status_code == 409
    assert "expired" in res_patch.json()["detail"]["message"].lower()

    auth_as(cust_user)
    res_accept = client.post(f"/api/v1/quotations/{q_id}/accept")
    assert res_accept.status_code == 409
    assert "expired" in res_accept.json()["detail"]["message"].lower()


