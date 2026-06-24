from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base

# Import UserGroup at the end to avoid circular import
# Will be imported after UserGroup definition


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(255))
    avatar_url = Column(String(500))

    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_admin = Column(Boolean, default=False)  # Deprecated, use role instead (kept for compatibility)

    # Authentication
    password_hash = Column(String(255), nullable=True)  # NULL for SSO/LDAP-only users

    # SSO / LDAP fields
    sso_provider = Column(String(50))
    sso_id = Column(String(255), index=True)
    ldap_dn = Column(String(500))
    ad_groups = Column(String(1000))  # Comma-separated list of AD group DNs

    # Status
    is_active = Column(Boolean, default=True)

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
    groups = relationship("UserGroup", secondary="user_group_members", back_populates="members")
