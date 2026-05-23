from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FormFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.schemas.file import (
    FileUpload, FileResponse, FileDetailResponse, FileFilter,
    FileListResponse, FileTypeEnum, FileStatusEnum, BatchDeleteRequest,
)
from app.services.file_service import FileService
from app.models.user import User
from app.api.deps import get_current_user
from app.models.file import FileType
from app.tasks.verification_tasks import queue_verification_task

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileResponse)
async def upload_file(
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

    return FileResponse.model_validate(db_file)


@router.get("", response_model=FileListResponse)
async def list_files(
    status: FileStatusEnum = Query(default=None),
    file_type: FileTypeEnum = Query(default=None),
    keyword: str = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
