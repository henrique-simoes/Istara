"""Project-scope contracts for ensemble validation compute routing.

W9: the validation helpers no longer carry a per-site legacy branch — every
call enters through the AgenticDispatcher (``app.core.agentic.agentic``).
These tests stub that singleton and assert the active project scope is
forwarded into every dispatch and every consensus-embedding call.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class _StubAgenticDispatcher:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self) -> None:
        self.project_calls: list[str] = []
        self.embed_project_calls: list[str | None] = []

    async def completion(self, **kwargs):  # noqa: ANN001
        self.project_calls.append(kwargs.get("project_id") or "")
        return SimpleNamespace(
            text="dispatcher validation response",
            status="success",
            usage={},
            stop_reason="stop",
            endpoint_id="ep-stub",
            tool_calls=[],
        )

    async def ensemble(self, **kwargs):  # noqa: ANN001
        self.project_calls.append(kwargs.get("project_id") or "")
        n = kwargs.get("n") or 1
        samples = [
            SimpleNamespace(
                text=f"ensemble response {index}",
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id=f"ep-{index}",
                tool_calls=[],
            )
            for index in range(n)
        ]
        return SimpleNamespace(
            samples=samples,
            endpoint_ids=[f"ep-{index}" for index in range(n)],
            usage={},
            status="success",
        )

    async def embed(self, **kwargs):  # noqa: ANN001
        self.embed_project_calls.append(kwargs.get("project_id"))
        return [[1.0, 0.0] for _ in (kwargs.get("texts") or [])]


@pytest.mark.asyncio
async def test_validation_helpers_forward_project_id_to_llm_and_embeddings(monkeypatch):
    from app.core import validation

    stub = _StubAgenticDispatcher()
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    adversarial = await validation.adversarial_review(
        "Review this",
        "Candidate output",
        project_id="project-a",
    )
    self_moa = await validation.self_moa("Validate this", n=2, project_id="project-a")
    debate = await validation.debate_rounds("Debate this", rounds=1, project_id="project-a")
    dual = await validation.dual_run("Compare this", project_id="project-a")
    ensemble = await validation.full_ensemble("Ensemble this", min_responses=2, project_id="project-a")

    # 3 completions (adversarial + debate initial/round) + 3 ensembles
    # (self_moa, dual_run, full_ensemble) — every dispatch project-scoped.
    assert stub.project_calls == ["project-a"] * 6
    assert stub.embed_project_calls == ["project-a"] * 5
    assert adversarial.metadata["route_evidence"][0]["route_kind"] == "agentic_completion"
    assert adversarial.metadata["route_evidence"][0]["endpoint_id"] == "ep-stub"
    assert self_moa.metadata["assurance"] == "single_model_temperature_variation"
    assert debate.metadata["route_evidence"][0]["route_kind"] == "agentic_completion"
    assert dual.metadata["endpoint_ids"] == ["ep-0", "ep-1"]
    assert ensemble.metadata["n_responses"] == 3
    assert adversarial.metadata["validation_scope"] == "response_level_quality_signal"
    assert adversarial.metadata["formal_reliability"] is False
    assert debate.metadata["validation_scope"] == "response_level_quality_signal"
    assert debate.metadata["formal_reliability"] is False


@pytest.mark.asyncio
async def test_debate_and_adversarial_review_emit_coded_evidence_telemetry(monkeypatch):
    from app.core import validation
    from app.core import telemetry as telemetry_module

    stub = _StubAgenticDispatcher()
    record_event = AsyncMock()
    monkeypatch.setattr("app.core.agentic.agentic", stub)
    monkeypatch.setattr(
        telemetry_module.telemetry_recorder,
        "record_research_validity_event",
        record_event,
    )

    adversarial = await validation.adversarial_review(
        "Review coded evidence disagreement",
        "Candidate reconciliation",
        project_id="project-a",
        coding_run_id="coding-run-a",
        evidence_unit_ids=["evidence-unit-a"],
        codebook_version_id="codebook-v1",
        trace_id="trace-adversarial",
    )
    debate = await validation.debate_rounds(
        "Debate coded evidence disagreement",
        rounds=1,
        project_id="project-a",
        coding_run_id="coding-run-b",
        evidence_unit_ids=["evidence-unit-b"],
        codebook_version_id="codebook-v1",
        trace_id="trace-debate",
    )

    assert adversarial.metadata["validation_scope"] == "coded_evidence_review"
    assert adversarial.metadata["coding_run_id"] == "coding-run-a"
    assert adversarial.metadata["evidence_unit_ids"] == ["evidence-unit-a"]
    assert debate.metadata["validation_scope"] == "coded_evidence_review"
    assert len(debate.metadata["route_evidence"]) == 2
    operations = [call.kwargs["operation"] for call in record_event.await_args_list]
    assert operations == ["adversarial.review", "debate.review"]
    assert record_event.await_args_list[0].kwargs["coding_run_id"] == "coding-run-a"
    assert record_event.await_args_list[0].kwargs["evidence_unit_id"] == "evidence-unit-a"
    assert record_event.await_args_list[1].kwargs["coding_run_id"] == "coding-run-b"
    assert record_event.await_args_list[1].kwargs["evidence_unit_id"] == "evidence-unit-b"


def test_task_ensemble_validation_passes_active_project_scope() -> None:
    agent_execution = read_repo("backend/app/core/agent_execution.py")
    validation_module = read_repo("backend/app/core/validation.py")

    assert '"project_id": project.id' in agent_execution
    assert "project_id: str | None = None" in validation_module
    assert "project_id=project_id" in validation_module
    # W9: the helpers forward the active scope into every dispatcher call.
    assert 'project_id=project_id or ""' in validation_module
    # W8: consensus embeddings are dispatcher-routed, project scope intact.
    assert "agentic.embed(texts=texts, project_id=project_id)" in validation_module
