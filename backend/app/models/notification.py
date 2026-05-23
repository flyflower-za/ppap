from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from app.core.database import Base


class NotificationType(str, enum.Enum):
    """Notification type categories."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Notification(Base):
    """User notification model."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotificationType, native_enum=False), default=NotificationType.INFO)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    link = Column(String(500))  # Optional link to related resource

    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
