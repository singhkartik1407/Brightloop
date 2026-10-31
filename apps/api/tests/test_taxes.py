from __future__ import annotations

from uuid import uuid4

import pytest

from app.models import TaxRule, TaxType


def tax_payload(**overrides):
    payload = {
        "name": "Goods and Services Tax 18%",
        "code": "GST_18",
        "taxType": "GENERIC",
        "ratePercent": "18.00",
        "jurisdiction": "India",
        "isInclusive": False,
    }
    payload.update(overrides)
    return payload


def create_test_tax_rule(client, **overrides):
    res = client.post("/api/v1/tax-rules", json=tax_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------
# Creation
# ---------------------------------------------------------

def test_create_tax_rule_minimal(client):
    rule = create_test_tax_rule(client)
    assert rule["name"] == "Goods and Services Tax 18%"
    assert rule["code"] == "GST_18"
    assert rule["taxType"] == "GENERIC"
    assert rule["ratePercent"] == "18.00"
    assert rule["jurisdiction"] == "India"
    assert rule["isInclusive"] is False
    assert rule["isActive"] is True
    assert "createdAt" in rule


@pytest.mark.parametrize("tax_type", ["GENERIC", "CGST", "SGST", "IGST", "OTHER"])
def test_create_tax_rule_types(client, tax_type):
    rule = create_test_tax_rule(
        client,
        name=f"Tax {tax_type}",
        code=f"TAX_{tax_type}",
        taxType=tax_type,
        ratePercent="9.00",
    )
    assert rule["taxType"] == tax_type


def test_create_inclusive_tax_rule(client):
    rule = create_test_tax_rule(
        client,
        name="VAT UK",
        code="VAT_20",
        ratePercent="20.00",
        isInclusive=True,
    )
    assert rule["isInclusive"] is True


# ---------------------------------------------------------
# Listing, Search and Pagination
# ---------------------------------------------------------

def test_list_search_and_pagination_taxes(client):
    create_test_tax_rule(client, name="Central GST", code="CGST_9", taxType="CGST", ratePercent="9.00", jurisdiction="MH")
    create_test_tax_rule(client, name="State GST", code="SGST_9", taxType="SGST", ratePercent="9.00", jurisdiction="MH")
    create_test_tax_rule(client, name="Integrated GST", code="IGST_18", taxType="IGST", ratePercent="18.00", jurisdiction="Interstate")

    # Search
    search_res = client.get("/api/v1/tax-rules", params={"search": "integrated"})
    assert search_res.status_code == 200
    search_body = search_res.json()
    assert search_body["total"] == 1
    assert search_body["items"][0]["code"] == "IGST_18"

    # Filter by taxType
    type_res = client.get("/api/v1/tax-rules", params={"taxType": "CGST"})
    assert type_res.status_code == 200
    assert type_res.json()["total"] == 1
    assert type_res.json()["items"][0]["code"] == "CGST_9"

    # Pagination: page 1 of 2
    p1 = client.get("/api/v1/tax-rules", params={"page": 1, "pageSize": 2}).json()
    assert p1["total"] == 3
    assert len(p1["items"]) == 2
    assert p1["page"] == 1

    # Pagination: page 2
    p2 = client.get("/api/v1/tax-rules", params={"page": 2, "pageSize": 2}).json()
    assert p2["total"] == 3
    assert len(p2["items"]) == 1


# ---------------------------------------------------------
# Detail Retrieval and Update
# ---------------------------------------------------------

def test_tax_rule_detail_and_update(client):
    rule = create_test_tax_rule(client)
    rule_id = rule["id"]

    # Detail
    detail = client.get(f"/api/v1/tax-rules/{rule_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == rule_id

    # Update
    update_res = client.patch(
        f"/api/v1/tax-rules/{rule_id}",
        json={"name": "GST Standard 18%", "ratePercent": "18.00", "jurisdiction": "All India"},
    )
    assert update_res.status_code == 200
    body = update_res.json()
    assert body["name"] == "GST Standard 18%"
    assert body["jurisdiction"] == "All India"


def test_empty_tax_rule_patch_returns_400(client):
    rule = create_test_tax_rule(client)
    res = client.patch(f"/api/v1/tax-rules/{rule['id']}", json={})
    assert res.status_code == 400


# ---------------------------------------------------------
# Archival and Restoration
# ---------------------------------------------------------

def test_tax_rule_archival_and_restoration(client):
    rule = create_test_tax_rule(client)
    rule_id = rule["id"]

    # Archive
    assert client.post(f"/api/v1/tax-rules/{rule_id}/archive").status_code == 204

    # Default list excludes archived
    assert client.get("/api/v1/tax-rules").json()["total"] == 0

    # Query with isActive=false includes archived
    assert client.get("/api/v1/tax-rules", params={"isActive": False}).json()["total"] == 1

    # Detail still accessible
    assert client.get(f"/api/v1/tax-rules/{rule_id}").status_code == 200

    # Update archived rule blocked
    assert client.patch(f"/api/v1/tax-rules/{rule_id}", json={"name": "Updated"}).status_code == 409

    # Restore via restore endpoint
    restore_res = client.post(f"/api/v1/tax-rules/{rule_id}/restore")
    assert restore_res.status_code == 200
    assert restore_res.json()["isActive"] is True

    # Re-archive
    client.post(f"/api/v1/tax-rules/{rule_id}/archive")

    # Restore via PATCH
    patch_restore = client.patch(f"/api/v1/tax-rules/{rule_id}", json={"isActive": True})
    assert patch_restore.status_code == 200
    assert patch_restore.json()["isActive"] is True


# ---------------------------------------------------------
# Rate Validation & Decimal Precision
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "valid_rate",
    ["0.00", "0", "5", "5.5", "18.00", "12.3456", "100.00"],
)
def test_valid_tax_rates(client, valid_rate):
    rule = create_test_tax_rule(client, code=f"RATE_{valid_rate.replace('.', '_')}", ratePercent=valid_rate)
    assert float(rule["ratePercent"]) == pytest.approx(float(valid_rate), rel=1e-3)


@pytest.mark.parametrize(
    "invalid_rate",
    ["-0.01", "100.01", "150", "abc", "12.34567"],
)
def test_rejects_invalid_tax_rates(client, invalid_rate):
    res = client.post("/api/v1/tax-rules", json=tax_payload(ratePercent=invalid_rate))
    assert res.status_code == 422


def test_rejects_invalid_tax_type(client):
    res = client.post("/api/v1/tax-rules", json=tax_payload(taxType="INVALID_TYPE"))
    assert res.status_code == 422


# ---------------------------------------------------------
# Duplicate Tax Code Rejection
# ---------------------------------------------------------

def test_duplicate_tax_code_rejected(client):
    create_test_tax_rule(client, code="GST_STANDARD")

    # Duplicate on create
    dup_res = client.post("/api/v1/tax-rules", json=tax_payload(code="  gst_standard  "))
    assert dup_res.status_code == 409

    # Duplicate on patch
    rule2 = create_test_tax_rule(client, code="GST_REDUCED")
    patch_dup = client.patch(f"/api/v1/tax-rules/{rule2['id']}", json={"code": "gst_standard"})
    assert patch_dup.status_code == 409


# ---------------------------------------------------------
# Permissions
# ---------------------------------------------------------

def test_tax_role_permissions(client, role_users, auth_as):
    rule = create_test_tax_rule(client)
    rule_id = rule["id"]

    # Staff can manage taxes
    auth_as(role_users["staff"])
    assert client.get("/api/v1/tax-rules").status_code == 200
    assert client.get(f"/api/v1/tax-rules/{rule_id}").status_code == 200
    assert client.post("/api/v1/tax-rules", json=tax_payload(code="STAFF_TAX")).status_code == 201
    assert client.patch(f"/api/v1/tax-rules/{rule_id}", json={"name": "Staff Named"}).status_code == 200
    assert client.post(f"/api/v1/tax-rules/{rule_id}/archive").status_code == 204
    assert client.post(f"/api/v1/tax-rules/{rule_id}/restore").status_code == 200

    # Customer is strictly forbidden
    auth_as(role_users["customer"])
    assert client.get("/api/v1/tax-rules").status_code == 403
    assert client.get(f"/api/v1/tax-rules/{rule_id}").status_code == 403
    assert client.post("/api/v1/tax-rules", json=tax_payload(code="CUST_TAX")).status_code == 403
    assert client.patch(f"/api/v1/tax-rules/{rule_id}", json={"name": "Nope"}).status_code == 403
    assert client.post(f"/api/v1/tax-rules/{rule_id}/archive").status_code == 403
    assert client.post(f"/api/v1/tax-rules/{rule_id}/restore").status_code == 403


# ---------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------

def test_tax_not_found_and_invalid_uuid(client):
    nonexistent = str(uuid4())
    assert client.get(f"/api/v1/tax-rules/{nonexistent}").status_code == 404
    assert client.patch(f"/api/v1/tax-rules/{nonexistent}", json={"name": "Test"}).status_code == 404
    assert client.post(f"/api/v1/tax-rules/{nonexistent}/archive").status_code == 404
    assert client.post(f"/api/v1/tax-rules/{nonexistent}/restore").status_code == 404

    assert client.get("/api/v1/tax-rules/not-a-valid-uuid").status_code == 422


@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 0}, {"pageSize": 101}])
def test_invalid_tax_pagination(client, params):
    assert client.get("/api/v1/tax-rules", params=params).status_code == 422
