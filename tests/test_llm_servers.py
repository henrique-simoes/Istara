"""Tests for LLM Servers API routes — CRUD, health-check, discover."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.core.compute_registry import ComputeNode, compute_registry
from app.api.routes.llm_servers import _is_local_host


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


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
    token = create_token("user2", "researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_llm_servers_list_returns_list(auth_headers):
    """GET /api/llm-servers returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/llm-servers", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_llm_servers_list_requires_auth():
    """LLM servers listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/llm-servers")
        assert response.status_code == 401


def test_local_server_detection_rejects_remote_hosts_marked_local():
    assert _is_local_host("http://localhost:11434")
    assert _is_local_host("127.0.0.1:1234")
    assert not _is_local_host("http://192.168.1.25:11434")
    assert not _is_local_host("https://istara.example.com")


@pytest.mark.asyncio
async def test_update_llm_server_refreshes_live_compute_node(auth_headers, monkeypatch):
    await init_db()
    original_nodes = dict(compute_registry._nodes)

    async def fake_health(self):
        self.provider_type = "lmstudio" if self.host.endswith(":1234") else self.provider_type
        self.is_healthy = True
        self.latency_ms = 12.5
        self.loaded_models = ["local-model"]
        self.model_capabilities = {"local-model": {"supports_tools": True}}
        self.health_error = ""
        return True

    monkeypatch.setattr(ComputeNode, "check_health", fake_health)
    compute_registry._nodes.clear()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            created = await ac.post(
                "/api/llm-servers",
                headers=auth_headers,
                json={
                    "name": "Local Ollama",
                    "provider_type": "ollama",
                    "host": "http://localhost:11434",
                    "is_local": True,
                },
            )
            assert created.status_code == 200
            server_id = created.json()["id"]
            assert compute_registry._nodes[server_id].host == "http://localhost:11434"

            updated = await ac.patch(
                f"/api/llm-servers/{server_id}",
                headers=auth_headers,
                json={
                    "name": "Local LM Studio",
                    "provider_type": "ollama",
                    "host": "http://localhost:1234",
                },
            )
            assert updated.status_code == 200
            body = updated.json()
            assert body["provider_type"] == "lmstudio"
            assert body["host"] == "http://localhost:1234"
            assert body["is_healthy"] is True

            node = compute_registry._nodes[server_id]
            assert node.host == "http://localhost:1234"
            assert node.provider_type == "lmstudio"
            assert node.loaded_models == ["local-model"]
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_health_check_reregisters_persisted_server_if_runtime_node_is_missing(
    auth_headers, monkeypatch
):
    await init_db()
    original_nodes = dict(compute_registry._nodes)

    async def fake_health(self):
        self.is_healthy = True
        self.latency_ms = 7.0
        self.loaded_models = ["recovered-model"]
        return True

    monkeypatch.setattr(ComputeNode, "check_health", fake_health)
    compute_registry._nodes.clear()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            created = await ac.post(
                "/api/llm-servers",
                headers=auth_headers,
                json={
                    "name": "Recoverable",
                    "provider_type": "openai_compat",
                    "host": "http://localhost:1234",
                    "is_local": True,
                },
            )
            assert created.status_code == 200
            server_id = created.json()["id"]

            compute_registry.unregister_server(server_id)
            assert server_id not in compute_registry._nodes

            health = await ac.post(
                f"/api/llm-servers/{server_id}/health-check",
                headers=auth_headers,
                json={},
            )
            assert health.status_code == 200
            assert health.json()["healthy"] is True
            assert compute_registry._nodes[server_id].loaded_models == ["recovered-model"]
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_researcher_can_discover_shared_llm_servers(researcher_headers, monkeypatch):
    await init_db()
    settings.team_mode = True

    async def fake_discover_and_register():
        return [{"name": "LAN Studio", "host": "http://10.0.0.10:1234"}]

    monkeypatch.setattr(
        "app.core.network_discovery.discover_and_register",
        fake_discover_and_register,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/llm-servers/discover", headers=researcher_headers)
        assert response.status_code == 200
        assert response.json()["discovered"] == 1


@pytest.mark.asyncio
async def test_researcher_can_add_remote_shared_llm_server(researcher_headers, monkeypatch):
    await init_db()
    settings.team_mode = True

    async def fake_health(self):
        self.is_healthy = True
        self.latency_ms = 3.0
        self.loaded_models = ["donated-model"]
        self.model_capabilities = {"donated-model": {"supports_tools": True}}
        return True

    monkeypatch.setattr(ComputeNode, "check_health", fake_health)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/llm-servers",
            headers=researcher_headers,
            json={
                "name": "Remote LAN",
                "provider_type": "ollama",
                "host": "http://192.168.1.25:11434",
                "is_local": True,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["host"] == "http://192.168.1.25:11434"
        assert body["is_healthy"] is True
