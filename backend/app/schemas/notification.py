from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class NotificationTypeEnum(str, Enum):
    """Notification type enum for API."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class NotificationResponse(BaseModel):
    """Notification response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: NotificationTypeEnum
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Notification list response."""
    total: int
    unread_count: int
    items: List[NotificationResponse]


class MarkReadRequest(BaseModel):
    """Mark notification as read request."""
    notification_ids: List[str]


class NotificationCreate(BaseModel):
    """Create notification (internal use)."""
    user_id: str
    type: NotificationTypeEnum
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
