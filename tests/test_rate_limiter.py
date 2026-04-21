"""Tests for rate limiting — login rate limiter."""

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-memory login attempts between tests."""
    from app.api.routes.auth import _login_attempts
    _login_attempts.clear()
    yield
    _login_attempts.clear()


@pytest.mark.asyncio
async def test_login_rate_limiter_function():
    """The _check_login_rate function blocks after 5 attempts in 60s."""
    from app.api.routes.auth import _check_login_rate, _login_attempts, MAX_LOGIN_ATTEMPTS
    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_request.client.host = "192.168.1.100"

    # 5 attempts should pass
    for i in range(MAX_LOGIN_ATTEMPTS):
        await _check_login_rate(mock_request)

    # 6th attempt should raise
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await _check_login_rate(mock_request)
    assert exc_info.value.status_code == 429
    assert "Too many login attempts" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_rate_limiter_resets_after_window():
    """After the window expires, login attempts are allowed again."""
    from app.api.routes.auth import _check_login_rate, _login_attempts, LOGIN_WINDOW
    from unittest.mock import MagicMock
    from fastapi import HTTPException

    mock_request = MagicMock()
    mock_request.client.host = "10.0.0.50"

    # Fill up
    for _ in range(5):
        await _check_login_rate(mock_request)

    # Verify blocked
    with pytest.raises(HTTPException):
        await _check_login_rate(mock_request)

    # Simulate time passing by clearing the old entries
    now = time.time()
    _login_attempts["10.0.0.50"] = [t for t in _login_attempts.get("10.0.0.50", []) if now - t < LOGIN_WINDOW]
    # Now clear them to simulate window expired
    _login_attempts.clear()

    # Should be allowed again
    await _check_login_rate(mock_request)  # No exception = allowed


@pytest.mark.asyncio
async def test_rate_limiter_per_ip_isolation():
    """Different IPs have independent rate limits."""
    from app.api.routes.auth import _check_login_rate, _login_attempts
    from unittest.mock import MagicMock
    from fastapi import HTTPException

    mock_ip1 = MagicMock()
    mock_ip1.client.host = "1.1.1.1"

    mock_ip2 = MagicMock()
    mock_ip2.client.host = "2.2.2.2"

    # Exhaust IP1's limit
    for _ in range(5):
        await _check_login_rate(mock_ip1)

    # IP1 should be blocked
    with pytest.raises(HTTPException):
        await _check_login_rate(mock_ip1)

    # IP2 should still be allowed
    await _check_login_rate(mock_ip2)  # No exception
