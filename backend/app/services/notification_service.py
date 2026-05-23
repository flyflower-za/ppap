from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
import uuid

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationTypeEnum


class NotificationService:
    """Service for user notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: str,
        type: NotificationTypeEnum,
        title: str,
        message: Optional[str] = None,
        link: Optional[str] = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user."""
        query = select(func.count()).select_from(Notification).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = await self.db.execute(query)
        return result.scalar()

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        notification = await self.db.execute(
            select(Notification).where(
                and_(Notification.id == notification_id, Notification.user_id == user_id)
            )
        )
        notification = notification.scalar_one_or_none()

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        notifications = await self.db.execute(
            select(Notification).where(
                and_(Notification.user_id == user_id, Notification.is_read == False)
            )
        )
        notifications = notifications.scalars().all()

        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count

    async def delete_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        from sqlalchemy import delete, func

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Use delete directly for better performance
        stmt = delete(Notification).where(Notification.created_at < cutoff_date)
        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount


# Helper function to create common notifications
async def notify_verification_complete(
    db: AsyncSession,
    user_id: str,
    filename: str,
    status: str,
    file_id: str,
):
    """Create notification for verification completion."""
    service = NotificationService(db)

    if status == "completed":
        await service.create_notification(
            user_id=user_id,
            type=NotificationTypeEnum.SUCCESS,
            title="校验完成",
            message=f"{filename} 已完成校验",
            link=f"/files/{file_id}",
        )
    elif status == "failed":
        await service.create_notification(
            user_id=user_id,
            type=NotificationTypeEnum.ERROR,
            title="校验失败",
            message=f"{filename} 校验失败，请查看详情",
            link=f"/files/{file_id}",
        )


from sqlalchemy import func, delete
from datetime import timedelta
