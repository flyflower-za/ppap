from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
import uuid

from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False) # e.g., 'LOGIN', 'CREATE_RULE', 'VERIFY_DOCUMENT'
    resource_type = Column(String, nullable=True) # e.g., 'RULE', 'DOCUMENT', 'SYSTEM'
    resource_id = Column(String, nullable=True)
    details = Column(JSONB, default=dict) # JSON payload of changes or results
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="audit_logs")
