from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.core.database import Base

class Setting(Base):
    """Setting model for persistent key-value configuration."""

    __tablename__ = "settings"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(String(4000), nullable=False)  # JSON or simple string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
