from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import Product, ProductVariant
from app.modules.products.pricing import calculate_unit_price


def product_payload(**overrides):
    payload = {
        "name": "Business Suite",
        "type": "SOFTWARE",
        "salesPrice": "1000.00",
        "costPrice": "450.00",
        "currency": "inr",
        "notes": "Core subscription product",
        "variants": [
            {"attributeName": "Brand", "attributeValue": "Odoo", "priceAdjustment": "560.00"},
            {"attributeName": "Storage", "attributeValue": "Premium", "priceAdjustment": "300.00"},
        ],
    }
    payload.update(overrides)
    return payload


def create_product(client, **overrides):
    response = client.post("/api/v1/products", json=product_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_product_with_variants(client):
    product = create_product(client)
    assert product["currency"] == "INR"
    assert product["salesPrice"] == "1000.00"
    assert product["costPrice"] == "450.00"
    assert "sales_price" not in product
    assert len(product["variants"]) == 2
    assert {variant["attributeValue"] for variant in product["variants"]} == {"Odoo", "Premium"}


def test_list_search_and_pagination(client):
    create_product(client, name="Business Analytics", variants=[])
    create_product(client, name="Support Service", type="SERVICE", variants=[])

    response = client.get("/api/v1/products", params={"search": "analytics", "page": 1, "pageSize": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["pageSize"] == 1
    assert body["items"][0]["name"] == "Business Analytics"


def test_product_detail_and_update_variants(client):
    product = create_product(client)
    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={
            "name": "Business Suite Plus",
            "variants": [{"attributeName": "Brand", "attributeValue": "Odoo", "priceAdjustment": "600.00"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Business Suite Plus"
    variants = {variant["attributeValue"]: variant for variant in body["variants"]}
    assert variants["Odoo"]["priceAdjustment"] == "600.00"
    assert variants["Premium"]["isActive"] is False

    detail = client.get(f"/api/v1/products/{product['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == product["id"]


def test_archive_hides_product_and_prevents_update(client):
    product = create_product(client)
    assert client.post(f"/api/v1/products/{product['id']}/archive").status_code == 204
    assert client.get("/api/v1/products").json()["total"] == 0
    assert client.get("/api/v1/products", params={"isActive": False}).json()["total"] == 1
    assert client.patch(f"/api/v1/products/{product['id']}", json={"name": "Nope"}).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"salesPrice": "-0.01"},
        {"costPrice": 450},
        {"salesPrice": "1.234"},
        {"currency": "RUPEE"},
        {"name": "   "},
    ],
)
def test_rejects_invalid_product_values(client, changes):
    assert client.post("/api/v1/products", json=product_payload(**changes)).status_code == 422


def test_rejects_duplicate_variant_configuration(client):
    response = client.post(
        "/api/v1/products",
        json=product_payload(
            variants=[
                {"attributeName": "Brand", "attributeValue": "Odoo", "priceAdjustment": "560.00"},
                {"attributeName": " brand ", "attributeValue": "odoo", "priceAdjustment": "600.00"},
            ]
        ),
    )
    assert response.status_code == 422


def test_additive_variant_pricing_and_invalid_selection(db_session):
    product = Product(name="Suite", type="SOFTWARE", sales_price=Decimal("1000.00"), cost_price=Decimal("1.00"), currency="INR")
    odoo = ProductVariant(attribute_name="Brand", attribute_value="Odoo", price_adjustment=Decimal("560.00"))
    storage = ProductVariant(attribute_name="Storage", attribute_value="Premium", price_adjustment=Decimal("300.00"))
    product.variants.extend([odoo, storage])
    db_session.add(product)
    db_session.commit()
    assert calculate_unit_price(product, [odoo.id, storage.id]) == Decimal("1860.00")
    with pytest.raises(HTTPException) as unmatched:
        calculate_unit_price(product, [uuid4()])
    assert unmatched.value.status_code == 422
    with pytest.raises(HTTPException) as duplicate:
        calculate_unit_price(product, [odoo.id, odoo.id])
    assert duplicate.value.status_code == 422


def test_staff_can_manage_products_and_customer_is_forbidden(client, role_users, auth_as):
    product = create_product(client, variants=[])
    auth_as(role_users["staff"])
    staff_detail = client.get(f"/api/v1/products/{product['id']}")
    assert staff_detail.status_code == 200
    assert "costPrice" not in staff_detail.json()
    assert client.patch(f"/api/v1/products/{product['id']}", json={"notes": "Updated"}).status_code == 200

    assert client.post("/api/v1/products", json=product_payload()).status_code == 403
    assert client.patch(f"/api/v1/products/{product['id']}", json={"costPrice": "1.00"}).status_code == 403

    auth_as(role_users["customer"])
    assert client.post("/api/v1/products", json=product_payload()).status_code == 403
    assert client.get("/api/v1/products").status_code == 403
    assert client.get(f"/api/v1/products/{product['id']}").status_code == 403
    assert client.patch(f"/api/v1/products/{product['id']}", json={"notes": "Nope"}).status_code == 403
    assert client.post(f"/api/v1/products/{product['id']}/archive").status_code == 403


@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 0}, {"pageSize": 101}])
def test_invalid_product_pagination(client, params):
    assert client.get("/api/v1/products", params=params).status_code == 422


def test_product_not_found_and_invalid_uuid(client):
    assert client.get("/api/v1/products/00000000-0000-0000-0000-000000000001").status_code == 404
    assert client.get("/api/v1/products/not-a-uuid").status_code == 422


def test_rejects_null_cost_price(client):
    assert client.post("/api/v1/products", json=product_payload(costPrice=None)).status_code == 422


def test_admin_can_update_cost_price(client):
    product = create_product(client, variants=[])
    response = client.patch(f"/api/v1/products/{product['id']}", json={"costPrice": "475.00"})
    assert response.status_code == 200
    assert response.json()["costPrice"] == "475.00"


def test_variant_patch_omission_empty_array_and_reactivation(client):
    product = create_product(client)
    product_id = product["id"]

    unchanged = client.patch(f"/api/v1/products/{product_id}", json={"notes": "No variant changes"})
    assert unchanged.status_code == 200
    assert all(variant["isActive"] for variant in unchanged.json()["variants"])

    archived = client.patch(f"/api/v1/products/{product_id}", json={"variants": []})
    assert archived.status_code == 200
    assert all(not variant["isActive"] for variant in archived.json()["variants"])

    reactivated = client.patch(
        f"/api/v1/products/{product_id}",
        json={"variants": [{"attributeName": "Brand", "attributeValue": "Odoo", "priceAdjustment": "560.00"}]},
    )
    assert reactivated.status_code == 200
    variants = {variant["attributeValue"]: variant for variant in reactivated.json()["variants"]}
    assert variants["Odoo"]["isActive"] is True
    assert variants["Premium"]["isActive"] is False
    assert len(variants) == 2


def test_database_rejects_case_insensitive_variant_duplicates(db_session):
    product = Product(name="Suite", type="SOFTWARE", sales_price=Decimal("1000.00"), cost_price=Decimal("1.00"), currency="INR")
    product.variants.append(ProductVariant(attribute_name="Brand", attribute_value="Odoo", price_adjustment=Decimal("1.00")))
    db_session.add(product)
    db_session.commit()
    duplicate = ProductVariant(product_id=product.id, attribute_name="brand", attribute_value="odoo", price_adjustment=Decimal("2.00"))
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_empty_product_patch_returns_400(client):
    product = create_product(client, variants=[])
    assert client.patch(f"/api/v1/products/{product['id']}", json={}).status_code == 400
