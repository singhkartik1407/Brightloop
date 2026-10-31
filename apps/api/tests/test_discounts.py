from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models import DiscountRule, DiscountScope, DiscountType, Product


def sample_product(client, name="Sample SaaS"):
    res = client.post(
        "/api/v1/products",
        json={
            "name": name,
            "type": "SOFTWARE",
            "salesPrice": "2000.00",
            "costPrice": "500.00",
            "currency": "INR",
            "variants": [],
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def discount_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "name": "Diwali Festival Discount",
        "code": "DIWALI50",
        "discountType": "PERCENTAGE",
        "value": "15.00",
        "scope": "SUBSCRIPTION",
        "startsAt": now.isoformat(),
        "endsAt": (now + timedelta(days=30)).isoformat(),
        "maxUses": 100,
        "minimumPurchase": "1000.00",
        "minimumQuantity": 1,
    }
    payload.update(overrides)
    return payload


def create_test_discount_rule(client, **overrides):
    res = client.post("/api/v1/discount-rules", json=discount_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------
# Creation
# ---------------------------------------------------------

def test_create_percentage_subscription_discount(client):
    rule = create_test_discount_rule(client)
    assert rule["name"] == "Diwali Festival Discount"
    assert rule["code"] == "DIWALI50"
    assert rule["discountType"] == "PERCENTAGE"
    assert rule["value"] == "15.00"
    assert rule["scope"] == "SUBSCRIPTION"
    assert rule["maxUses"] == 100
    assert rule["usedCount"] == 0
    assert rule["isActive"] is True
    assert rule["productIds"] == []
    assert "createdAt" in rule


def test_create_fixed_product_discount(client):
    product = sample_product(client, name="Security Suite")
    rule = create_test_discount_rule(
        client,
        name="Flat 500 Off",
        code="FLAT500",
        discountType="FIXED",
        value="500.00",
        scope="PRODUCT",
        productIds=[product["id"]],
    )
    assert rule["discountType"] == "FIXED"
    assert rule["value"] == "500.00"
    assert rule["scope"] == "PRODUCT"
    assert rule["productIds"] == [product["id"]]


# ---------------------------------------------------------
# Listing, Search and Pagination
# ---------------------------------------------------------

def test_list_search_and_pagination_discounts(client):
    create_test_discount_rule(client, name="New Year Special", code="NY2027", discountType="PERCENTAGE", scope="SUBSCRIPTION")
    create_test_discount_rule(client, name="Black Friday Promo", code="BF2026", discountType="FIXED", scope="PRODUCT")
    create_test_discount_rule(client, name="Cyber Monday Deal", code="CM2026", discountType="PERCENTAGE", scope="PRODUCT")

    # Search
    search_res = client.get("/api/v1/discount-rules", params={"search": "black friday"})
    assert search_res.status_code == 200
    search_body = search_res.json()
    assert search_body["total"] == 1
    assert search_body["items"][0]["code"] == "BF2026"

    # Filter by discountType
    fixed_res = client.get("/api/v1/discount-rules", params={"discountType": "FIXED"})
    assert fixed_res.status_code == 200
    assert fixed_res.json()["total"] == 1

    # Filter by scope
    sub_res = client.get("/api/v1/discount-rules", params={"scope": "SUBSCRIPTION"})
    assert sub_res.status_code == 200
    assert sub_res.json()["total"] == 1

    # Pagination: page 1 of 2
    p1 = client.get("/api/v1/discount-rules", params={"page": 1, "pageSize": 2}).json()
    assert p1["total"] == 3
    assert len(p1["items"]) == 2
    assert p1["page"] == 1

    # Pagination: page 2
    p2 = client.get("/api/v1/discount-rules", params={"page": 2, "pageSize": 2}).json()
    assert p2["total"] == 3
    assert len(p2["items"]) == 1


# ---------------------------------------------------------
# Detail Retrieval and Update
# ---------------------------------------------------------

def test_discount_rule_detail_and_update(client):
    product1 = sample_product(client, name="CRM Tool")
    product2 = sample_product(client, name="ERP Suite")

    rule = create_test_discount_rule(client, productIds=[product1["id"]])
    rule_id = rule["id"]

    # Detail
    detail = client.get(f"/api/v1/discount-rules/{rule_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == rule_id

    # Update: change name, value, and product targets
    update_res = client.patch(
        f"/api/v1/discount-rules/{rule_id}",
        json={
            "name": "Diwali Mega Sale",
            "value": "20.00",
            "productIds": [product2["id"]],
        },
    )
    assert update_res.status_code == 200
    body = update_res.json()
    assert body["name"] == "Diwali Mega Sale"
    assert body["value"] == "20.00"
    assert body["productIds"] == [product2["id"]]


def test_empty_discount_patch_returns_400(client):
    rule = create_test_discount_rule(client)
    res = client.patch(f"/api/v1/discount-rules/{rule['id']}", json={})
    assert res.status_code == 400


# ---------------------------------------------------------
# Archival and Restoration
# ---------------------------------------------------------

def test_discount_rule_archival_and_restoration(client):
    rule = create_test_discount_rule(client)
    rule_id = rule["id"]

    # Archive
    assert client.post(f"/api/v1/discount-rules/{rule_id}/archive").status_code == 204

    # Default list excludes archived
    assert client.get("/api/v1/discount-rules").json()["total"] == 0

    # Query with isActive=false includes archived
    assert client.get("/api/v1/discount-rules", params={"isActive": False}).json()["total"] == 1

    # Detail still accessible
    assert client.get(f"/api/v1/discount-rules/{rule_id}").status_code == 200

    # Update archived rule blocked
    assert client.patch(f"/api/v1/discount-rules/{rule_id}", json={"name": "New Name"}).status_code == 409

    # Restore via restore endpoint
    restore_res = client.post(f"/api/v1/discount-rules/{rule_id}/restore")
    assert restore_res.status_code == 200
    assert restore_res.json()["isActive"] is True

    # Re-archive
    client.post(f"/api/v1/discount-rules/{rule_id}/archive")

    # Restore via PATCH
    patch_restore = client.patch(f"/api/v1/discount-rules/{rule_id}", json={"isActive": True})
    assert patch_restore.status_code == 200
    assert patch_restore.json()["isActive"] is True


# ---------------------------------------------------------
# Percentage & Value Validations
# ---------------------------------------------------------

def test_percentage_discount_validation(client):
    # Valid percentages: 0.00, 50.00, 100.00
    r1 = create_test_discount_rule(client, code="P_ZERO", discountType="PERCENTAGE", value="0.00")
    assert r1["value"] == "0.00"

    r2 = create_test_discount_rule(client, code="P_HUNDRED", discountType="PERCENTAGE", value="100.00")
    assert r2["value"] == "100.00"

    # Percentage exceeding 100 rejected
    res1 = client.post("/api/v1/discount-rules", json=discount_payload(discountType="PERCENTAGE", value="100.01"))
    assert res1.status_code == 422

    # Negative percentage rejected
    res2 = client.post("/api/v1/discount-rules", json=discount_payload(discountType="PERCENTAGE", value="-5.00"))
    assert res2.status_code == 422


def test_fixed_discount_validation(client):
    # Valid fixed values
    r1 = create_test_discount_rule(client, code="F_VALID", discountType="FIXED", value="2500.50")
    assert r1["value"] == "2500.50"

    # Negative fixed rejected
    res = client.post("/api/v1/discount-rules", json=discount_payload(discountType="FIXED", value="-1.00"))
    assert res.status_code == 422


# ---------------------------------------------------------
# Date Range & Usage Validations
# ---------------------------------------------------------

def test_date_range_validation(client):
    now = datetime.now(timezone.utc)

    # Ends before starts on create
    res = client.post(
        "/api/v1/discount-rules",
        json=discount_payload(
            startsAt=now.isoformat(),
            endsAt=(now - timedelta(days=1)).isoformat(),
        ),
    )
    assert res.status_code == 422

    # Create valid rule
    rule = create_test_discount_rule(
        client,
        startsAt=now.isoformat(),
        endsAt=(now + timedelta(days=10)).isoformat(),
    )

    # Patch ends to precede starts
    patch_res = client.patch(
        f"/api/v1/discount-rules/{rule['id']}",
        json={"endsAt": (now - timedelta(days=5)).isoformat()},
    )
    assert patch_res.status_code == 422


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"maxUses": 0},
        {"maxUses": -1},
        {"minimumQuantity": 0},
        {"minimumQuantity": -5},
        {"minimumPurchase": "-10.00"},
        {"value": "10.123"},  # 3 decimal places
    ],
)
def test_rejects_invalid_discount_fields(client, invalid_fields):
    res = client.post("/api/v1/discount-rules", json=discount_payload(**invalid_fields))
    assert res.status_code == 422


