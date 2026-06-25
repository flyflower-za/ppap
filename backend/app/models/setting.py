from sqlalchemy import Column, String, DateTime
from datetime import datetime, timezone
from app.core.database import Base

class Setting(Base):
    """Setting model for persistent key-value configuration."""

    __tablename__ = "settings"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(String(4000), nullable=False)  # JSON or simple string
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
