from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
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

    id = Column(String(36), primary_key=True, index=True)
    file_id = Column(String(36), ForeignKey("files.id"), nullable=False)
    task_type = Column(String(50), default="verify")  # verify, re_verify, etc.
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)

    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(255))
    error_message = Column(Text)

    # Celery task ID
    celery_task_id = Column(String(255), index=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Result
    result = Column(Text)  # JSON string

    # Relationships
    file = relationship("File", back_populates="tasks")
