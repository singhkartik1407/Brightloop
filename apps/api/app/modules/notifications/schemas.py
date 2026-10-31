from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    customer_id: uuid.UUID | None = Field(
        default=None, validation_alias="customer_id", serialization_alias="customerId"
    )
    channel: NotificationChannel
    notification_type: NotificationType = Field(
        validation_alias="notification_type", serialization_alias="notificationType"
    )
    title: str
    message: str
    related_entity_type: str | None = Field(
        default=None,
        validation_alias="related_entity_type",
        serialization_alias="relatedEntityType",
    )
    related_entity_id: uuid.UUID | None = Field(
        default=None,
        validation_alias="related_entity_id",
        serialization_alias="relatedEntityId",
    )
    status: NotificationStatus
    is_read: bool = Field(
        validation_alias="is_read", serialization_alias="isRead"
    )
    read_at: datetime | None = Field(
        default=None, validation_alias="read_at", serialization_alias="readAt"
    )
    created_at: datetime = Field(
        validation_alias="created_at", serialization_alias="createdAt"
    )


class UnreadCountResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    unread_count: int = Field(
        validation_alias="unread_count", serialization_alias="unreadCount"
    )
