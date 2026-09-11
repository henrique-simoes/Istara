"""Unit tests for Istara version resolution and update mechanics."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.routes import updates as updates_routes
from app.api.routes.updates import (
    _parse_calver,
    apply_update,
    check_for_updates,
    get_current_version,
    is_containerized,
    is_newer,
)


def test_calver_parsing():
    """Verify CalVer string parsing into 4-element int tuples."""
    assert _parse_calver("2026.05.27.3") == (2026, 5, 27, 3)
    assert _parse_calver("v2026.05.27.3") == (2026, 5, 27, 3)
    assert _parse_calver("2026.04.27") == (2026, 4, 27, 0)
    assert _parse_calver("2026.05.27") == (2026, 5, 27, 0)
    assert _parse_calver("v2026.04.08.3") == (2026, 4, 8, 3)
    assert _parse_calver("") == ()


def test_is_newer_calver_comparisons():
    """Verify semantic ordering of date-based CalVer releases."""
    # May release is newer than April release
    assert is_newer("2026.05.27.3", "2026.04.27") is True
    assert is_newer("2026.04.27", "2026.05.27.3") is False

    # April 8 is older than April 27
    assert is_newer("2026.04.08.3", "2026.04.27") is False
    assert is_newer("2026.04.27", "2026.04.08.3") is True

    # Patch versions on same date
    assert is_newer("2026.05.27.3", "2026.05.27.2") is True
    assert is_newer("2026.05.27.2", "2026.05.27.3") is False
    assert is_newer("2026.05.27.1", "2026.05.27") is True

    # Identical versions
    assert is_newer("2026.05.27.3", "2026.05.27.3") is False
    assert is_newer("2026.04.27", "2026.04.27") is False

    # Edge cases
    assert is_newer("", "2026.04.27") is False
    assert is_newer("unknown", "2026.04.27") is False
    assert is_newer("2026.05.27.3", "unknown") is True


def test_is_containerized_detection(monkeypatch):
    """Verify container environment detection."""
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.delenv("CONTAINER", raising=False)
    monkeypatch.delenv("DOCKER_CONTAINER", raising=False)
    assert is_containerized() is False

    def fake_is_file(self):
        return str(self) == "/.dockerenv"

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    assert is_containerized() is True

    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setenv("CONTAINER", "docker")
    assert is_containerized() is True


@pytest.mark.asyncio
async def test_check_for_updates_when_current_is_latest(monkeypatch):
    """When running latest version, check_for_updates reports update_available: False."""
    updates_routes._update_cache.clear()

    mock_releases = [
        {"tag_name": "v2026.05.27.3", "name": "Istara 2026.05.27.3", "draft": False, "prerelease": False},
        {"tag_name": "v2026.04.08.3", "name": "Istara 2026.04.08.3", "draft": False, "prerelease": False},
    ]

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return SimpleNamespace(status_code=200, json=lambda: mock_releases)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())
    monkeypatch.setattr(updates_routes, "get_current_version", lambda: "2026.05.27.3")
    monkeypatch.setattr(updates_routes, "is_containerized", lambda: False)

    res = await check_for_updates()
    assert res["update_available"] is False
    assert res["current_version"] == "2026.05.27.3"
    assert res["latest_version"] == "2026.05.27.3"
    assert res["release_name"] == "Istara 2026.05.27.3"


@pytest.mark.asyncio
async def test_check_for_updates_when_outdated_in_docker(monkeypatch):
    """When running older version in Docker, returns update_available: True with docker command."""
    updates_routes._update_cache.clear()

    mock_releases = [
        {
            "tag_name": "v2026.05.27.3",
            "name": "Istara 2026.05.27.3",
            "body": "Changelog text",
            "draft": False,
            "prerelease": False,
            "assets": [],
        },
    ]

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return SimpleNamespace(status_code=200, json=lambda: mock_releases)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())
    monkeypatch.setattr(updates_routes, "get_current_version", lambda: "2026.04.27")
    monkeypatch.setattr(updates_routes, "is_containerized", lambda: True)
    monkeypatch.setattr(updates_routes, "head_includes_release", lambda *a: False)

    res = await check_for_updates()
    assert res["update_available"] is True
    assert res["current_version"] == "2026.04.27"
    assert res["latest_version"] == "2026.05.27.3"
    assert res["install_type"] == "docker"
    assert res["can_auto_update"] is False
    assert "docker compose pull" in res["docker_command"]


@pytest.mark.asyncio
async def test_check_for_updates_rate_limit_git_fallback(monkeypatch):
    """When GitHub REST API is rate limited (403), falls back to git ls-remote tags."""
    updates_routes._update_cache.clear()

    class FakeClient403:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return SimpleNamespace(status_code=403)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient403())
    monkeypatch.setattr(updates_routes, "get_current_version", lambda: "2026.04.27")
    monkeypatch.setattr(updates_routes, "get_latest_release_version_from_git", lambda: "2026.05.27.3")
    monkeypatch.setattr(updates_routes, "head_includes_release", lambda *a: False)

    res = await check_for_updates()
    assert res["latest_version"] == "2026.05.27.3"
    assert res["update_available"] is True
    assert res["method"] == "git_ls_remote"


@pytest.mark.asyncio
async def test_apply_update_refuses_in_container(monkeypatch):
    """Inside a container, apply_update returns HTTP 400 guiding user to docker compose."""
    from fastapi import HTTPException

    monkeypatch.setattr(updates_routes, "is_containerized", lambda: True)
    monkeypatch.setattr("app.api.routes.updates.require_admin_or_localhost_for_destructive_action", lambda *a: None)

    req = MagicMock()
    payload = updates_routes.UpdateConfirmation(confirm="APPLY_UPDATE")
    with pytest.raises(HTTPException) as exc_info:
        await apply_update(req, payload)

    assert exc_info.value.status_code == 400
    assert "docker compose pull" in exc_info.value.detail
