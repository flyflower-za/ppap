from sqlalchemy import Column, String, DateTime, ForeignKey, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


# User-Group association table (many-to-many)
user_group_association = Table(
    'user_group_members',
    Base.metadata,
    Column('user_id', UUID(as_uuid=False), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', String(255), ForeignKey('user_groups.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.utcnow)
)


class UserGroup(Base):
    """User Permission Group model for LDAP/SSO group mapping"""

    __tablename__ = "user_groups"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)

    # LDAP Group DN for automatic role assignment
    ldap_group_dn = Column(String(1000))

    # Role assigned to users in this group
    role = Column(String(50), nullable=False, default="USER")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("User", secondary=user_group_association, back_populates="groups")
