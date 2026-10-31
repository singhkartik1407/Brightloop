
# --------------------------------
# STAFF CAN MANAGE CUSTOMERS
# --------------------------------

def test_staff_can_manage_customers(
    client, role_users, auth_as
):

    auth_as(role_users["staff"])

    response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Staff Created Customer",
            "billing_email": "staff.created@example.com"
        }
    )

    assert response.status_code == 201

    customer_id = response.json()["id"]

    assert client.get(
        "/api/v1/customers"
    ).status_code == 200

    assert client.get(
        f"/api/v1/customers/{customer_id}"
    ).status_code == 200

    assert client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"company_name": "Staff Updated Company"}
    ).status_code == 200

    assert client.delete(
        f"/api/v1/customers/{customer_id}"
    ).status_code == 204

    assert client.post(
        f"/api/v1/customers/{customer_id}/restore"
    ).status_code == 200


# --------------------------------
# CUSTOMER CANNOT USE ADMIN APIs
# --------------------------------

def test_customer_cannot_manage_customers(
    client, role_users, auth_as
):

    auth_as(role_users["customer"])

    customer_id = role_users["own_profile"].id

    payload = {
        "display_name": "Unauthorized Customer",
        "billing_email": "unauthorized@example.com"
    }

    assert client.post(
        "/api/v1/customers",
        json=payload
    ).status_code == 403

    assert client.get(
        "/api/v1/customers"
    ).status_code == 403

    assert client.get(
        f"/api/v1/customers/{customer_id}"
    ).status_code == 403

    assert client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"display_name": "Unauthorized Update"}
    ).status_code == 403

    assert client.delete(
        f"/api/v1/customers/{customer_id}"
    ).status_code == 403

    assert client.post(
        f"/api/v1/customers/{customer_id}/restore"
    ).status_code == 403


# --------------------------------
# CUSTOMER CAN ACCESS OWN PROFILE
# --------------------------------

def test_customer_can_access_own_profile(
    client, role_users, auth_as
):

    auth_as(role_users["customer"])

    response = client.get("/api/v1/customers/me")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(role_users["own_profile"].id)

    # Internal fields must not be exposed.
    assert "notes" not in data
    assert "user_id" not in data


# --------------------------------
# CUSTOMER CAN UPDATE OWN PROFILE
# --------------------------------

def test_customer_can_update_own_profile(
    client, role_users, auth_as
):

    auth_as(role_users["customer"])

    response = client.patch(
        "/api/v1/customers/me",
        json={
            "display_name": "My Updated Profile",
            "phone": "+919876543210"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["display_name"] == "My Updated Profile"
    assert data["phone"] == "+919876543210"


# --------------------------------
# CUSTOMER CANNOT ACCESS OTHER PROFILE
# --------------------------------

def test_customer_cannot_access_other_profile(
    client, role_users, auth_as
):

    auth_as(role_users["customer"])

    other_id = role_users["other_profile"].id

    response = client.get(
        f"/api/v1/customers/{other_id}"
    )

    assert response.status_code == 403

    response = client.patch(
        f"/api/v1/customers/{other_id}",
        json={"display_name": "Unauthorized"}
    )

    assert response.status_code == 403


# --------------------------------
# CUSTOMER WITHOUT LINKED PROFILE
# --------------------------------

def test_unlinked_customer_gets_404(
    client, role_users, auth_as
):

    auth_as(role_users["unlinked_customer"])

    response = client.get("/api/v1/customers/me")

    assert response.status_code == 404
