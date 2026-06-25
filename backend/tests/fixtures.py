import uuid
from datetime import datetime, timezone
from app.models.user import User, UserRole

mock_normal_user = User(
    id=str(uuid.uuid4()),
    email="user@example.com",
    full_name="Normal User",
    is_active=True,
    is_admin=False,
    role=UserRole.USER,
    email_notifications_enabled=True,
    notification_on_complete=True,
    notification_on_failure=True,
    daily_summary_enabled=False,
    created_at=datetime.now(timezone.utc).replace(tzinfo=None)
)

mock_admin_user = User(
    id=str(uuid.uuid4()),
    email="admin@example.com",
    full_name="Admin User",
    is_active=True,
    is_admin=True,
    role=UserRole.ADMIN,
    email_notifications_enabled=True,
    notification_on_complete=True,
    notification_on_failure=True,
    daily_summary_enabled=False,
    created_at=datetime.now(timezone.utc).replace(tzinfo=None)
)
