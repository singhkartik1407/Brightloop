from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.notification import Notification, NotificationChannel, NotificationType
from app.modules.notifications.services import create_notification


def test_notification_creation_and_listing(client, role_users, db_session):
    customer = role_users["own_profile"]

    # Create 3 notifications
    n1 = create_notification(
        db=db_session,
        customer_id=customer.id,
        title="Notice 1",
        message="Message 1",
        notification_type=NotificationType.INVOICE_ISSUED.value,
    )
    n2 = create_notification(
        db=db_session,
        customer_id=customer.id,
        title="Notice 2",
        message="Message 2",
        notification_type=NotificationType.PAYMENT_RECEIVED.value,
    )
    n3 = create_notification(
        db=db_session,
        customer_id=customer.id,
        title="Notice 3",
        message="Message 3",
        notification_type=NotificationType.GENERAL.value,
    )
    db_session.commit()

    # Get unread count
    res_count = client.get("/api/v1/notifications/unread-count")
    assert res_count.status_code == 200
    assert res_count.json()["unreadCount"] >= 3

    # List notifications
    res_list = client.get("/api/v1/notifications")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 3
    notif_ids = [item["id"] for item in data["items"]]
    assert str(n1.id) in notif_ids
    assert str(n2.id) in notif_ids
    assert str(n3.id) in notif_ids


def test_mark_notification_as_read(client, role_users, db_session):
    customer = role_users["own_profile"]
    n = create_notification(
        db=db_session,
        customer_id=customer.id,
        title="Payment Confirmed",
        message="Payment has settled successfully.",
        notification_type=NotificationType.PAYMENT_RECEIVED.value,
    )
    db_session.commit()

    # Mark as read
    res = client.post(f"/api/v1/notifications/{n.id}/read")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(n.id)
    assert body["isRead"] is True
    assert body["status"] == "READ"
    assert body["readAt"] is not None


def test_mark_all_notifications_as_read(client, role_users, db_session, auth_as):
    customer = role_users["own_profile"]
    for i in range(4):
        create_notification(
            db=db_session,
            customer_id=customer.id,
            title=f"Alert {i}",
            message=f"Message {i}",
        )
    db_session.commit()

    # Switch to customer
    auth_as(role_users["customer"])

    # Ensure unread count >= 4
    count_before = client.get("/api/v1/notifications/unread-count").json()["unreadCount"]
    assert count_before >= 4

    # Mark all read
    mark_res = client.post("/api/v1/notifications/read-all")
    assert mark_res.status_code == 200
    assert mark_res.json()["count"] >= 4

    # Unread count should now be 0
    count_after = client.get("/api/v1/notifications/unread-count").json()["unreadCount"]
    assert count_after == 0


def test_notification_customer_isolation(client, role_users, db_session, auth_as):
    own_customer = role_users["own_profile"]
    other_customer = role_users["other_profile"]

    other_n = create_notification(
        db=db_session,
        customer_id=other_customer.id,
        title="Secret Notification",
        message="Confidential to other customer.",
    )
    db_session.commit()

    # Switch to customer
    auth_as(role_users["customer"])

    # Cannot view other's notification in list
    items = client.get("/api/v1/notifications").json()["items"]
    assert not any(item["id"] == str(other_n.id) for item in items)

    # Cannot mark other's notification as read -> 404
    forbidden_res = client.post(f"/api/v1/notifications/{other_n.id}/read")
    assert forbidden_res.status_code == 404
