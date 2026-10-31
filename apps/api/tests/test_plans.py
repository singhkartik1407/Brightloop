from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models import BillingInterval, Plan, Product


def sample_product_payload(**overrides):
    payload = {
        "name": "Cloud Platform",
        "type": "SOFTWARE",
        "salesPrice": "5000.00",
        "costPrice": "2000.00",
        "currency": "INR",
        "notes": "Core cloud subscription",
        "variants": [],
    }
    payload.update(overrides)
    return payload


def create_test_product(client, **overrides):
    res = client.post("/api/v1/products", json=sample_product_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


def plan_payload(**overrides):
    payload = {
        "name": "Standard Monthly",
        "price": "999.00",
        "currency": "INR",
        "billingInterval": "MONTHLY",
        "intervalCount": 1,
        "minQuantity": 1,
    }
    payload.update(overrides)
    return payload


def create_test_plan(client, **overrides):
    res = client.post("/api/v1/plans", json=plan_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------
# Plan Creation
# ---------------------------------------------------------

def test_create_plan_minimal(client):
    plan = create_test_plan(client)
    assert plan["name"] == "Standard Monthly"
    assert plan["price"] == "999.00"
    assert plan["currency"] == "INR"
    assert plan["billingInterval"] == "MONTHLY"
    assert plan["intervalCount"] == 1
    assert plan["minQuantity"] == 1
    assert plan["autoCloseAtEnd"] is False
    assert plan["allowEarlyClose"] is False
    assert plan["allowPause"] is False
    assert plan["allowRenewal"] is True
    assert plan["isActive"] is True
    assert "createdAt" in plan
    assert plan["productId"] is None


def test_create_plan_full_with_product_and_policies(client):
    product = create_test_product(client, name="Enterprise DB")
    payload = plan_payload(
        name="Enterprise Annual",
        description="High availability enterprise plan",
        productId=product["id"],
        price="12000.00",
        currency="USD",
        billingInterval="YEARLY",
        intervalCount=1,
        minQuantity=10,
        availableFrom="2026-11-01",
        availableUntil="2027-10-31",
        autoCloseAtEnd=True,
        allowEarlyClose=True,
        allowPause=True,
        allowRenewal=False,
    )
    res = client.post("/api/v1/plans", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Enterprise Annual"
    assert body["description"] == "High availability enterprise plan"
    assert body["productId"] == product["id"]
    assert body["price"] == "12000.00"
    assert body["currency"] == "USD"
    assert body["billingInterval"] == "YEARLY"
    assert body["minQuantity"] == 10
    assert body["availableFrom"] == "2026-11-01"
    assert body["availableUntil"] == "2027-10-31"
    assert body["autoCloseAtEnd"] is True
    assert body["allowEarlyClose"] is True
    assert body["allowPause"] is True
    assert body["allowRenewal"] is False


# ---------------------------------------------------------
# Listing, Search and Pagination
# ---------------------------------------------------------

def test_list_search_and_pagination_plans(client):
    create_test_plan(client, name="Starter Weekly", billingInterval="WEEKLY")
    create_test_plan(client, name="Professional Monthly", billingInterval="MONTHLY")
    create_test_plan(client, name="Enterprise Yearly", billingInterval="YEARLY")

    # Search
    search_res = client.get("/api/v1/plans", params={"search": "professional"})
    assert search_res.status_code == 200
    search_body = search_res.json()
    assert search_body["total"] == 1
    assert search_body["items"][0]["name"] == "Professional Monthly"

    # Pagination: page 1 of 2 items
    p1_res = client.get("/api/v1/plans", params={"page": 1, "pageSize": 2})
    assert p1_res.status_code == 200
    p1 = p1_res.json()
    assert p1["total"] == 3
    assert len(p1["items"]) == 2
    assert p1["page"] == 1
    assert p1["pageSize"] == 2

    # Pagination: page 2
    p2_res = client.get("/api/v1/plans", params={"page": 2, "pageSize": 2})
    assert p2_res.status_code == 200
    p2 = p2_res.json()
    assert p2["total"] == 3
    assert len(p2["items"]) == 1


def test_filter_by_product_and_billing_interval(client):
    product1 = create_test_product(client, name="Product One")
    product2 = create_test_product(client, name="Product Two")

    p1 = create_test_plan(client, name="P1 Monthly", productId=product1["id"], billingInterval="MONTHLY")
    create_test_plan(client, name="P1 Yearly", productId=product1["id"], billingInterval="YEARLY")
    p2 = create_test_plan(client, name="P2 Monthly", productId=product2["id"], billingInterval="MONTHLY")

    # Filter by product1
    res1 = client.get("/api/v1/plans", params={"productId": product1["id"]})
    assert res1.status_code == 200
    assert res1.json()["total"] == 2

    # Filter by product1 and billingInterval=MONTHLY
    res2 = client.get(
        "/api/v1/plans",
        params={"productId": product1["id"], "billingInterval": "MONTHLY"},
    )
    assert res2.status_code == 200
    items = res2.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == p1["id"]


# ---------------------------------------------------------
# Detail Retrieval and Update
# ---------------------------------------------------------

def test_plan_detail_and_update(client):
    plan = create_test_plan(client)
    plan_id = plan["id"]

    # Detail
    detail = client.get(f"/api/v1/plans/{plan_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == plan_id

    # Update
    update_res = client.patch(
        f"/api/v1/plans/{plan_id}",
        json={
            "name": "Standard Monthly Plus",
            "price": "1299.00",
            "description": "Upgraded tier",
            "minQuantity": 3,
            "allowPause": True,
        },
    )
    assert update_res.status_code == 200
    body = update_res.json()
    assert body["name"] == "Standard Monthly Plus"
    assert body["price"] == "1299.00"
    assert body["description"] == "Upgraded tier"
    assert body["minQuantity"] == 3
    assert body["allowPause"] is True


def test_empty_plan_patch_returns_400(client):
    plan = create_test_plan(client)
    res = client.patch(f"/api/v1/plans/{plan['id']}", json={})
    assert res.status_code == 400


# ---------------------------------------------------------
# Archival and Restoration
# ---------------------------------------------------------

def test_plan_archival_and_restoration(client):
    plan = create_test_plan(client)
    plan_id = plan["id"]

    # Archive
    archive_res = client.post(f"/api/v1/plans/{plan_id}/archive")
    assert archive_res.status_code == 204

    # Default list hides archived
    list_active = client.get("/api/v1/plans")
    assert list_active.json()["total"] == 0

    # Query with isActive=False shows archived
    list_archived = client.get("/api/v1/plans", params={"isActive": False})
    assert list_archived.json()["total"] == 1

    # Detail still accessible
    detail = client.get(f"/api/v1/plans/{plan_id}")
    assert detail.status_code == 200
    assert detail.json()["isActive"] is False

    # Cannot update archived plan without restoring
    blocked_update = client.patch(f"/api/v1/plans/{plan_id}", json={"name": "New Name"})
    assert blocked_update.status_code == 409

    # Restore via restore endpoint
    restore_res = client.post(f"/api/v1/plans/{plan_id}/restore")
    assert restore_res.status_code == 200
    assert restore_res.json()["isActive"] is True

    # Re-archive
    client.post(f"/api/v1/plans/{plan_id}/archive")

    # Restore via PATCH isActive=true
    patch_restore = client.patch(f"/api/v1/plans/{plan_id}", json={"isActive": True, "name": "Restored Name"})
    assert patch_restore.status_code == 200
    assert patch_restore.json()["isActive"] is True
    assert patch_restore.json()["name"] == "Restored Name"


# ---------------------------------------------------------
# Product Association Validation
# ---------------------------------------------------------

def test_product_association_validation(client):
    nonexistent_id = str(uuid4())

    # Create with nonexistent product
    res = client.post("/api/v1/plans", json=plan_payload(productId=nonexistent_id))
    assert res.status_code == 404

    # Create plan with valid product
    product = create_test_product(client, name="Widget Service", type="SERVICE")
    plan = create_test_plan(client, productId=product["id"])
    assert plan["productId"] == product["id"]

    # Update with nonexistent product
    patch_res = client.patch(f"/api/v1/plans/{plan['id']}", json={"productId": nonexistent_id})
    assert patch_res.status_code == 404


# ---------------------------------------------------------
# Billing Intervals & Dates Validation
# ---------------------------------------------------------

@pytest.mark.parametrize("interval", ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"])
def test_valid_billing_intervals(client, interval):
    plan = create_test_plan(client, name=f"Plan {interval}", billingInterval=interval)
    assert plan["billingInterval"] == interval


@pytest.mark.parametrize("invalid_interval", ["HOURLY", "BIWEEKLY", "DECADELY", "invalid"])
def test_rejects_invalid_billing_intervals(client, invalid_interval):
    res = client.post("/api/v1/plans", json=plan_payload(billingInterval=invalid_interval))
    assert res.status_code == 422


def test_invalid_availability_date_ranges(client):
    # End precedes start on create
    res = client.post(
        "/api/v1/plans",
        json=plan_payload(availableFrom="2026-12-01", availableUntil="2026-11-01"),
    )
    assert res.status_code == 422

    # Create valid plan
    plan = create_test_plan(
        client,
        availableFrom="2026-11-01",
        availableUntil="2026-11-30",
    )

    # Patch end to precede start
    patch_res = client.patch(
        f"/api/v1/plans/{plan['id']}",
        json={"availableUntil": "2026-10-31"},
    )
    assert patch_res.status_code == 422

    # Patch start to exceed end
    patch_res2 = client.patch(
        f"/api/v1/plans/{plan['id']}",
        json={"availableFrom": "2026-12-15"},
    )
    assert patch_res2.status_code == 422


# ---------------------------------------------------------
# Monetary & Quantity Validation
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "changes",
    [
        {"price": "-10.00"},
        {"price": "10.999"},
        {"price": 100},
        {"price": "abc"},
        {"currency": "USDX"},
        {"currency": "US"},
        {"minQuantity": 0},
        {"minQuantity": -1},
        {"intervalCount": 0},
        {"intervalCount": -2},
        {"name": "   "},
    ],
)
def test_rejects_invalid_plan_fields(client, changes):
    res = client.post("/api/v1/plans", json=plan_payload(**changes))
    assert res.status_code == 422


# ---------------------------------------------------------
# Duplicate / Conflict Handling
# ---------------------------------------------------------

def test_duplicate_active_plan_name_rejected(client):
    product = create_test_product(client, name="Platform Alpha")
    create_test_plan(client, name="Gold Tier", productId=product["id"])

    # Duplicate create for same product
    dup_res = client.post("/api/v1/plans", json=plan_payload(name="  gold tier  ", productId=product["id"]))
    assert dup_res.status_code == 409

    # Another product can have the same plan name
    product_beta = create_test_product(client, name="Platform Beta")
    beta_plan = create_test_plan(client, name="Gold Tier", productId=product_beta["id"])
    assert beta_plan["name"] == "Gold Tier"

    # Renaming to existing active plan name fails
    silver_plan = create_test_plan(client, name="Silver Tier", productId=product["id"])
    rename_res = client.patch(f"/api/v1/plans/{silver_plan['id']}", json={"name": "Gold Tier"})
    assert rename_res.status_code == 409


# ---------------------------------------------------------
# Role Permissions
# ---------------------------------------------------------

def test_staff_and_customer_role_permissions(client, role_users, auth_as):
    plan = create_test_plan(client)
    plan_id = plan["id"]

    # Staff can create, get, list, update, and archive plans
    auth_as(role_users["staff"])
    staff_list = client.get("/api/v1/plans")
    assert staff_list.status_code == 200

    staff_get = client.get(f"/api/v1/plans/{plan_id}")
    assert staff_get.status_code == 200

    staff_create = client.post("/api/v1/plans", json=plan_payload(name="Staff Created Plan"))
    assert staff_create.status_code == 201

    staff_update = client.patch(f"/api/v1/plans/{plan_id}", json={"description": "Staff updated"})
    assert staff_update.status_code == 200

    staff_archive = client.post(f"/api/v1/plans/{plan_id}/archive")
    assert staff_archive.status_code == 204

    staff_restore = client.post(f"/api/v1/plans/{plan_id}/restore")
    assert staff_restore.status_code == 200

    # Customer is strictly forbidden from all plan operations
    auth_as(role_users["customer"])
    assert client.get("/api/v1/plans").status_code == 403
    assert client.get(f"/api/v1/plans/{plan_id}").status_code == 403
    assert client.post("/api/v1/plans", json=plan_payload(name="Cust Plan")).status_code == 403
    assert client.patch(f"/api/v1/plans/{plan_id}", json={"name": "Nope"}).status_code == 403
    assert client.post(f"/api/v1/plans/{plan_id}/archive").status_code == 403
    assert client.post(f"/api/v1/plans/{plan_id}/restore").status_code == 403


# ---------------------------------------------------------
# Edge Cases: Not Found, Invalid UUID, Invalid Pagination
# ---------------------------------------------------------

def test_plan_not_found_and_invalid_uuid(client):
    nonexistent = str(uuid4())
    assert client.get(f"/api/v1/plans/{nonexistent}").status_code == 404
    assert client.patch(f"/api/v1/plans/{nonexistent}", json={"name": "Test"}).status_code == 404
    assert client.post(f"/api/v1/plans/{nonexistent}/archive").status_code == 404
    assert client.post(f"/api/v1/plans/{nonexistent}/restore").status_code == 404

    assert client.get("/api/v1/plans/not-a-valid-uuid").status_code == 422
    assert client.patch("/api/v1/plans/not-a-valid-uuid", json={"name": "Test"}).status_code == 422


@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 0}, {"pageSize": 101}])
def test_invalid_plan_pagination(client, params):
    assert client.get("/api/v1/plans", params=params).status_code == 422
