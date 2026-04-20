"""Tests for Network Security middleware — X-Access-Token validation."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def reset_network_security():
    """Reset network security settings after each test."""
    from app.config import settings
    original_token = settings.network_access_token
    yield
    settings.network_access_token = original_token


def test_localhost_detection():
    """Localhost requests are correctly identified."""
    from app.core.network_security import _is_localhost

    assert _is_localhost("127.0.0.1") is True
    assert _is_localhost("::1") is True
    assert _is_localhost("localhost") is True
    assert _is_localhost("192.168.1.100") is False
    assert _is_localhost("203.0.113.1") is False
    assert _is_localhost(None) is False


def test_token_extraction_from_header():
    """X-Access-Token header (lowercase) is extracted correctly."""
    from app.core.network_security import _extract_token

    mock_request = MagicMock()
    mock_request.headers = {"x-access-token": "my-secret-token"}
    mock_request.query_params = {}
    assert _extract_token(mock_request) == "my-secret-token"


def test_token_extraction_from_query():
    """?token= query param is extracted correctly."""
    from app.core.network_security import _extract_token

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.query_params = {"token": "query-token-value"}
    assert _extract_token(mock_request) == "query-token-value"


def test_token_extraction_from_short_bearer():
    """Short Bearer token (access token, not JWT) is extracted."""
    from app.core.network_security import _extract_token

    mock_request = MagicMock()
    mock_request.headers = {"authorization": "Bearer short-access-token"}
    mock_request.query_params = {}
    assert _extract_token(mock_request) == "short-access-token"


def test_token_extraction_returns_none():
    """No token returns None."""
    from app.core.network_security import _extract_token

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.query_params = {}
    assert _extract_token(mock_request) is None


def test_exempt_paths():
    """Health, login, and register paths are exempt."""
    from app.core.network_security import EXEMPT_PATHS, EXEMPT_PREFIXES

    assert "/api/health" in EXEMPT_PATHS
    assert "/api/auth/login" in EXEMPT_PATHS
    assert "/api/auth/register" in EXEMPT_PATHS
