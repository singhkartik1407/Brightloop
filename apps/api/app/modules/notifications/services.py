from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.user import User, UserRole
from app.modules.invoices.services import get_user_customer_id
from app.modules.notifications.schemas import NotificationResponse


def serialize_notification(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id,
        customer_id=item.customer_id,
        channel=NotificationChannel(item.channel),
        notification_type=NotificationType(item.notification_type),
        title=item.title,
        message=item.message,
        related_entity_type=item.related_entity_type,
        related_entity_id=item.related_entity_id,
        status=NotificationStatus(item.status),
        is_read=item.is_read,
        read_at=item.read_at,
        created_at=item.created_at,
    )


def create_notification(
    db: Session,
    title: str,
    message: str,
    notification_type: str = NotificationType.GENERAL.value,
    customer_id: uuid.UUID | None = None,
    recipient_email: str | None = None,
    channel: str = NotificationChannel.IN_APP.value,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> Notification:
    notif = Notification(
        customer_id=customer_id,
        recipient_email=recipient_email,
        channel=channel,
        notification_type=notification_type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        status=NotificationStatus.SENT.value if channel == NotificationChannel.IN_APP.value else NotificationStatus.PENDING.value,
    )
    db.add(notif)
    db.flush()
    return notif


def list_user_notifications(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool | None = None,
) -> tuple[list[Notification], int]:
    query = select(Notification)

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id:
            return [], 0
        query = query.where(Notification.customer_id == cust_id)

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = (
        db.scalars(
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return list(items), total


def get_user_unread_count(db: Session, current_user: User) -> int:
    query = select(func.count(Notification.id)).where(Notification.is_read.is_(False))

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id:
            return 0
        query = query.where(Notification.customer_id == cust_id)

    return db.scalar(query) or 0


def mark_notification_as_read(
    db: Session,
    notification_id: uuid.UUID,
    current_user: User,
) -> Notification:
    item = db.get(Notification, notification_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found"},
        )

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id or cust_id != item.customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found"},
            )

    item.is_read = True
    item.read_at = datetime.now(timezone.utc)
    item.status = NotificationStatus.READ.value
    db.commit()
    db.refresh(item)
    return item


def mark_all_user_notifications_as_read(
    db: Session,
    current_user: User,
) -> int:
    now_utc = datetime.now(timezone.utc)
    stmt = (
        update(Notification)
        .where(Notification.is_read.is_(False))
        .values(
            is_read=True,
            read_at=now_utc,
            status=NotificationStatus.READ.value,
        )
    )

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id:
            return 0
        stmt = stmt.where(Notification.customer_id == cust_id)

    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
