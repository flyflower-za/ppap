import pytest
from httpx import AsyncClient
from typing import AsyncGenerator

from app.main import app
from app.api.deps import get_current_user
from app.models.user import User

from tests.fixtures import mock_normal_user, mock_admin_user

@pytest.fixture
def override_user():
    """Fixture to dynamically override the current user dependency."""
    def _override_user(user: User = mock_normal_user):
        async def dependency():
            return user
        app.dependency_overrides[get_current_user] = dependency
    
    yield _override_user
    
    # Clean up overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture to provide an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
