import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from app.tasks.cleanup_tasks import cleanup_expired_files
from app.models.file import File
from app.models.setting import Setting


def test_cleanup_expired_files_skipped_when_disabled():
    """Test that cleanup skips execution when auto_cleanup_enabled is false."""
    mock_setting = MagicMock(spec=Setting)
    mock_setting.value = '{"retention_days": 30, "auto_cleanup_enabled": false}'

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_setting

    with patch('app.tasks.cleanup_tasks.async_session_maker') as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        
        result = cleanup_expired_files()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "Auto cleanup disabled"
        assert result["deleted_count"] == 0


def test_cleanup_expired_files_deletes_old_files():
    """Test that cleanup properly identifies and deletes old files."""
    mock_setting = MagicMock(spec=Setting)
    mock_setting.value = '{"retention_days": 30, "auto_cleanup_enabled": true}'

    mock_file = MagicMock(spec=File)
    mock_file.id = "file_123"
    mock_file.file_path = "test/path.pdf"
    mock_file.file_size = 1024

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_setting
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_file]
    mock_db.execute.return_value = mock_result

    with patch('app.tasks.cleanup_tasks.async_session_maker') as mock_session_maker, \
         patch('app.tasks.cleanup_tasks.minio_client') as mock_minio:
        
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_minio.delete_file.return_value = True
        
        result = cleanup_expired_files()
        
        assert result["status"] == "success"
        assert result["deleted_count"] == 1
        assert result["total_freed_space"] == 1024
        assert mock_file.is_deleted is True
        mock_minio.delete_file.assert_called_once_with("test/path.pdf")
        mock_db.commit.assert_called_once()
