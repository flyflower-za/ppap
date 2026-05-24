from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FormFile, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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
from app.models.file import FileType, File
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


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file_detail(
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

    return file


@router.get("/{file_id}/download")
async def download_file(
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

    return {"download_url": url}


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file (soft delete)."""
    file_service = FileService(db)
    success = await file_service.delete_file(file_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )


@router.post("/batch-delete", status_code=status.HTTP_204_NO_CONTENT)
async def batch_delete_files(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch delete files."""
    file_service = FileService(db)
    await file_service.batch_delete(request.file_ids)


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
