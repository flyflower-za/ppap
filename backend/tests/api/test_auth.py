import pytest
from httpx import AsyncClient
from tests.fixtures import mock_normal_user, mock_admin_user

@pytest.mark.asyncio
async def test_get_me_normal_user(client: AsyncClient, override_user):
    """Test getting current user profile for a normal user."""
    override_user(mock_normal_user)
    
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_normal_user.email
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_get_me_admin_user(client: AsyncClient, override_user):
    """Test getting current user profile for an admin user."""
    override_user(mock_admin_user)
    
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_admin_user.email
    assert data["is_admin"] is True
