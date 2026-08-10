"""Pytest configuration for Istara tests."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


@pytest_asyncio.fixture(autouse=True)
async def dispose_db_engine():
    """Dispose the global async engine after each test to prevent
    aiosqlite 'Event loop is closed' warnings and SQLite locking."""
    yield
    from app.core.compute_route_evidence import drain_compute_telemetry
    from app.models.database import engine

    await drain_compute_telemetry()
    await engine.dispose()


@pytest.fixture
def admin_token():
    """Sessionless admin token for unit tests that do not exercise session storage."""
    from app.config import settings
    from app.core.auth import create_token

    if not settings.jwt_secret:
        settings.jwt_secret = "test-suite-secret"
    return create_token("test-admin", "admin", "admin", mfa_verified=True)


@pytest.fixture
def admin_auth_headers(admin_token):
    """Authorization headers for protected API tests."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def researcher_token():
    """Sessionless researcher token for role and permission tests."""
    from app.config import settings
    from app.core.auth import create_token

    if not settings.jwt_secret:
        settings.jwt_secret = "test-suite-secret"
    return create_token(
        "test-researcher", "researcher", "researcher", mfa_verified=True
    )


@pytest.fixture
def researcher_auth_headers(researcher_token):
    """Authorization headers for non-admin protected API tests."""
    return {"Authorization": f"Bearer {researcher_token}"}
