"""Browser transport contract for the chat agent-engine selector."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_chat_preflight_allows_the_agent_engine_header() -> None:
    origin = next(item.strip() for item in settings.cors_origins.split(",") if item.strip())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/chat",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,content-type,x-istara-agent-engine"
                ),
            },
        )

    assert response.status_code == 200, response.text
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-istara-agent-engine" in allowed_headers


@pytest.mark.asyncio
async def test_chat_preflight_does_not_broaden_origin_trust() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/chat",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-istara-agent-engine",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
