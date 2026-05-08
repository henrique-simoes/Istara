"""Tests for Compute API routes — nodes, stats."""

import asyncio

import httpx
import pytest
from app.api.routes.compute import _infer_relay_provider_type, relay_websocket
from app.api.routes import settings as settings_routes
from app.config import settings
from app.core.auth import create_token
from app.core.compute_registry import ComputeNode, ComputeRegistry, compute_registry
from app.core.lmstudio import LMStudioClient, configured_lmstudio_model_is_authoritative
from app.main import app, _build_configured_local_llm_node
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_provider = settings.llm_provider
    original_lmstudio_host = settings.lmstudio_host
    original_lmstudio_model = settings.lmstudio_model
    original_lmstudio_api_key = settings.lmstudio_api_key
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.llm_provider = original_provider
    settings.lmstudio_host = original_lmstudio_host
    settings.lmstudio_model = original_lmstudio_model
    settings.lmstudio_api_key = original_lmstudio_api_key


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def researcher_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher1", "researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


__all__ = [name for name in globals() if not name.startswith("__")]
