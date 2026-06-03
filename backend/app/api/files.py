from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FormFile, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.core.database import get_db
from app.core.config import settings
from app.core.permissions import get_accessible_departments
from app.schemas.file import (
    FileUpload, FileResponse, FileDetailResponse, FileFilter,
    FileListResponse, FileTypeEnum, FileStatusEnum, BatchDeleteRequest,
)
from app.services.file_service import FileService
from app.models.user import User, UserRole
from app.api.deps import get_current_user
from app.models.file import FileType, File, FileStatus
from app.models.task import Task
from app.tasks.verification_tasks import queue_verification_task
from app.core.audit_logger import log_audit_event

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    request: Request,
    file: UploadFile = FormFile(...),
    file_type: FileTypeEnum = Query(default=FileTypeEnum.OTHER),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF file for verification."""
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Create file record
    file_service = FileService(db)
    file_type_enum = FileType(file_type.value) if file_type else FileType.OTHER

    db_file = await file_service.create_file(
        filename=file.filename,
        file_size=len(content),
        file_bytes=content,
        uploaded_by=current_user.id,
        file_type=file_type_enum,
    )

    # Queue verification task asynchronously in Celery background
    queue_verification_task.delay(db_file.id)

    await log_audit_event(
        db=db,
        action="UPLOAD_DOCUMENT",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=db_file.id,
        details={"filename": file.filename, "file_type": db_file.file_type.value},
        request=request
    )

    return FileResponse.model_validate(db_file)


@router.get("", response_model=FileListResponse)
async def list_files(
    status: FileStatusEnum = Query(default=None),
    file_type: FileTypeEnum = Query(default=None),
    keyword: str = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List files with filtering and pagination."""
    from datetime import datetime

    filters = FileFilter(
        status=status,
        file_type=file_type,
        keyword=keyword,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        page=page,
        page_size=page_size,
    )

    file_service = FileService(db)
    files, total = await file_service.list_files(filters)

    return FileListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[FileResponse.model_validate(f) for f in files],
    )


