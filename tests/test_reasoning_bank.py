"""Tests for ReasoningBank memory service and API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.core.reasoning_bank import reasoning_bank
from app.main import app
from app.models.database import init_db


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


@pytest.mark.asyncio
async def test_reasoning_bank_redacts_and_retrieves_project_scoped_memory():
    await init_db()

    project_id = "reasoning-project-redaction"
    stored = await reasoning_bank.record_trace(
        project_id=project_id,
        agent_id="istara-main",
        query="transcribe mixed language interview audio",
        trajectory={
            "decision": "Use transcription skill with explicit language detection.",
            "api_key": "super-secret-value",
        },
        outcome="success",
        source_kind="skill",
        source_id="task-redaction",
        tags=["transcription", "language-detection"],
        domain="interviews",
        judge_score=0.9,
    )

    assert stored
    assert "super-secret-value" not in stored[0]["content"]
    assert "[REDACTED]" in stored[0]["content"]

    matches = await reasoning_bank.retrieve(
        project_id=project_id,
        query="mixed language transcription detection interview",
        limit=3,
    )
    assert any(item["id"] == stored[0]["id"] for item in matches)

    isolated = await reasoning_bank.retrieve(
        project_id="other-project",
        query="mixed language transcription detection interview",
        limit=3,
    )
    assert all(item["id"] != stored[0]["id"] for item in isolated)


@pytest.mark.asyncio
async def test_reasoning_bank_records_autoresearch_failures():
    await init_db()

    memories = await reasoning_bank.record_autoresearch_experiment(
        {
            "id": "experiment-reverted",
            "loop_type": "model_temp",
            "target_name": "kappa-thematic-analysis",
            "hypothesis": "Increase temperature to improve synthesis.",
            "mutation_description": "temperature 0.7 -> 1.2",
            "baseline_score": 0.61,
            "experiment_score": 0.60,
            "delta": -0.01,
            "decision_reason": "delta below minimum",
            "kept": False,
            "status": "reverted",
        },
        project_id="reasoning-project-autoresearch",
    )

    assert memories[0]["source_kind"] == "autoresearch"
    assert memories[0]["outcome"] == "failure"
    assert "temperature" in memories[0]["content"]


@pytest.mark.asyncio
async def test_reasoning_bank_api_creates_and_retrieves_memory(auth_headers):
    await init_db()
    settings.team_mode = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/reasoning-bank/memories",
            headers=auth_headers,
            json={
                "project_id": "reasoning-project-api",
                "source_kind": "manual",
                "outcome": "success",
                "title": "Use bilingual transcription guard",
                "content": "When Portuguese and English appear together, keep language auto-detect enabled.",
                "tags": ["transcription", "language-detection"],
                "confidence": 0.8,
            },
        )
        assert created.status_code == 200

        retrieved = await ac.post(
            "/api/reasoning-bank/retrieve",
            headers=auth_headers,
            json={
                "project_id": "reasoning-project-api",
                "query": "Portuguese English transcription language detection",
                "limit": 5,
            },
        )
        assert retrieved.status_code == 200
        body = retrieved.json()
        assert body["memories"]
        assert "Relevant Reasoning Memory" in body["context"]


@pytest.mark.asyncio
async def test_reasoning_bank_api_requires_admin_role():
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user2", "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/reasoning-bank/summary",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
