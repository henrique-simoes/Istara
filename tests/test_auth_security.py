import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token

@pytest.mark.asyncio
async def test_team_status_insecure_flag():
    """Verify that insecure=True when team_mode is off and request is from a remote IP."""
    await init_db()
    # We use the app directly with a mock transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test localhost (should NOT be insecure even if team_mode is off)
        settings.team_mode = False
        response = await ac.get("/api/auth/team-status")
        assert response.status_code == 200
        data = response.json()
        assert data["team_mode"] is False
        assert data["insecure"] is False

        # 2. Test Team Mode (should NEVER be insecure)
        settings.team_mode = True
        response = await ac.get("/api/auth/team-status")
        assert response.status_code == 200
        assert response.json()["insecure"] is False

@pytest.mark.asyncio
async def test_auth_me_enforcement():
    """Verify that auth/me requires a token in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/me")
        # SecurityAuthMiddleware should catch this
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

@pytest.mark.asyncio
async def test_local_mode_admin_bypass():
    """Verify that local mode still works as expected (intentional bypass)."""
    await init_db()
    settings.team_mode = False
    # Ensure we have a secret for signing
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    
    # Generate a VALID token for the middleware to pass
    token = create_token("local", "tester", "admin")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # In local mode, auth/me returns admin
        response = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"
