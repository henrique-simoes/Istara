"""Tests for Network Security middleware — X-Access-Token validation."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def reset_network_security():
    """Reset network security settings after each test."""
    from app.config import settings

    original_token = settings.network_access_token
    original_bind_host = settings.bind_host
    original_team_mode = settings.team_mode
    yield
    settings.network_access_token = original_token
    settings.bind_host = original_bind_host
    settings.team_mode = original_team_mode


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
    from app.core.network_security import EXEMPT_PATHS

    assert "/api/health" in EXEMPT_PATHS
    assert "/api/auth/login" in EXEMPT_PATHS
    assert "/api/auth/register" in EXEMPT_PATHS
    assert "/api/webauthn/authenticate/start" in EXEMPT_PATHS
    assert "/api/webauthn/authenticate/finish" in EXEMPT_PATHS


def test_local_admin_network_guard_detects_unsafe_wildcard_bind():
    """Local mode on 0.0.0.0 without a network token must be guarded."""
    from app.config import settings
    from app.core.network_security import requires_local_admin_network_guard

    settings.team_mode = False
    settings.network_access_token = ""
    settings.bind_host = "0.0.0.0"
    assert requires_local_admin_network_guard() is True

    settings.bind_host = "127.0.0.1"
    assert requires_local_admin_network_guard() is False

    settings.bind_host = "0.0.0.0"
    settings.network_access_token = "network-secret"
    assert requires_local_admin_network_guard() is False

    settings.network_access_token = ""
    settings.team_mode = True
    assert requires_local_admin_network_guard() is False


def test_remote_local_admin_block_reason_denies_remote_api_access():
    """Remote clients cannot receive implicit local admin in exposed local mode."""
    from app.config import settings
    from app.core.network_security import remote_local_admin_block_reason

    settings.team_mode = False
    settings.network_access_token = ""
    settings.bind_host = "0.0.0.0"

    reason = remote_local_admin_block_reason("203.0.113.10", "/api/agents/status")
    assert reason is not None
    assert "Remote requests are denied" in reason
    assert remote_local_admin_block_reason("127.0.0.1", "/api/agents/status") is None
    assert remote_local_admin_block_reason("203.0.113.10", "/api/health") is None
