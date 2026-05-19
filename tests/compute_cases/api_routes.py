from datetime import UTC, datetime, timedelta
import uuid

from tests.compute_cases.common import *

from app.api.routes.compute import _scope_from_connection_string
from app.core.connection_string import (
    create_compute_donation_string,
    hash_connection_string,
    preview_connection_string,
)
from app.models.connection_string import ConnectionString
from app.models.database import async_session
from app.models.project import Project
from app.models.project_member import ProjectMember

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
    project_id = f"project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Compute Visibility Project"))
        db.add(
            ProjectMember(
                id=f"member-{uuid.uuid4()}",
                project_id=project_id,
                user_id="researcher1",
                role="researcher",
            )
        )
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/compute/stats?project_id={project_id}",
            headers=researcher_headers,
        )
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
async def test_team_researcher_compute_stats_requires_active_project(researcher_headers):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/stats", headers=researcher_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_team_researcher_compute_stats_requires_project_membership(researcher_headers):
    await init_db()
    settings.team_mode = True
    project_id = f"project-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Project A"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/compute/stats?project_id={project_id}",
            headers=researcher_headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_team_researcher_compute_stats_filters_relay_nodes_to_active_project(
    researcher_headers,
):
    await init_db()
    settings.team_mode = True
    project_a = f"project-{uuid.uuid4()}"
    project_b = f"project-{uuid.uuid4()}"
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        async with async_session() as db:
            db.add_all(
                [
                    Project(id=project_a, name="Project A"),
                    Project(id=project_b, name="Project B"),
                    ProjectMember(
                        id=f"member-{uuid.uuid4()}",
                        project_id=project_a,
                        user_id="researcher1",
                        role="researcher",
                    ),
                ]
            )
            await db.commit()

        compute_registry.register_node(
            ComputeNode(
                node_id="local",
                name="Server Local",
                host="http://localhost:1234",
                source="local",
                provider_type="lmstudio",
                is_healthy=True,
                ram_total_gb=36,
                ram_available_gb=18,
                cpu_cores=12,
                loaded_models=["local-model"],
            )
        )
        compute_registry.register_node(
            ComputeNode(
                node_id="relay-a",
                name="Project A Relay",
                host="",
                source="relay",
                provider_type="ollama",
                is_healthy=True,
                ram_total_gb=16,
                ram_available_gb=8,
                cpu_cores=8,
                loaded_models=["llama3"],
                allowed_project_ids=[project_a],
            )
        )
        compute_registry.register_node(
            ComputeNode(
                node_id="relay-b",
                name="Project B Relay",
                host="",
                source="relay",
                provider_type="ollama",
                is_healthy=True,
                ram_total_gb=24,
                ram_available_gb=20,
                cpu_cores=10,
                loaded_models=["other-model"],
                allowed_project_ids=[project_b],
            )
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                f"/api/compute/stats?project_id={project_a}",
                headers=researcher_headers,
            )

        assert response.status_code == 200
        body = response.json()
        node_ids = {node["node_id"] for node in body["nodes"]}
        assert node_ids == {"local", "relay-a"}
        assert body["total_ram_gb"] == 52
        assert "other-model" not in body["available_models"]
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_compute_model_warnings_are_project_scoped(researcher_headers):
    await init_db()
    settings.team_mode = True
    project_a = f"project-{uuid.uuid4()}"
    project_b = f"project-{uuid.uuid4()}"
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        async with async_session() as db:
            db.add_all(
                [
                    Project(id=project_a, name="Project A"),
                    Project(id=project_b, name="Project B"),
                    ProjectMember(
                        id=f"member-{uuid.uuid4()}",
                        project_id=project_a,
                        user_id="researcher1",
                        role="researcher",
                    ),
                ]
            )
            await db.commit()

        compute_registry.register_node(
            ComputeNode(
                node_id="relay-a",
                name="Project A Relay",
                host="",
                source="relay",
                provider_type="ollama",
                is_healthy=True,
                model_capabilities={
                    "project-a-model": {
                        "supports_tools": False,
                        "context_length": 8192,
                    }
                },
                allowed_project_ids=[project_a],
            )
        )
        compute_registry.register_node(
            ComputeNode(
                node_id="relay-b",
                name="Project B Relay",
                host="",
                source="relay",
                provider_type="ollama",
                is_healthy=True,
                model_capabilities={
                    "project-b-model": {
                        "supports_tools": False,
                        "context_length": 8192,
                    }
                },
                allowed_project_ids=[project_b],
            )
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                f"/api/compute/model-warnings?project_id={project_a}",
                headers=researcher_headers,
            )

        assert response.status_code == 200
        warnings = response.json()["warnings"]
        assert {warning["server"] for warning in warnings} == {"Project A Relay"}
        assert all("project-b-model" not in warning["model"] for warning in warnings)
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


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


@pytest.mark.asyncio
async def test_team_mode_rejects_wildcard_compute_donation_scope(monkeypatch):
    await init_db()
    settings.team_mode = True
    monkeypatch.setattr(settings, "network_access_token", "scoped-network-token")
    conn_str = create_compute_donation_string(
        "http://localhost:3000",
        ws_url="ws://localhost:8000/ws/relay",
        label="Legacy wildcard donor",
        allowed_project_ids=["*"],
    )
    async with async_session() as db:
        db.add(
            ConnectionString(
                connection_string=preview_connection_string(conn_str),
                connection_string_hash=hash_connection_string(conn_str),
                token_type="compute_donation",
                label="Legacy wildcard donor",
                server_url="http://localhost:3000",
                ws_url="ws://localhost:8000/ws/relay",
                intended_role="compute_node",
                allowed_project_ids_json='["*"]',
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await db.commit()
        scope, reason = await _scope_from_connection_string(db, conn_str)

    assert reason == "wildcard_scope"
    assert scope == []
