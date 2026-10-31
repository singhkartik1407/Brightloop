
import pytest


# --------------------------------
# INVALID CUSTOMER INPUT
# --------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {
            "display_name": "",
            "billing_email": "valid@example.com"
        },
        {
            "display_name": "   ",
            "billing_email": "valid@example.com"
        },
        {
            "display_name": "Valid Customer",
            "billing_email": "invalid-email"
        },
        {
            "display_name": "Valid Customer",
            "billing_email": "valid@example.com",
            "billing_country_code": "IND"
        }
    ]
)
def test_invalid_customer_creation(client, payload):

    response = client.post(
        "/api/v1/customers",
        json=payload
    )

    assert response.status_code == 422


# --------------------------------
# FORBIDDEN FIELDS
# --------------------------------

def test_customer_creation_rejects_extra_fields(client):

    response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Test Customer",
            "billing_email": "test@example.com",
            "is_active": False,
            "user_id": None
        }
    )

    assert response.status_code == 422


# --------------------------------
# INVALID UPDATE VALUES
# --------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": None},
        {"display_name": "   "},
        {"billing_email": None},
        {"billing_email": "invalid-email"}
    ]
)
def test_invalid_customer_updates(
    client, make_customer, payload
):

    customer = make_customer()

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json=payload
    )

    assert response.status_code == 422


# --------------------------------
# CUSTOMERS CANNOT CHANGE INTERNAL FIELDS
# --------------------------------

def test_update_rejects_internal_fields(
    client, make_customer
):

    customer = make_customer()

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"is_active": False}
    )

    assert response.status_code == 422


# --------------------------------
# INVALID PAGINATION
# --------------------------------

@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 101}
    ]
)
def test_invalid_pagination(client, params):

    response = client.get(
        "/api/v1/customers",
        params=params
    )

    assert response.status_code == 422


# --------------------------------
# EMPTY UPDATE
# --------------------------------

def test_empty_customer_update(client, make_customer):

    customer = make_customer()

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={}
    )

    assert response.status_code == 400


# --------------------------------
# CUSTOMER SELF-UPDATE FORBIDDEN FIELDS
# --------------------------------

def test_self_update_rejects_internal_fields(
    client, role_users, auth_as
):

    auth_as(role_users["customer"])

    response = client.patch(
        "/api/v1/customers/me",
        json={
            "display_name": "Updated Name",
            "notes": "Unauthorized internal note"
        }
    )

    assert response.status_code == 422
