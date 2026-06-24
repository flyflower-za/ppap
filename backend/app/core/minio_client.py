from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io
import asyncio


class MinIOClient:
    """MinIO client wrapper for file storage."""

    def __init__(self):
        self.client: Optional[Minio] = None
        self.bucket = settings.MINIO_BUCKET

    def connect(self):
        """Create MinIO client."""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            raise Exception(f"MinIO bucket error: {e}")

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str,
        length: Optional[int] = None,
    ) -> str:
        """Upload a file to MinIO."""
        if not self.client:
            self.connect()

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=file_path,
            data=file_data,
            length=length,
            content_type=content_type,
        )
        return file_path

    def download_file(self, file_path: str) -> bytes:
        """Download a file from MinIO."""
        if not self.client:
            self.connect()

        try:
            response = self.client.get_object(bucket_name=self.bucket, object_name=file_path)
            return response.read()
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {file_path}")

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from MinIO."""
        if not self.client:
            self.connect()

        try:
            self.client.remove_object(bucket_name=self.bucket, object_name=file_path)
            return True
        except S3Error:
            return False

    def get_presigned_url(self, file_path: str, expires: int = 3600) -> str:
        """Generate a presigned URL for file download."""
        if not self.client:
            self.connect()

        from datetime import timedelta
        return self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=file_path,
            expires=timedelta(seconds=expires),
        )

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in MinIO."""
        if not self.client:
            self.connect()

        try:
            self.client.stat_object(bucket_name=self.bucket, object_name=file_path)
            return True
        except S3Error:
            return False

    # ── Async wrappers (avoid blocking the event loop) ──

    async def upload_file_async(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str,
        length: Optional[int] = None,
    ) -> str:
        """Async-friendly upload — runs sync MinIO call in a thread pool."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.upload_file, file_path, file_data, content_type, length
        )

    async def download_file_async(self, file_path: str) -> bytes:
        """Async-friendly download — runs sync MinIO call in a thread pool."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.download_file, file_path
        )

    async def delete_file_async(self, file_path: str) -> bool:
        """Async-friendly delete — runs sync MinIO call in a thread pool."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.delete_file, file_path
        )


# Global MinIO client instance
minio_client = MinIOClient()