# ---------------------------------------------------------
# Product Association Validation
# ---------------------------------------------------------

def test_discount_product_association(client):
    nonexistent = str(uuid4())

    # Create with missing product
    res = client.post(
        "/api/v1/discount-rules",
        json=discount_payload(scope="PRODUCT", productIds=[nonexistent]),
    )
    assert res.status_code == 404

    # Update with missing product
    rule = create_test_discount_rule(client)
    patch_res = client.patch(
        f"/api/v1/discount-rules/{rule['id']}",
        json={"productIds": [nonexistent]},
    )
    assert patch_res.status_code == 404


# ---------------------------------------------------------
# Duplicate Code Handling
# ---------------------------------------------------------

def test_duplicate_discount_code_rejected(client):
    create_test_discount_rule(client, code="PROMO2026")

    # Duplicate on create
    dup_res = client.post("/api/v1/discount-rules", json=discount_payload(code="  promo2026  "))
    assert dup_res.status_code == 409

    # Duplicate on patch
    rule2 = create_test_discount_rule(client, code="PROMO2027")
    patch_dup = client.patch(f"/api/v1/discount-rules/{rule2['id']}", json={"code": "promo2026"})
    assert patch_dup.status_code == 409


# ---------------------------------------------------------
# Permissions: Admin Only for Mutations, Admin & Staff for Read
# ---------------------------------------------------------

