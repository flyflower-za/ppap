from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.core.database import Base
import enum
import uuid

class RuleType(str, enum.Enum):
    keyword = "keyword"
    regex = "regex"
    llm_prompt = "llm_prompt"
    plugin = "plugin"
    logic_graph = "logic_graph"

class Severity(str, enum.Enum):
    warning = "warning"
    fail = "fail"
    reference = "reference"  # Advisory check: runs and reports, but does NOT count toward the score

class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    keywords = Column(JSONB, default=list, nullable=False)  # List of strings
    is_active = Column(Boolean, default=True)

    rules = relationship("VerificationRule", back_populates="category", cascade="all, delete-orphan")

class VerificationRule(Base):
    __tablename__ = "verification_rules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(UUID(as_uuid=False), ForeignKey("document_categories.id"), nullable=True) # Null = global rule
    rule_name = Column(String, nullable=False)
    rule_type = Column(Enum(RuleType), default=RuleType.llm_prompt)
    rule_content = Column(Text, nullable=False)
    severity = Column(Enum(Severity), default=Severity.fail)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False, nullable=False) # True for built-in rules
    logic_config = Column(JSONB, default=dict) # Stores node graph connections / AST

    category = relationship("DocumentCategory", back_populates="rules")
