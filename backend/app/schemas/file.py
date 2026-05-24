from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from app.models.file import FileStatus, FileType


class FileTypeEnum(str, Enum):
    """File type enum for API."""
    PRODUCTION_PLAN = "production_plan"
    QUALITY_REPORT = "quality_report"
    PURCHASE_ORDER = "purchase_order"
    SUPPLIER_QUALIFICATION = "supplier_qualification"
    PRODUCT_SPECIFICATION = "product_specification"
    OTHER = "other"


class FileStatusEnum(str, Enum):
    """File status enum for API."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"


class FileUpload(BaseModel):
    """File upload schema."""
    file_type: Optional[FileTypeEnum] = FileTypeEnum.OTHER


class FileResponse(BaseModel):
    """File response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: Optional[FileTypeEnum] = None
    page_count: Optional[int] = None
    status: FileStatusEnum
    verification_progress: int
    pass_count: int = 0
    warning_count: int = 0
    fail_count: int = 0
    pass_rate: Optional[int] = None
    uploaded_at: datetime
    will_delete_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    notes_summary: Optional[str] = ""
    verification_result_json: Optional[Dict[str, Any]] = None


class FileReviewResolution(BaseModel):
    action: str = Field(..., description="The review decision: 'approve' or 'reject'")
    comment: Optional[str] = Field(None, description="Optional review comment or reason")


class FileDetailResponse(FileResponse):
    """Detailed file response with verification results."""
    verification_result: Optional[Dict[str, Any]] = None
    uploaded_by: Optional[str] = None  # User email


class FileFilter(BaseModel):
    """File filter parameters."""
    status: Optional[FileStatusEnum] = None
    file_type: Optional[FileTypeEnum] = None
    keyword: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)


class FileListResponse(BaseModel):
    """Paginated file list response."""
    total: int
    page: int
    page_size: int
    items: List[FileResponse]


class VerificationResult(BaseModel):
    """Single verification check result."""
    name: str
    status: str  # pass, fail, warning
    message: str
    page: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class FileVerificationUpdate(BaseModel):
    """Update file verification status (internal use)."""
    status: FileStatusEnum
    progress: int = Field(ge=0, le=100)
    result: Optional[Dict[str, Any]] = None


class BatchDeleteRequest(BaseModel):
    """Batch delete files request schema."""
    file_ids: List[str]
    error_message: Optional[str] = None
