from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(255))
    avatar_url = Column(String(500))

    # SSO / LDAP fields
    sso_provider = Column(String(50))
    sso_id = Column(String(255), index=True)
    ldap_dn = Column(String(500))

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Notification preferences
    email_notifications_enabled = Column(Boolean, default=True)
    notification_on_complete = Column(Boolean, default=True)
    notification_on_failure = Column(Boolean, default=True)
    daily_summary_enabled = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    files = relationship("File", back_populates="uploaded_by_user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="author", cascade="all, delete-orphan")
