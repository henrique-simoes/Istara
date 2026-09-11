"""Tests for mid-execution steering infrastructure and API routes.

Tests cover:
- SteeringQueue: enqueue, drain (one-at-a-time vs all modes), clear, count, has_items
- SteeringManager: steer, follow_up, get_steering, get_follow_up, clear_all,
  mark_working, mark_idle, is_working, wait_for_idle, abort, get_status
- API routes: all 7 endpoints with validation
- WebSocket events: steering_message, agent_idle broadcast structure
"""

import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

# ---------- Backend path setup ----------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.steering import (
    SteeringMessage,
    SteeringQueue,
    SteeringManager,
)
from app.main import app
from app.config import settings
from app.models.agent import Agent
from app.models.database import async_session, init_db
from app.models.project import Project
from app.api.websocket import (
    broadcast_steering_message,
    broadcast_steering_response,
    broadcast_agent_idle,
    manager as ws_manager,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def manager():
    """Fresh SteeringManager for each test."""
    return SteeringManager()


@pytest.fixture
def agent_id():
    return "test-agent-001"


@pytest.fixture(autouse=True)
def configure_settings():
    """Ensure JWT secret is set so middleware passes in local mode."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-steering-secret"
    settings.team_mode = False


@pytest.fixture
def auth_headers():
    """Generate a valid JWT token for test requests."""
    from app.core.auth import create_token

    token = create_token("local", "test-user", "admin")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _seed_project(name: str | None = None) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        name=name or f"Steering Project {uuid.uuid4()}",
    )
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


@pytest.fixture
async def steering_project_id():
    await init_db()
    project = await _seed_project()
    return project.id


# ============================================================
# Unit Tests: SteeringQueue
# ============================================================


class TestSteeringAPI:
    """HTTP endpoint tests using httpx ASGITransport."""

    @pytest.fixture(autouse=True)
    async def clear_queues(self):
        """Clear all steering queues before each test."""
        from app.core.steering import steering_manager

        steering_manager._agents.clear()

    @pytest.mark.asyncio
    async def test_queue_steering_message(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            resp = await ac.post(
                "/api/steering/istara-main",
                json={
                    "message": "Check the new UI for contrast issues",
                    "project_id": steering_project_id,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert data["agent_id"] == "istara-main"
            assert data["project_id"] == steering_project_id
            assert data["queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_queue_follow_up_message(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            resp = await ac.post(
                "/api/steering/istara-main/follow-up",
                json={
                    "message": "Run final accessibility audit",
                    "project_id": steering_project_id,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert data["project_id"] == steering_project_id
            assert data["queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_steering_status(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "test", "project_id": steering_project_id},
            )
            resp = await ac.get(
                f"/api/steering/istara-main/status?project_id={steering_project_id}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent_id"] == "istara-main"
            assert data["project_id"] == steering_project_id
            assert data["steering_queue_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_steering_queues(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "steer msg", "project_id": steering_project_id},
            )
            await ac.post(
                "/api/steering/istara-main/follow-up",
                json={"message": "follow msg", "project_id": steering_project_id},
            )
            resp = await ac.get(
                f"/api/steering/istara-main/queues?project_id={steering_project_id}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == steering_project_id
            assert len(data["steering_queue"]) >= 1
            assert len(data["follow_up_queue"]) >= 1
            assert data["steering_queue"][0]["message"] == "steer msg"
            assert (
                data["steering_queue"][0]["metadata"]["project_id"]
                == steering_project_id
            )

    @pytest.mark.asyncio
    async def test_clear_queues(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "test", "project_id": steering_project_id},
            )
            resp = await ac.delete(
                f"/api/steering/istara-main/queues?project_id={steering_project_id}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "cleared"
            assert data["project_id"] == steering_project_id
            assert data["cleared_steering_count"] >= 1

    @pytest.mark.asyncio
    async def test_abort(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "test", "project_id": steering_project_id},
            )
            resp = await ac.post(
                f"/api/steering/istara-main/abort?project_id={steering_project_id}",
                json={},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == steering_project_id
            assert "cleared_steering_count" in data

    @pytest.mark.asyncio
    async def test_get_all_steering_status(self, auth_headers, steering_project_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            resp = await ac.get(f"/api/steering?project_id={steering_project_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_empty_agent_id_returns_error(self, auth_headers):
        """Empty agent ID should be rejected or redirect."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers,
            follow_redirects=False,
        ) as ac:
            resp = await ac.post("/api/steering/", json={"message": "test"})
            # FastAPI redirects /api/steering/ to /api/steering (no trailing slash)
            assert resp.status_code in (307, 404, 405)

    @pytest.mark.asyncio
    async def test_steering_message_persists_across_requests(
        self, auth_headers, steering_project_id
    ):
        """Verify that a queued message survives across separate HTTP requests."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "persistent msg", "project_id": steering_project_id},
            )
            resp = await ac.get(
                f"/api/steering/istara-main/queues?project_id={steering_project_id}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["steering_queue"]) >= 1
            assert data["steering_queue"][0]["message"] == "persistent msg"

    @pytest.mark.asyncio
    async def test_missing_project_id_is_rejected(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            post_resp = await ac.post(
                "/api/steering/istara-main", json={"message": "test"}
            )
            status_resp = await ac.get("/api/steering/istara-main/status")
            all_resp = await ac.get("/api/steering")

        assert post_resp.status_code == 422
        assert status_resp.status_code == 400
        assert status_resp.json()["detail"] == "project_id is required"
        assert all_resp.status_code == 400
        assert all_resp.json()["detail"] == "project_id is required"

    @pytest.mark.asyncio
    async def test_same_agent_queues_are_filtered_by_project(self, auth_headers):
        project_a = await _seed_project("Steering A")
        project_b = await _seed_project("Steering B")

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "project a message", "project_id": project_a.id},
            )
            await ac.post(
                "/api/steering/istara-main",
                json={"message": "project b message", "project_id": project_b.id},
            )
            queues_a = await ac.get(
                f"/api/steering/istara-main/queues?project_id={project_a.id}"
            )
            queues_b = await ac.get(
                f"/api/steering/istara-main/queues?project_id={project_b.id}"
            )
            clear_a = await ac.delete(
                f"/api/steering/istara-main/queues?project_id={project_a.id}"
            )
            queues_b_after = await ac.get(
                f"/api/steering/istara-main/queues?project_id={project_b.id}"
            )

        assert [msg["message"] for msg in queues_a.json()["steering_queue"]] == [
            "project a message"
        ]
        assert [msg["message"] for msg in queues_b.json()["steering_queue"]] == [
            "project b message"
        ]
        assert clear_a.json()["cleared_steering_count"] == 1
        assert [msg["message"] for msg in queues_b_after.json()["steering_queue"]] == [
            "project b message"
        ]

    @pytest.mark.asyncio
    async def test_project_scoped_agent_rejects_other_project_steering(
        self, auth_headers
    ):
        project_a = await _seed_project("Steering Target A")
        project_b = await _seed_project("Steering Target B")
        agent_id = f"project-agent-{uuid.uuid4()}"
        async with async_session() as db:
            db.add(
                Agent(
                    id=agent_id,
                    name="Project Agent",
                    scope="project",
                    project_id=project_b.id,
                )
            )
            await db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=auth_headers
        ) as ac:
            rejected = await ac.post(
                f"/api/steering/{agent_id}",
                json={"message": "wrong project", "project_id": project_a.id},
            )
            accepted = await ac.post(
                f"/api/steering/{agent_id}",
                json={"message": "right project", "project_id": project_b.id},
            )

        assert rejected.status_code == 404
        assert accepted.status_code == 200


# ============================================================
# WebSocket Event Tests
# ============================================================
