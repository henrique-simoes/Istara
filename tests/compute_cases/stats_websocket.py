import json
import uuid
from datetime import UTC, datetime, timedelta

from app.core.auth import hash_password
from app.core.auth_sessions import issue_auth_session_token
from app.core.connection_string import (
    create_compute_donation_string,
    hash_connection_string,
    preview_connection_string,
)
from app.core.field_encryption import hash_field
from app.models.connection_string import ConnectionString
from app.models.database import async_session
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User, UserRole
from tests.compute_cases.common import *

def test_compute_stats_include_capacity_envelope():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="busy-local",
            name="Busy Local",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            active_requests=2,
            max_active_requests=4,
            ram_total_gb=16,
            ram_available_gb=4,
            cpu_cores=8,
            cpu_load_pct=80,
            loaded_models=["llama3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="saturated-relay",
            name="Saturated Relay",
            host="",
            source="relay",
            provider_type="ollama",
            is_healthy=True,
            active_requests=2,
            max_active_requests=2,
            cpu_load_pct=50,
        )
    )

    stats = registry.get_stats()

    assert stats["request_slots_total"] == 6
    assert stats["request_slots_used"] == 4
    assert stats["request_slots_available"] == 2
    assert stats["saturated_nodes"] == 1
    assert stats["hardware_load_pct"] == 65.0


def test_relay_websocket_is_registered_at_connection_string_path():
    websocket_paths = {getattr(route, "path", "") for route in app.routes}

    assert "/ws/relay" in websocket_paths
    assert "/api/ws/relay" in websocket_paths


class FakeRelayWebSocket:
    def __init__(self, *, headers=None, query_params=None, messages=None):
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.client = type("Client", (), {"host": "10.0.0.22"})()
        self.messages = list(messages or [])
        self.accepted = False
        self.close_code = None
        self.close_reason = ""
        self.sent: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        self.close_code = code
        self.close_reason = reason

    async def receive_text(self):
        if not self.messages:
            raise WebSocketDisconnect()
        return self.messages.pop(0)

    async def send_json(self, payload: dict):
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_relay_websocket_rejects_missing_auth():
    ws = FakeRelayWebSocket()

    await relay_websocket(ws)

    assert not ws.accepted
    assert ws.close_code == 4001
    assert "Authentication required" in ws.close_reason


@pytest.mark.asyncio
async def test_relay_websocket_accepts_network_token_and_cleans_up_node():
    original_nodes = dict(compute_registry._nodes)
    original_network_token = settings.network_access_token
    try:
        compute_registry._nodes.clear()
        settings.network_access_token = "relay-test-token"
        ws = FakeRelayWebSocket(
            headers={"x-access-token": "relay-test-token"},
            messages=[
                '{"type":"register","hostname":"relay-host","user_id":"relay-user",'
                '"provider_type":"ollama","provider_host":"http://localhost:11434",'
                '"loaded_models":["llama3"],"ram_total_gb":16,"cpu_cores":8}'
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert compute_registry._nodes == {}
    finally:
        settings.network_access_token = original_network_token
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_relay_websocket_uses_registration_connection_string_scope(monkeypatch):
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        await init_db()
        monkeypatch.setattr(settings, "network_access_token", "relay-test-token")
        project_id = f"relay-project-{uuid.uuid4().hex}"
        conn_str = create_compute_donation_string(
            "http://localhost:3000",
            ws_url="ws://localhost:8000/ws/relay",
            label="Scoped relay donor",
            allowed_project_ids=[project_id],
        )
        async with async_session() as db:
            db.add(
                ConnectionString(
                    connection_string=preview_connection_string(conn_str),
                    connection_string_hash=hash_connection_string(conn_str),
                    token_type="compute_donation",
                    label="Scoped relay donor",
                    server_url="http://localhost:3000",
                    ws_url="ws://localhost:8000/ws/relay",
                    intended_role="compute_node",
                    allowed_project_ids_json=json.dumps([project_id]),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            await db.commit()

        ws = FakeRelayWebSocket(
            headers={"x-access-token": "relay-test-token"},
            messages=[
                json.dumps(
                    {
                        "type": "register",
                        "hostname": "relay-host",
                        "user_id": "relay-user",
                        "provider_type": "openai_compat",
                        "provider_host": "http://host.docker.internal:18112",
                        "loaded_models": ["qwen-test"],
                        "connection_string": conn_str,
                    }
                )
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert ws.sent[0]["authorized_project_count"] == 1
        assert compute_registry._nodes == {}
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_relay_websocket_accepts_browser_jwt():
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        token = create_token("browser-user", "donor", "researcher")
        ws = FakeRelayWebSocket(
            query_params={"token": token},
            messages=[
                '{"type":"register","hostname":"browser","user_id":"browser",'
                '"provider_type":"lmstudio","provider_host":"http://localhost:1234",'
                '"loaded_models":["local-model"]}'
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert compute_registry._nodes == {}
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_relay_websocket_bound_jwt_uses_current_db_role_for_scope():
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        await init_db()
        suffix = uuid.uuid4().hex
        user_id = f"relay-donor-{suffix}"
        project_id = f"relay-project-{suffix}"
        email = f"relay-donor-{suffix}@example.test"

        async with async_session() as db:
            user = User(
                id=user_id,
                username=f"relay-donor-{suffix}",
                email=email,
                email_hash=hash_field(email),
                password_hash=hash_password("relay-test-password"),
                role=UserRole.ADMIN,
                display_name="Relay Donor",
            )
            db.add_all(
                [
                    user,
                    Project(
                        id=project_id,
                        name="Relay Donor Project",
                        owner_id=user_id,
                    ),
                    ProjectMember(
                        id=f"relay-member-{suffix}",
                        project_id=project_id,
                        user_id=user_id,
                        role="researcher",
                        added_by=user_id,
                    ),
                ]
            )
            await db.commit()
            token = await issue_auth_session_token(db, user, None, mfa_verified=True)
            user.role = UserRole.RESEARCHER
            await db.commit()

        ws = FakeRelayWebSocket(
            query_params={"token": token},
            messages=[
                '{"type":"register","hostname":"browser","user_id":"browser",'
                '"provider_type":"lmstudio","loaded_models":["local-model"]}'
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert ws.sent[0]["authorized_project_count"] == 1
        assert compute_registry._nodes == {}
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)
