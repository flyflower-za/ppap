import pytest
from httpx import AsyncClient
from tests.fixtures import mock_normal_user, mock_admin_user

@pytest.mark.asyncio
async def test_smtp_config_update_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot update SMTP settings (403 Forbidden)."""
    override_user(mock_normal_user)
    
    payload = {
        "enabled": False,
        "host": "smtp.example.com",
        "port": 587,
        "encryption": "tls",
        "username": "test@example.com",
        "from_name": "Test Platform",
        "password": "test"
    }
    
    response = await client.post("/api/v1/settings/smtp", json=payload)
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_email_templates_delete_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot delete email templates."""
    override_user(mock_normal_user)
    
    response = await client.delete("/api/v1/settings/email-templates/test-template")
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_notifications_update_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot modify system-wide notification settings."""
    override_user(mock_normal_user)

    payload = {
        "email_enabled": True,
        "notify_on_failure": True,
        "daily_summary": True
    }

    response = await client.post("/api/v1/settings/notifications", json=payload)
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_notifications_get_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot read notification settings."""
    override_user(mock_normal_user)

    response = await client.get("/api/v1/settings/notifications")
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_file_retention_get_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot read file retention settings."""
    override_user(mock_normal_user)

    response = await client.get("/api/v1/settings/file-retention")
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_file_retention_update_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot update file retention settings."""
    override_user(mock_normal_user)

    payload = {
        "retention_days": 30,
        "auto_cleanup_enabled": True,
        "cleanup_hour": 2
    }

    response = await client.post("/api/v1/settings/file-retention", json=payload)
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"


@pytest.mark.asyncio
async def test_file_retention_cleanup_normal_user(client: AsyncClient, override_user):
    """Test that normal users cannot trigger file cleanup."""
    override_user(mock_normal_user)

    response = await client.post("/api/v1/settings/file-retention/cleanup-now")
    assert response.status_code == 403
    assert response.json()["message"] == "需要管理员权限"
