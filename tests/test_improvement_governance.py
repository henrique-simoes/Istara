"""Tests for system-wide improvement governance."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth import create_token
from app.core.dgmh_archive import dgmh_archive
from app.core.improvement_governance import improvement_governance
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


def test_governance_policy_separates_learning_from_behavioral_mutations():
    auto = improvement_governance.classify_policy(
        affected_surfaces=["memory", "telemetry"],
        source_system="reasoning_bank",
        risk_level="low",
    )
    assert auto["approval_policy"] == "auto_apply"
    assert auto["requires_human_approval"] is False

    prompt_change = improvement_governance.classify_policy(
        affected_surfaces=["skills", "prompts"],
        source_system="memento",
    )
    assert prompt_change["approval_policy"] == "approval_required"
    assert prompt_change["requires_human_approval"] is True

    backend_change = improvement_governance.classify_policy(
        affected_surfaces=["backend_code", "integrations"],
        source_system="autoresearch",
    )
    assert backend_change["approval_policy"] == "admin_required"
    assert backend_change["risk_level"] == "critical"


@pytest.mark.asyncio
async def test_governance_lifecycle_redacts_evaluates_and_reverts():
    await init_db()
    source_id = f"ig_{uuid.uuid4().hex[:12]}"

    proposal = await improvement_governance.create_proposal(
        source_system="manual",
        source_id=source_id,
        project_id="project-governance-lifecycle",
        title="Tune interview transcription prompt",
        summary="Improve bilingual transcription instructions",
        affected_surfaces=["prompts", "skills"],
        proposed_change={"prompt": "detect language", "api_key": "secret-value"},
        rollback_plan={"strategy": "restore previous prompt"},
        evidence=[{"kind": "test"}],
        confidence=0.8,
    )

    assert proposal.status == "proposed"
    assert proposal.requires_human_approval is True
    assert proposal.get_proposed_change()["api_key"] == "[REDACTED]"

    blocked = await improvement_governance.apply_proposal(proposal.id, actor_id="user1")
    assert "approval required" in blocked["error"]

    approved = await improvement_governance.approve_proposal(proposal.id, reviewer_id="user1")
    assert approved["proposal"]["status"] == "approved"

    applied = await improvement_governance.apply_proposal(
        proposal.id,
        actor_id="user1",
        evidence={"command": "pytest tests/test_improvement_governance.py"},
    )
    assert applied["proposal"]["status"] == "applied"

    evaluated = await improvement_governance.record_evaluation(
        proposal.id,
        metrics_before={"accuracy": 0.7},
        metrics_after={"accuracy": 0.8},
        passed=True,
    )
    assert evaluated["proposal"]["evaluation_runs"][-1]["passed"] is True

    reverted = await improvement_governance.revert_proposal(
        proposal.id,
        actor_id="user1",
        reason="test rollback",
    )
    assert reverted["proposal"]["status"] == "reverted"


@pytest.mark.asyncio
async def test_governance_api_contract_and_admin_guard(auth_headers):
    await init_db()
    settings.team_mode = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/improvement-governance/proposals",
            headers=auth_headers,
            json={
                "source_system": "reasoning_bank",
                "source_id": "api-auto-learning",
                "title": "Record safe reasoning memory",
                "affected_surfaces": ["memory", "telemetry"],
                "risk_level": "low",
                "proposed_change": {"memory": "safe distilled trace"},
                "rollback_plan": {"strategy": "delete or quarantine memory"},
            },
        )
        assert created.status_code == 200
        proposal = created.json()["proposal"]
        assert proposal["status"] == "applied"
        assert proposal["auto_apply_allowed"] is True

        listed = await ac.get(
            "/api/improvement-governance/proposals?source_system=reasoning_bank",
            headers=auth_headers,
        )
        assert listed.status_code == 200
        assert any(item["id"] == proposal["id"] for item in listed.json()["proposals"])

        feature_contract = await ac.get(
            "/api/improvement-governance/feature-contract",
            headers=auth_headers,
        )
        assert feature_contract.status_code == 200
        features = {item["feature"] for item in feature_contract.json()["features"]}
        assert "dgmh_archive_evolution" in features
        assert "karpathy_autoresearch" in features
        assert "interviews_audio_upload_transcription_tagging_documents" in features

    token = create_token("user2", "researcher", "researcher")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.get(
            "/api/improvement-governance/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_autoresearch_kept_experiment_registers_governance_proposal():
    await init_db()
    experiment_id = f"exp_{uuid.uuid4().hex[:12]}"

    proposal_ids = await improvement_governance.register_autoresearch_experiment(
        {
            "id": experiment_id,
            "loop_type": "model_temp",
            "target_name": "thematic-analysis",
            "hypothesis": "Lower temperature for more stable coding.",
            "mutation_description": "temperature 0.7 -> 0.4",
            "baseline_score": 0.62,
            "experiment_score": 0.71,
            "delta": 0.09,
            "kept": True,
            "decision_reason": "delta exceeds configured minimum and uncertainty guard",
            "score_samples": [0.70, 0.72],
        },
        project_id="project-autoresearch-governance",
        reasoning_memory_ids=["memory-1"],
    )

    assert proposal_ids
    proposals = await improvement_governance.list_proposals(
        source_system="autoresearch",
        project_id="project-autoresearch-governance",
    )
    proposal = next(item for item in proposals if item["id"] == proposal_ids[0])
    assert proposal["approval_policy"] == "admin_required"
    assert "compute" in proposal["affected_surfaces"]
    assert proposal["reasoning_memory_ids"] == ["memory-1"]
    variants = await dgmh_archive.list_variants(
        source_system="autoresearch",
        project_id="project-autoresearch-governance",
    )
    assert any(item["governance_proposal_id"] == proposal["id"] for item in variants)

    skipped = await improvement_governance.register_autoresearch_experiment(
        {
            "id": "experiment-governance-reverted",
            "loop_type": "model_temp",
            "kept": False,
        },
        project_id="project-autoresearch-governance",
    )
    assert skipped == []


@pytest.mark.asyncio
async def test_hyperagent_proposal_registers_governance_contract():
    await init_db()
    meta_proposal_id = f"mp_test_{uuid.uuid4().hex[:12]}"

    proposal_id = await improvement_governance.register_meta_proposal(
        {
            "id": meta_proposal_id,
            "target_system": "skill_selection",
            "parameter_path": "agent.skill_similarity_threshold",
            "current_value": 0.6,
            "proposed_value": 0.5,
            "reason": "Semantic fallback rate exceeded threshold.",
            "expected_impact": "More accurate skill routing.",
            "evidence": [{"metric": "semantic_fallback_rate", "value": 0.45}],
            "confidence": 60,
        }
    )

    proposal = await improvement_governance.get_proposal_by_source(
        source_system="hyperagent",
        source_id=meta_proposal_id,
    )
    assert proposal is not None
    assert proposal.id == proposal_id
    assert proposal.status == "proposed"
    assert set(proposal.get_affected_surfaces()) >= {"skills", "orchestration", "configs"}
    variants = await dgmh_archive.list_variants(source_system="hyperagent")
    assert any(item["governance_proposal_id"] == proposal.id for item in variants)


@pytest.mark.asyncio
async def test_feature_evidence_records_auto_applied_proposal_and_archive_variant():
    await init_db()
    evidence_id = f"transcription-doc-{uuid.uuid4().hex[:8]}"

    recorded = await improvement_governance.record_feature_evidence(
        feature="interviews_audio_upload_transcription_tagging_documents",
        source_system="transcription",
        source_id=evidence_id,
        project_id="project-feature-evidence",
        evidence={
            "passed": True,
            "language": "pt",
            "detected_language": "pt",
            "confidence": 0.88,
        },
        metrics_after={"confidence": 0.88, "needs_review": False},
        confidence=0.88,
    )

    proposal = await improvement_governance.get_proposal(recorded["proposal_id"])
    assert proposal is not None
    assert proposal.status == "applied"
    assert proposal.approval_policy == "auto_apply"
    assert proposal.get_proposed_change()["evidence_only"] is True

    variants = await dgmh_archive.list_variants(
        source_system="transcription",
        project_id="project-feature-evidence",
    )
    assert any(item["governance_proposal_id"] == proposal.id for item in variants)