def test_discount_role_permissions(client, role_users, auth_as):
    rule = create_test_discount_rule(client)
    rule_id = rule["id"]

    # Staff can list and view details
    auth_as(role_users["staff"])
    assert client.get("/api/v1/discount-rules").status_code == 200
    assert client.get(f"/api/v1/discount-rules/{rule_id}").status_code == 200

    # Staff is forbidden from mutations (Admin-only)
    assert client.post("/api/v1/discount-rules", json=discount_payload(code="STAFF_DISC")).status_code == 403
    assert client.patch(f"/api/v1/discount-rules/{rule_id}", json={"name": "Staff Update"}).status_code == 403
    assert client.post(f"/api/v1/discount-rules/{rule_id}/archive").status_code == 403
    assert client.post(f"/api/v1/discount-rules/{rule_id}/restore").status_code == 403

    # Customer is strictly forbidden from all discount administration
    auth_as(role_users["customer"])
    assert client.get("/api/v1/discount-rules").status_code == 403
    assert client.get(f"/api/v1/discount-rules/{rule_id}").status_code == 403
    assert client.post("/api/v1/discount-rules", json=discount_payload(code="CUST_DISC")).status_code == 403
    assert client.patch(f"/api/v1/discount-rules/{rule_id}", json={"name": "Cust Update"}).status_code == 403
    assert client.post(f"/api/v1/discount-rules/{rule_id}/archive").status_code == 403
    assert client.post(f"/api/v1/discount-rules/{rule_id}/restore").status_code == 403


# ---------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------

def test_discount_not_found_and_invalid_uuid(client):
    nonexistent = str(uuid4())
    assert client.get(f"/api/v1/discount-rules/{nonexistent}").status_code == 404
    assert client.patch(f"/api/v1/discount-rules/{nonexistent}", json={"name": "Test"}).status_code == 404
    assert client.post(f"/api/v1/discount-rules/{nonexistent}/archive").status_code == 404
    assert client.post(f"/api/v1/discount-rules/{nonexistent}/restore").status_code == 404

    assert client.get("/api/v1/discount-rules/not-a-valid-uuid").status_code == 422


@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 0}, {"pageSize": 101}])
def test_invalid_discount_pagination(client, params):
    assert client.get("/api/v1/discount-rules", params=params).status_code == 422
