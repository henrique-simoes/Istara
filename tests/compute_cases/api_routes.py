from tests.compute_cases.common import *
from datetime import UTC, datetime, timedelta

from app.api.routes.compute import _scope_from_connection_string
from app.core.connection_string import (
    create_compute_donation_string,
    hash_connection_string,
    preview_connection_string,
)
from app.models.connection_string import ConnectionString
from app.models.database import async_session

async def test_compute_nodes_returns_list(auth_headers):
    """GET /api/compute/nodes returns compute nodes."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/nodes", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert "nodes" in body
        assert "total_nodes" in body


@pytest.mark.asyncio
async def test_compute_nodes_requires_auth():
    """Compute nodes requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/nodes")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_researcher_can_view_compute_pool(researcher_headers):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/stats", headers=researcher_headers)
    assert response.status_code == 200
    assert "nodes" in response.json()


@pytest.mark.asyncio
async def test_compute_stats_returns_response(auth_headers):
    """GET /api/compute/stats returns compute stats."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/stats", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "total_nodes" in body


@pytest.mark.asyncio
async def test_compute_donation_connection_string_resolves_project_scope(monkeypatch):
    await init_db()
    monkeypatch.setattr(settings, "network_access_token", "scoped-network-token")
    conn_str = create_compute_donation_string(
        "http://localhost:3000",
        ws_url="ws://localhost:8000/ws/relay",
        label="Scoped donor",
        allowed_project_ids=["project-a"],
    )
    async with async_session() as db:
        db.add(
            ConnectionString(
                connection_string=preview_connection_string(conn_str),
                connection_string_hash=hash_connection_string(conn_str),
                token_type="compute_donation",
                label="Scoped donor",
                server_url="http://localhost:3000",
                ws_url="ws://localhost:8000/ws/relay",
                intended_role="compute_node",
                allowed_project_ids_json='["project-a"]',
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await db.commit()
        scope, reason = await _scope_from_connection_string(db, conn_str)

    assert reason == "ok"
    assert scope == ["project-a"]
