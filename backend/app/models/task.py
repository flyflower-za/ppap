from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid
from app.core.database import Base


class TaskStatus(str, enum.Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """Background task model for file verification."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(UUID(as_uuid=False), ForeignKey("files.id"), nullable=False)
    task_type = Column(String(50), default="verify")  # verify, re_verify, etc.
    status = Column(Enum(TaskStatus, native_enum=False), default=TaskStatus.PENDING, index=True)

    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(255))
    error_message = Column(Text)

    # Celery task ID
    celery_task_id = Column(String(255), index=True)

    # Timing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Result
    result = Column(Text)  # JSON string

    # Relationships
    file = relationship("File", back_populates="tasks")
