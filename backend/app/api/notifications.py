from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse,
    MarkReadRequest, NotificationTypeEnum,
)
from app.services.notification_service import NotificationService
from app.models.user import User
from app.api.deps import get_current_user
from sqlalchemy import func

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for current user."""
    service = NotificationService(db)

    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )

    # Get unread count
    unread_count = await service.get_unread_count(current_user.id)

    # Get total count
    from app.models.notification import Notification
    from sqlalchemy import select
    total_result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id
        )
    )
    total = total_result.scalar()

    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        items=[NotificationResponse.model_validate(n) for n in notifications],
    )


@router.post("/mark-read")
async def mark_as_read(
    request: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark notifications as read."""
    service = NotificationService(db)

    for notification_id in request.notification_ids:
        await service.mark_as_read(notification_id, current_user.id)

    return {"message": "Notifications marked as read"}


@router.post("/mark-all-read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)

    return {"message": f"Marked {count} notifications as read"}
