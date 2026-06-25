from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, Text, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.core.database import Base
from app.models.rule import RuleType, Severity
import uuid
from datetime import datetime

class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(UUID(as_uuid=False), ForeignKey("verification_rules.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    rule_name = Column(String, nullable=False)
    rule_type = Column(Enum(RuleType), nullable=False)
    rule_content = Column(Text, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    is_active = Column(Boolean, default=True)
    logic_config = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)  # Full name or email of editor

    # P3: Version management enhancements
    change_log = Column(Text, nullable=True)  # Description of what changed and why

    rule = relationship("VerificationRule")

