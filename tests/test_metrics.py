"""Tests for validation metrics aggregation and statistical rigor fields."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.database import async_session, init_db
from app.models.method_metric import MethodMetric
from app.models.project import Project


@pytest.mark.asyncio
async def test_validation_metrics_aggregate_method_contexts_with_intervals(admin_auth_headers):
    await init_db()
    project_id = f"metrics-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        db.add(Project(id=project_id, name="Metrics Project"))
        db.add_all(
            [
                MethodMetric(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    skill_name="interviews",
                    agent_id="agent-a",
                    method="dual_run",
                    total_runs=4,
                    success_count=3,
                    fail_count=1,
                    avg_consensus_score=0.6,
                    weight=1.0,
                    last_used=now - timedelta(days=1),
                ),
                MethodMetric(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    skill_name="synthesis",
                    agent_id="agent-b",
                    method="dual_run",
                    total_runs=6,
                    success_count=6,
                    fail_count=0,
                    avg_consensus_score=0.8,
                    weight=2.0,
                    last_used=now,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/metrics/{project_id}/validation",
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    dual_run = next(row for row in body["method_stats"] if row["method"] == "dual_run")
    assert dual_run["total_runs"] == 10
    assert dual_run["success_count"] == 9
    assert dual_run["fail_count"] == 1
    assert dual_run["avg_consensus_score"] == 0.72
    assert dual_run["success_rate"] == 0.9
    assert dual_run["context_count"] == 2
    assert 0 <= dual_run["success_rate_ci_low"] <= dual_run["success_rate_ci_high"] <= 1
    assert dual_run["sample_confidence_weight"] == 1.0
    assert dual_run["rigor_status"] == "stable_sample"
    assert "Wilson 95% confidence intervals" in body["statistical_notes"]["success_rate"]
