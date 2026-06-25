from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
import uuid
import json

from app.models.file import File, FileStatus, FileType
from app.models.user import User
from app.core.config import settings
from app.schemas.file import FileFilter, FileResponse, FileDetailResponse
from app.core.minio_client import minio_client
from app.services.aliyun_service import aliyun_service


class FileService:
    """Service for file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_file(
        self,
        filename: str,
        file_size: int,
        file_bytes: bytes,
        uploaded_by: str,
        file_type: Optional[FileType] = None,
    ) -> File:
        """Create a new file record and upload to storage."""
        file_id = str(uuid.uuid4())
        file_path = f"files/{uploaded_by}/{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m')}/{file_id}.pdf"

        # Detect file type if not provided
        if not file_type:
            file_type = FileType.OTHER

        # Upload to MinIO
        import io
        minio_client.upload_file(
            file_path=file_path,
            file_data=io.BytesIO(file_bytes),
            content_type="application/pdf",
            length=file_size,
        )

        # Parse PDF metadata
        metadata = aliyun_service.parse_pdf_metadata(file_bytes)

        # Create file record
        db_file = File(
            id=file_id,
            filename=f"{file_id}.pdf",
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            page_count=metadata.get("page_count"),
            status=FileStatus.PENDING,
            uploaded_by=uploaded_by,
            will_delete_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.FILE_RETENTION_DAYS),
        )

        self.db.add(db_file)
        await self.db.commit()
        await self.db.refresh(db_file)

        return db_file

    async def get_file(self, file_id: str) -> Optional[File]:
        """Get a file by ID."""
        result = await self.db.execute(select(File).where(File.id == file_id))
        return result.scalar_one_or_none()

    async def get_file_detail(self, file_id: str) -> Optional[FileDetailResponse]:
        """Get detailed file information."""
        # Use selectinload to preload user in a single query (fixes N+1)
        result = await self.db.execute(
            select(File).options(selectinload(File.uploaded_by_user)).where(File.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            return None

        user = file.uploaded_by_user

        verification_result = None
        if file.verification_result:
            verification_result = json.loads(file.verification_result)

        return FileDetailResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_size=file.file_size,
            file_type=file.file_type,
            page_count=file.page_count,
            status=file.status,
            verification_progress=file.verification_progress,
            pass_count=file.pass_count,
            warning_count=file.warning_count,
            fail_count=file.fail_count,
            pass_rate=file.pass_rate,
            uploaded_at=file.uploaded_at,
            completed_at=file.completed_at,
            duration_seconds=file.duration_seconds,
            verification_result=verification_result,
            uploaded_by=user.email if user else None,
        )

    async def list_files(
        self,
        filters: FileFilter,
        user_id: Optional[str] = None,
    ) -> Tuple[List[File], int]:
        """List files with filtering and pagination."""
        # Build query
        query = select(File).options(selectinload(File.notes)).where(File.is_deleted == False)

        # Apply filters
        if filters.status:
            if filters.status == "completed":
                query = query.where(File.status.in_(["completed", "warning"]))
            elif filters.status == "processing":
                query = query.where(File.status.in_(["processing", "pending"]))
            else:
                query = query.where(File.status == filters.status)
        if filters.file_type:
            query = query.where(File.file_type == filters.file_type)
        if filters.institution:
            # verification_result 是 Text 列，需 cast 为 JSONB 后再提取签发机构
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import JSONB
            inst_expr = cast(File.verification_result, JSONB)["summary"]["institution"].astext
            query = query.where(inst_expr.ilike(f"%{filters.institution}%"))
        if filters.keyword:
            query = query.where(File.original_filename.ilike(f"%{filters.keyword}%"))
        if filters.date_from:
            query = query.where(File.uploaded_at >= filters.date_from)
        if filters.date_to:
            query = query.where(File.uploaded_at <= filters.date_to)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(File.uploaded_at.desc())
        query = query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)

        result = await self.db.execute(query)
        files = result.scalars().all()

        return files, total

    async def update_verification_status(
        self,
        file_id: str,
        status: FileStatus,
        progress: int,
        result: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> Optional[File]:
        """Update file verification status."""
        file = await self.get_file(file_id)
        if not file:
            return None

        file.status = status
        file.verification_progress = progress

        if result:
            file.verification_result = json.dumps(result)
            summary = result.get("summary", {})
            file.pass_count = summary.get("pass", 0)
            file.warning_count = summary.get("warning", 0)
            file.fail_count = summary.get("fail", 0)
            total = summary.get("total", 1)
            if total > 0:
                file.pass_rate = int((file.pass_count / total) * 100)
            file.verification_model = result.get("model_version")

        if error_message:
            file.verification_result = json.dumps({"error": error_message})

        if status in [FileStatus.COMPLETED, FileStatus.FAILED, FileStatus.WARNING]:
            file.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if file.uploaded_at:
                duration = int((file.completed_at - file.uploaded_at).total_seconds())
                file.duration_seconds = duration

        await self.db.commit()
        await self.db.refresh(file)

        return file

    async def delete_file(self, file_id: str) -> bool:
        """Soft delete a file."""
        file = await self.get_file(file_id)
        if not file:
            return False

        file.is_deleted = True
        file.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await self.db.commit()
        return True

    async def get_file_download_url(self, file_id: str) -> Optional[str]:
        """Generate a presigned download URL."""
        file = await self.get_file(file_id)
        if not file:
            return None

        return minio_client.get_presigned_url(file.file_path, expires=3600)

    async def batch_delete(self, file_ids: List[str]) -> int:
        """Batch delete files."""
        files = await self.db.execute(
            select(File).where(File.id.in_(file_ids))
        )
        files = files.scalars().all()

        count = 0
        for file in files:
            file.is_deleted = True
            file.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            count += 1

        await self.db.commit()
        return count

    async def resolve_review(
        self,
        file_id: str,
        action: str,
        comment: Optional[str],
        user_id: str,
        user_name: str,
    ) -> Optional[FileDetailResponse]:
        """Resolve a NEEDS_REVIEW file to either COMPLETED or FAILED."""
        file = await self.get_file(file_id)
        if not file:
            return None

        if file.status != FileStatus.NEEDS_REVIEW:
            return None

        new_status = FileStatus.COMPLETED if action == 'approve' else FileStatus.FAILED
        file.status = new_status
        file.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if file.uploaded_at:
            duration = int((file.completed_at - file.uploaded_at).total_seconds())
            file.duration_seconds = duration

        # Add note
        from app.models.note import Note
        note_content = f"已通过仲裁：{comment}" if action == 'approve' else f"已驳回仲裁：{comment}"
        if not comment:
            note_content = "已通过仲裁：无备注" if action == 'approve' else "已驳回仲裁：无备注"

        note = Note(
            file_id=file_id,
            author_id=user_id,
            author_name=user_name,
            content=note_content,
        )
        self.db.add(note)
        await self.db.commit()

        return await self.get_file_detail(file_id)
