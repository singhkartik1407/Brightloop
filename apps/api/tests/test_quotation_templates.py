import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.customer import Customer
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.tax import TaxRule, TaxType


def create_test_product_and_variants(db_session, name="Cloud Server"):
    prod = Product(
        name=name,
        type="SOFTWARE",
        sales_price="100.00",
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
    v2 = ProductVariant(
        attribute_name="Storage",
        attribute_value="512GB",
        price_adjustment="30.00",
        is_active=True,
    )
    prod.variants.extend([v1, v2])
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod, v1, v2


def create_test_plan(db_session, name="Monthly Plan", price="50.00", product_id=None):
    plan = Plan(
        name=name,
        price=price,
        currency="INR",
        billing_interval="MONTHLY",
        interval_count=1,
        min_quantity=1,
        product_id=product_id,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def create_test_tax_rule(db_session, name="GST 18%", code="GST18", rate="18.00"):
    tax = TaxRule(
        name=name,
        code=code,
        tax_type=TaxType.GENERIC.value,
        rate_percent=rate,
        is_inclusive=False,
        is_active=True,
    )
    db_session.add(tax)
    db_session.commit()
    db_session.refresh(tax)
    return tax


def test_create_quote_template_success(client: TestClient, db_session):
    product, v1, v2 = create_test_product_and_variants(db_session, "Template Product")
    plan = create_test_plan(db_session, "Template Plan")
    tax = create_test_tax_rule(db_session)

    payload = {
        "name": "Standard Enterprise Template",
        "validityDays": 14,
        "planId": str(plan.id),
        "lines": [
            {
                "productId": str(product.id),
                "quantity": 2,
                "selectedVariantIds": [str(v1.id), str(v2.id)],
                "taxRuleIds": [str(tax.id)],
            }
        ],
    }

    res = client.post("/api/v1/quote-templates", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Standard Enterprise Template"
    assert data["validityDays"] == 14
    assert data["planId"] == str(plan.id)
    assert data["isActive"] is True
    assert len(data["lines"]) == 1
    assert data["lines"][0]["productId"] == str(product.id)
    assert data["lines"][0]["quantity"] == 2
    assert len(data["lines"][0]["selectedVariantIds"]) == 2
    assert len(data["lines"][0]["taxRuleIds"]) == 1


def test_list_and_search_quote_templates(client: TestClient, db_session):
    product, _, _ = create_test_product_and_variants(db_session, "P1")
    plan = create_test_plan(db_session, "Plan L")

    for i in range(5):
        client.post(
            "/api/v1/quote-templates",
            json={
                "name": f"Alpha Template {i}",
                "validityDays": 30,
                "planId": str(plan.id),
                "lines": [{"productId": str(product.id), "quantity": 1, "selectedVariantIds": []}],
            },
        )

    client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Beta Special Template",
            "validityDays": 15,
            "planId": str(plan.id),
            "lines": [{"productId": str(product.id), "quantity": 1, "selectedVariantIds": []}],
        },
    )

    # Search
    res = client.get("/api/v1/quote-templates?search=Special")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Beta Special Template"

    # Pagination
    res_page = client.get("/api/v1/quote-templates?page=1&pageSize=3")
    assert res_page.status_code == 200
    p_data = res_page.json()
    assert len(p_data["items"]) == 3
    assert p_data["total"] == 6


def test_quote_template_detail_and_update(client: TestClient, db_session):
    product, v1, _ = create_test_product_and_variants(db_session, "P-Detail")
    plan1 = create_test_plan(db_session, "Plan 1")
    plan2 = create_test_plan(db_session, "Plan 2")

    res = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Original Name",
            "validityDays": 30,
            "planId": str(plan1.id),
            "lines": [{"productId": str(product.id), "quantity": 1, "selectedVariantIds": [str(v1.id)]}],
        },
    )
    t_id = res.json()["id"]

    # Detail
    res_get = client.get(f"/api/v1/quote-templates/{t_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Original Name"

    # Patch
    res_patch = client.patch(
        f"/api/v1/quote-templates/{t_id}",
        json={"name": "Updated Name", "validityDays": 45, "planId": str(plan2.id)},
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert updated["name"] == "Updated Name"
    assert updated["validityDays"] == 45
    assert updated["planId"] == str(plan2.id)

    # Empty patch
    res_empty = client.patch(f"/api/v1/quote-templates/{t_id}", json={})
    assert res_empty.status_code == 400


def test_quote_template_archive_and_restore(client: TestClient, db_session):
    product, _, _ = create_test_product_and_variants(db_session, "P-Arch")
    plan = create_test_plan(db_session, "Plan-Arch")

    res = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Template to Archive",
            "validityDays": 10,
            "planId": str(plan.id),
            "lines": [{"productId": str(product.id), "quantity": 1}],
        },
    )
    t_id = res.json()["id"]

    # Archive
    res_arch = client.post(f"/api/v1/quote-templates/{t_id}/archive")
    assert res_arch.status_code == 204

    # Verify detail shows isActive = False
    res_detail = client.get(f"/api/v1/quote-templates/{t_id}")
    assert res_detail.json()["isActive"] is False

    # Restore
    res_rest = client.post(f"/api/v1/quote-templates/{t_id}/restore")
    assert res_rest.status_code == 200
    assert res_rest.json()["isActive"] is True


