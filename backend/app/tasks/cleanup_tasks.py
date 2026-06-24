"""
File cleanup scheduled tasks
"""
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.file import File
from app.models.setting import Setting
from app.core.minio_client import minio_client

logger = get_task_logger(__name__)


@celery_app.task(name='app.tasks.cleanup_tasks.cleanup_expired_files')
def cleanup_expired_files():
    """
    Cleanup expired PDF files based on retention settings.

    This task:
    1. Reads file_retention_settings from database
    2. Finds all files past retention period
    3. Deletes files from MinIO storage
    4. Marks files as deleted in database
    """
    logger.info("Starting file cleanup task")

    async def _async_cleanup():
        task_engine = create_async_engine(
            settings.DATABASE_URL, echo=settings.DEBUG,
            pool_pre_ping=True, pool_size=5, max_overflow=10,
        )
        task_session_maker = sessionmaker(
            task_engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with task_session_maker() as db:
                # Get retention settings from database
                setting = await db.get(Setting, "file_retention_settings")

                # Default values if not configured
                retention_days = 30
                auto_cleanup_enabled = True

                if setting:
                    try:
                        import json
                        settings_dict = json.loads(setting.value)
                        retention_days = settings_dict.get('retention_days', 30)
                        auto_cleanup_enabled = settings_dict.get('auto_cleanup_enabled', True)
                        logger.info(f"Loaded retention settings: {retention_days} days, auto_cleanup={auto_cleanup_enabled}")
                    except Exception as e:
                        logger.warning(f"Failed to parse retention settings, using defaults: {e}")

                if not auto_cleanup_enabled:
                    logger.info("Auto cleanup is disabled, skipping cleanup task")
                    return {
                        "status": "skipped",
                        "reason": "Auto cleanup disabled",
                        "deleted_count": 0,
                        "failed_count": 0
                    }

                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

                # Find files that should be deleted
                query = select(File).where(
                    File.is_deleted == False,
                    (
                        (File.will_delete_at < datetime.utcnow()) |
                        (File.uploaded_at < cutoff_date)
                    )
                )

                result = await db.execute(query)
                files_to_delete = result.scalars().all()

                if not files_to_delete:
                    logger.info("No files to clean up")
                    return {
                        "status": "success",
                        "deleted_count": 0,
                        "failed_count": 0,
                        "retention_days": retention_days
                    }

                logger.info(f"Found {len(files_to_delete)} files to delete")

                deleted_count = 0
                failed_count = 0
                total_freed_space = 0

                for file in files_to_delete:
                    try:
                        if file.file_path:
                            success = minio_client.delete_file(file.file_path)
                            if success:
                                logger.info(f"Deleted file from MinIO: {file.file_path}")
                            else:
                                logger.warning(f"Failed to delete from MinIO (file may not exist): {file.file_path}")

                        file.is_deleted = True
                        file.deleted_at = datetime.utcnow()

                        deleted_count += 1
                        total_freed_space += file.file_size or 0

                        logger.info(f"Marked file as deleted: {file.id} - {file.original_filename}")

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to delete file {file.id}: {e}")

                await db.commit()

                logger.info(
                    f"Cleanup completed: {deleted_count} files deleted, "
                    f"{failed_count} failed, {total_freed_space} bytes freed"
                )

                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                    "failed_count": failed_count,
                    "total_freed_space": total_freed_space,
                    "retention_days": retention_days
                }
        finally:
            await task_engine.dispose()

    # Run the async operations
    try:
        import asyncio
        result = asyncio.run(_async_cleanup())
        return result
    except Exception as e:
        logger.error(f"File cleanup task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "deleted_count": 0,
            "failed_count": 0
        }
