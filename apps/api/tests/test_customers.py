
from uuid import UUID

from app.models import Customer


# --------------------------------
# CREATE CUSTOMER
# --------------------------------

def test_create_customer(client):

    payload = {
        "display_name": "Brightloop Test Customer",
        "company_name": "Brightloop Technologies",
        "billing_email": "test@example.com",
        "phone": "+919876543210",
        "billing_city": "Bengaluru",
        "billing_state": "Karnataka",
        "billing_country_code": "IN"
    }

    response = client.post(
        "/api/v1/customers",
        json=payload
    )

    assert response.status_code == 201

    data = response.json()

    assert data["display_name"] == payload["display_name"]
    assert data["billing_email"] == payload["billing_email"]
    assert data["company_name"] == payload["company_name"]
    assert data["user_id"] is None
    assert data["is_active"] is True
    assert UUID(data["id"])


# --------------------------------
# LIST CUSTOMERS
# --------------------------------

def test_list_customers(client, make_customer):

    make_customer(
        display_name="Customer One",
        billing_email="one@example.com"
    )

    make_customer(
        display_name="Customer Two",
        billing_email="two@example.com"
    )

    response = client.get("/api/v1/customers")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 20


# --------------------------------
# SEARCH CUSTOMERS
# --------------------------------

def test_search_customers(client, make_customer):

    make_customer(
        display_name="Alpha Customer",
        company_name="Alpha Technologies",
        billing_email="alpha@example.com"
    )

    make_customer(
        display_name="Beta Customer",
        company_name="Beta Technologies",
        billing_email="beta@example.com"
    )

    response = client.get(
        "/api/v1/customers",
        params={"q": "Alpha"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["display_name"] == "Alpha Customer"


# --------------------------------
# PAGINATION
# --------------------------------

def test_customer_pagination(client, make_customer):

    for i in range(5):
        make_customer(
            display_name=f"Customer {i}",
            billing_email=f"customer{i}@example.com"
        )

    page1 = client.get(
        "/api/v1/customers",
        params={"page": 1, "page_size": 2}
    )

    page2 = client.get(
        "/api/v1/customers",
        params={"page": 2, "page_size": 2}
    )

    assert page1.status_code == 200
    assert page2.status_code == 200

    assert page1.json()["total"] == 5
    assert page1.json()["pages"] == 3
    assert len(page1.json()["items"]) == 2
    assert len(page2.json()["items"]) == 2


# --------------------------------
# GET CUSTOMER DETAILS
# --------------------------------

def test_get_customer(client, make_customer):

    customer = make_customer(
        display_name="Detail Customer"
    )

    response = client.get(
        f"/api/v1/customers/{customer.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)
    assert response.json()["display_name"] == "Detail Customer"


# --------------------------------
# UPDATE CUSTOMER
# --------------------------------

def test_update_customer(client, make_customer):

    customer = make_customer(
        display_name="Old Customer Name"
    )

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={
            "display_name": "Updated Customer Name",
            "company_name": "Updated Company"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["display_name"] == "Updated Customer Name"
    assert data["company_name"] == "Updated Company"


# --------------------------------
# ARCHIVE CUSTOMER
# --------------------------------

def test_archive_customer(client, make_customer):

    customer = make_customer(
        display_name="Archive Customer"
    )

    response = client.delete(
        f"/api/v1/customers/{customer.id}"
    )

    assert response.status_code == 204

    # Archived customer should not appear in the default list.
    default_list = client.get("/api/v1/customers")

    assert default_list.json()["total"] == 0

    # It should appear when inactive records are included.
    all_customers = client.get(
        "/api/v1/customers",
        params={"include_inactive": True}
    )

    assert all_customers.status_code == 200
    assert all_customers.json()["total"] == 1
    assert all_customers.json()["items"][0]["is_active"] is False


# --------------------------------
# RESTORE CUSTOMER
# --------------------------------

def test_restore_customer(client, make_customer):

    customer = make_customer(
        display_name="Restore Customer",
        is_active=False
    )

    response = client.post(
        f"/api/v1/customers/{customer.id}/restore"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    active_list = client.get("/api/v1/customers")

    assert active_list.json()["total"] == 1


# --------------------------------
# NONEXISTENT CUSTOMER
# --------------------------------

def test_customer_not_found(client):

    customer_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(
        f"/api/v1/customers/{customer_id}"
    )

    assert response.status_code == 404


# --------------------------------
# INVALID UUID
# --------------------------------

def test_invalid_customer_uuid(client):

    response = client.get(
        "/api/v1/customers/not-a-valid-uuid"
    )

    assert response.status_code == 422