def test_quote_template_validations(client: TestClient, db_session):
    product, v1, _ = create_test_product_and_variants(db_session, "P-Val")
    product2, v2_other, _ = create_test_product_and_variants(db_session, "P-Val2")
    plan = create_test_plan(db_session, "Plan-Val")

    # Inactive/missing plan
    fake_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Invalid Plan",
            "validityDays": 10,
            "planId": fake_id,
            "lines": [{"productId": str(product.id), "quantity": 1}],
        },
    )
    assert res.status_code == 400

    # Cross-product variant assignment
    res_var = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Cross Variant",
            "validityDays": 10,
            "planId": str(plan.id),
            "lines": [{"productId": str(product.id), "quantity": 1, "selectedVariantIds": [str(v2_other.id)]}],
        },
    )
    assert res_var.status_code == 400

    # Missing/empty lines
    res_empty_lines = client.post(
        "/api/v1/quote-templates",
        json={
            "name": "Empty Lines",
            "validityDays": 10,
            "planId": str(plan.id),
            "lines": [],
        },
    )
    assert res_empty_lines.status_code == 422


def test_quote_template_role_permissions(
    client: TestClient,
    role_users: dict,
    auth_as,
    db_session,
):
    product, _, _ = create_test_product_and_variants(db_session, "P-Perm")
    plan = create_test_plan(db_session, "Plan-Perm")

    payload = {
        "name": "Permissions Template",
        "validityDays": 14,
        "planId": str(plan.id),
        "lines": [{"productId": str(product.id), "quantity": 1}],
    }

    # Staff cannot create
    auth_as(role_users["staff"])
    res_staff_create = client.post("/api/v1/quote-templates", json=payload)
    assert res_staff_create.status_code == 403

    # Customer cannot create
    auth_as(role_users["customer"])
    res_cust_create = client.post("/api/v1/quote-templates", json=payload)
    assert res_cust_create.status_code == 403

    # Admin creates
    auth_as(role_users["admin"])
    res_admin = client.post("/api/v1/quote-templates", json=payload)
    assert res_admin.status_code == 201
    t_id = res_admin.json()["id"]

    # Staff can list and get
    auth_as(role_users["staff"])
    res_staff_list = client.get("/api/v1/quote-templates")
    assert res_staff_list.status_code == 200
    res_staff_get = client.get(f"/api/v1/quote-templates/{t_id}")
    assert res_staff_get.status_code == 200

    # Customer cannot list or get
    auth_as(role_users["customer"])
    res_cust_list = client.get("/api/v1/quote-templates")
    assert res_cust_list.status_code == 403
    res_cust_get = client.get(f"/api/v1/quote-templates/{t_id}")
    assert res_cust_get.status_code == 403
