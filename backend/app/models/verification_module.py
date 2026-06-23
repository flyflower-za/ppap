from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.core.database import Base
import enum
import uuid


class ModuleType(str, enum.Enum):
    """Verification module types corresponding to available operators"""
    qr_scanner = "qr_scanner"
    signature_verifier = "signature_verifier"
    pdf_info = "pdf_info"
    institution_sniffer = "institution_sniffer"
    revision_check = "revision_check"
    text_llm = "text_llm"
    vision_llm = "vision_llm"
    url_fetch = "url_fetch"
    stamp_detection = "stamp_detection"
    document_diff = "document_diff"
    table_verification = "table_verification"
    regex_match = "regex_match"
    keyword_match = "keyword_match"
    comparison = "comparison"
    variable_extractor = "variable_extractor"


class ModuleSeverity(str, enum.Enum):
    """Severity levels for verification modules"""
    critical = "critical"  # 关键 - 失败会导致验证不通过
    warning = "warning"    # 告警 - 警告但不阻止通过
    info = "info"          # 信息 - 仅作记录，不影响结果


class VerificationModule(Base):
    """
    Verification Module - 校验模块

    A simplified alternative to complex logic graphs.
    Users can create modules and select them in rules for execution.
    """
    __tablename__ = "verification_modules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Module type determines which operator to use
    module_type = Column(Enum(ModuleType), nullable=False)

    # Severity determines how failures affect the final result
    severity = Column(Enum(ModuleSeverity), default=ModuleSeverity.warning, nullable=False)

    # Configuration parameters for the module (JSONB)
    # Example: {"pattern": "^ID:(?P<id>[A-Z0-9]+)$", "prompt": "Check if document is valid"}
    config = Column(JSONB, default=dict, nullable=False)

    # Optional: Link to a document category (None = global module)
    category_id = Column(UUID(as_uuid=False), ForeignKey("document_categories.id"), nullable=True)

    # Active status
    is_active = Column(Boolean, default=True, nullable=False)

    # System module flag (True for built-in modules)
    is_system = Column(Boolean, default=False, nullable=False)

    # Display order
    sort_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(Integer, nullable=True)  # Unix timestamp
    updated_at = Column(Integer, nullable=True)  # Unix timestamp

    # Relationships
    category = relationship("DocumentCategory", backref="modules")
    # rules = relationship("VerificationRule", secondary="rule_modules", back_populates="modules")


class RuleModule(Base):
    """
    Junction table for Rule-Module many-to-many relationship
    """
    __tablename__ = "rule_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(UUID(as_uuid=False), ForeignKey("verification_rules.id"), nullable=False)
    module_id = Column(UUID(as_uuid=False), ForeignKey("verification_modules.id"), nullable=False)

    # Timestamp
    created_at = Column(Integer, nullable=True)  # Unix timestamp
