from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class FileStatus(str, enum.Enum):
    """File verification status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"


class FileType(str, enum.Enum):
    """File type categories."""
    PRODUCTION_PLAN = "production_plan"      # 生产计划单
    QUALITY_REPORT = "quality_report"        # 质量检测报告
    PURCHASE_ORDER = "purchase_order"        # 采购订单
    SUPPLIER_QUALIFICATION = "supplier_qualification"  # 供应商资质
    PRODUCT_SPECIFICATION = "product_specification"    # 产品规格
    OTHER = "other"


class File(Base):
    """File model for uploaded PDF files."""

    __tablename__ = "files"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # MinIO path
    file_size = Column(BigInteger, nullable=False)  # bytes
    file_type = Column(Enum(FileType), default=FileType.OTHER)
    page_count = Column(Integer)

    # Verification status
    status = Column(Enum(FileStatus), default=FileStatus.PENDING, index=True)
    verification_progress = Column(Integer, default=0)  # 0-100
    verification_model = Column(String(100))  # e.g., "Aliyun Agent v1.2"

    # Verification results
    verification_result = Column(Text)  # JSON string
    pass_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    pass_rate = Column(Integer)  # percentage

    # Timing
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Relationships
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_by_user = relationship("User", back_populates="files")

    # Deletion
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    will_delete_at = Column(DateTime)  # Auto-delete after retention period

    # Relationships
    tasks = relationship("Task", back_populates="file", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="file", cascade="all, delete-orphan")
