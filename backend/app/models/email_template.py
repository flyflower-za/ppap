"""
Email Template model
"""
from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime, timezone
from app.core.database import Base


class EmailTemplate(Base):
    """Email Template model for customizable email content."""

    __tablename__ = "email_templates"

    id = Column(String(100), primary_key=True)  # Template identifier
    name = Column(String(255), nullable=False)  # Human-readable name
    subject = Column(String(500), nullable=False)  # Email subject template
    html_content = Column(Text, nullable=False)  # HTML body template
    description = Column(Text)  # Template description
    variables = Column(Text)  # JSON array of available variables
    is_active = Column(String(10), default="true")  # Whether template is active
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
