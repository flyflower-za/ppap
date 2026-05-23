from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Note(Base):
    """Notes/Comments for file verification review."""

    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, index=True)
    file_id = Column(String(36), ForeignKey("files.id"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    file = relationship("File", back_populates="notes")
    author = relationship("User", back_populates="notes")
