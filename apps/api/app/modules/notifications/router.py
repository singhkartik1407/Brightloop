from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.notifications.schemas import (
    NotificationResponse,
    UnreadCountResponse,
)
from app.modules.notifications.services import (
    get_user_unread_count,
    list_user_notifications,
    mark_all_user_notifications_as_read,
    mark_notification_as_read,
    serialize_notification,
)


router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=dict[str, Any])
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    unread_only: bool | None = Query(None, alias="unreadOnly"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items, total = list_user_notifications(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return {
        "items": [serialize_notification(item).model_dump(by_alias=True) for item in items],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    count = get_user_unread_count(db, current_user)
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    item = mark_notification_as_read(db, notification_id, current_user)
    return serialize_notification(item)


@router.post("/read-all", response_model=dict[str, Any])
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    count = mark_all_user_notifications_as_read(db, current_user)
    return {"message": "All notifications marked as read.", "count": count}
