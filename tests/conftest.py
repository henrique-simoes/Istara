"""Pytest configuration for Istara tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Unit tests must never inherit the developer checkout's persistent SQLite file:
# it may be on an older schema and parallel test processes can lock it.  An
# explicitly supplied DATABASE_URL still wins for integration/Postgres runs.
_PYTEST_DB_DIR = tempfile.TemporaryDirectory(prefix="istara-pytest-")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{Path(_PYTEST_DB_DIR.name) / 'istara.db'}",
)

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def pytest_sessionstart(session):
    """Make ORM mapper configuration deterministic across test order.

    Pi runtime tests can persist telemetry without initializing the database.
    Register every mapped class first so that early telemetry rows cannot leave
    unrelated project relationships in SQLAlchemy's permanent failed state.
    This imports metadata only; it does not create or connect to a database.
    """
    from app.models.database import register_models

    register_models()


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


@pytest.fixture(autouse=True)
def _no_live_llm_env(request, monkeypatch):
    if os.environ.get("ISTARA_RUN_REAL_LLM_BENCHMARK"):
        pytest.fail(
            "ISTARA_RUN_REAL_LLM_BENCHMARK is set: live inference is forbidden "
            "in this suite (use the marker-gated integration module explicitly)."
        )
    if request.node.get_closest_marker("live_llm") is None:
        monkeypatch.setenv("ISTARA_TEST_BLOCK_EXTERNAL_LLM", "1")
    yield