@router.get("/statistics")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve macro-level compliance statistics for the dashboard."""
    from app.models.file import File, FileStatus
    from sqlalchemy import select, func, case, Date
    from datetime import datetime, timedelta
    import json
    from collections import Counter

    # 1. Overview counts
    total_stmt = select(func.count(File.id))
    total_res = await db.execute(total_stmt)
    total_count = total_res.scalar() or 0

    status_stmt = select(File.status, func.count(File.id)).group_by(File.status)
    status_res = await db.execute(status_stmt)
    status_counts = {}
    for row in status_res.all():
        if row[0] is not None:
            status_counts[row[0].value] = row[1]
        else:
            status_counts["unknown"] = row[1]

    completed_count = status_counts.get(FileStatus.COMPLETED.value, 0)
    warning_count = status_counts.get(FileStatus.WARNING.value, 0)
    failed_count = status_counts.get(FileStatus.FAILED.value, 0)
    needs_review_count = status_counts.get(FileStatus.NEEDS_REVIEW.value, 0)
    pending_count = status_counts.get(FileStatus.PENDING.value, 0)
    processing_count = status_counts.get(FileStatus.PROCESSING.value, 0)

    decided_total = completed_count + warning_count + failed_count
    pass_rate = int(((completed_count + warning_count) / max(1, decided_total)) * 100)

    # 2. Trend statistics (Last 14 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=14)
    
    trend_stmt = (
        select(
            func.cast(File.uploaded_at, Date).label("date"),
            func.count(File.id).label("total"),
            func.sum(case((File.status.in_([FileStatus.COMPLETED, FileStatus.WARNING]), 1), else_=0)).label("passed")
        )
        .where(File.uploaded_at >= start_date)
        .group_by(func.cast(File.uploaded_at, Date))
        .order_by("date")
    )
    
    trend_res = await db.execute(trend_stmt)
    trend_data = []
    
    # Fill in potential date gaps with 0
    date_map = {}
    for row in trend_res.all():
        if row.date:
            date_str = row.date.strftime("%Y-%m-%d")
            date_map[date_str] = {
                "date": date_str,
                "total": row.total,
                "passed": int(row.passed or 0)
            }
        
    for i in range(15):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        if d not in date_map:
            trend_data.append({
                "date": d,
                "total": 0,
                "passed": 0
            })
        else:
            trend_data.append(date_map[d])

    # 3. Top Failing Rules Counter
    # Parse last 1000 files results
    files_stmt = select(File.verification_result).where(File.verification_result.isnot(None)).order_by(File.uploaded_at.desc()).limit(1000)
    files_res = await db.execute(files_stmt)
    failing_rules = Counter()
    
    for row in files_res.scalars().all():
        try:
            data = json.loads(row) if isinstance(row, str) else row
            if data and "checks" in data:
                for check in data["checks"]:
                    if check.get("status") == "fail":
                        failing_rules[check.get("name")] += 1
        except Exception:
            continue
            
    top_failing = [
        {"rule_name": name, "count": count} 
        for name, count in failing_rules.most_common(5)
    ]

    return {
        "overview": {
            "total": total_count,
            "completed": completed_count,
            "warning": warning_count,
            "failed": failed_count,
            "needs_review": needs_review_count,
            "pending": pending_count,
            "processing": processing_count,
            "pass_rate": pass_rate
        },
        "trend": trend_data,
        "top_failing_rules": top_failing
    }


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file_detail(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed file information."""
    file_service = FileService(db)
    file = await file_service.get_file_detail(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    await log_audit_event(
        db=db,
        action="VIEW_VERIFICATION_REPORT",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=file_id,
        details={"filename": file.filename, "status": file.status.value},
        request=request
    )

    return file


@router.get("/{file_id}/download")
async def download_file(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a presigned download URL for a file."""
    file_service = FileService(db)
    url = await file_service.get_file_download_url(file_id)

    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # 获取文件基本信息用于日志详情
    db_file = await file_service.get_file(file_id)
    filename = db_file.filename if db_file else "Unknown"

    await log_audit_event(
        db=db,
        action="DOWNLOAD_DOCUMENT",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=file_id,
        details={"filename": filename},
        request=request
    )

    return {"download_url": url}


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file (soft delete)."""
    file_service = FileService(db)
    
    # 提前获取文件名用于审计日志
    db_file = await file_service.get_file(file_id)
    filename = db_file.filename if db_file else "Unknown"
    
    success = await file_service.delete_file(file_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    await log_audit_event(
        db=db,
        action="DELETE_DOCUMENT",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=file_id,
        details={"filename": filename},
        request=request
    )


@router.post("/batch-delete", status_code=status.HTTP_204_NO_CONTENT)
async def batch_delete_files(
    request: Request,
    batch_req: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch delete files."""
    file_service = FileService(db)
    await file_service.batch_delete(batch_req.file_ids)

    await log_audit_event(
        db=db,
        action="BATCH_DELETE_DOCUMENTS",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=None,
        details={"file_ids": batch_req.file_ids, "count": len(batch_req.file_ids)},
        request=request
    )


@router.post("/{file_id}/reverify", response_model=FileResponse)
async def reverify_file(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-verify an existing file."""
    # Fetch the file
    result = await db.execute(select(File).where(File.id == file_id, File.is_deleted == False))
    db_file = result.scalars().first()
    
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
        
    # Reset file state
    db_file.status = FileStatus.PENDING
    db_file.verification_progress = 0
    db_file.verification_result = None
    db_file.pass_count = 0
    db_file.warning_count = 0
    db_file.fail_count = 0
    db_file.pass_rate = 0.0
    db_file.duration_seconds = None
    db_file.completed_at = None
    
    # Delete old tasks
    await db.execute(delete(Task).where(Task.file_id == db_file.id))
    
    await db.commit()
    await db.refresh(db_file)
    
    # Re-queue
    queue_verification_task.delay(db_file.id)
    
    await log_audit_event(
        db=db,
        action="REVERIFY_DOCUMENT",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=db_file.id,
        details={"filename": db_file.filename},
        request=request
    )
    
    return FileResponse.model_validate(db_file)


from app.schemas.file import FileReviewResolution

@router.post("/{file_id}/resolve_review", response_model=FileDetailResponse)
async def resolve_review(
    request: Request,
    file_id: str,
    resolution: FileReviewResolution,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a file currently in NEEDS_REVIEW status."""
    if resolution.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'",
        )

    file_service = FileService(db)
    file_detail = await file_service.resolve_review(
        file_id=file_id,
        action=resolution.action,
        comment=resolution.comment,
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.email,
    )

    if not file_detail:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found or not in NEEDS_REVIEW status",
        )

    await log_audit_event(
        db=db,
        action="RESOLVE_REVIEW",
        user=current_user,
        resource_type="DOCUMENT",
        resource_id=file_id,
        details={"action": resolution.action, "comment": resolution.comment},
        request=request
    )

    return file_detail
