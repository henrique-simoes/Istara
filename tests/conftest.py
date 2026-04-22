"""Pytest configuration for Istara tests."""

import sys
from pathlib import Path

import pytest_asyncio

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


@pytest_asyncio.fixture(autouse=True)
async def dispose_db_engine():
    """Dispose the global async engine after each test to prevent
    aiosqlite 'Event loop is closed' warnings and SQLite locking."""
    yield
    from app.models.database import engine
    await engine.dispose()
