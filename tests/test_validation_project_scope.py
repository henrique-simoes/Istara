"""Project-scope contracts for ensemble validation compute routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class _FakeValidationServer:
    def __init__(self, name: str, project_calls: list[str | None]) -> None:
        self.name = name
        self.is_healthy = True
        self.project_calls = project_calls

    async def chat(self, messages, **kwargs):  # noqa: ANN001
        self.project_calls.append(kwargs.get("project_id"))
        return {
            "message": {"content": f"{self.name} validation response"},
            "_istara_route": {
                "node_id": self.name,
                "node_source": "local",
                "provider_type": "fake",
                "route_kind": "chat",
                "project_id": kwargs.get("project_id") or "",
                "model": kwargs.get("model") or self.name,
                "outcome": "served",
            },
        }


class _FakeValidationRouter:
    def __init__(self) -> None:
        self.chat_project_calls: list[str | None] = []
        self.embed_project_calls: list[str | None] = []
        self.sorted_project_calls: list[str | None] = []
        self.server_project_calls: list[str | None] = []
        self.servers = [
            _FakeValidationServer("server-a", self.server_project_calls),
            _FakeValidationServer("server-b", self.server_project_calls),
            _FakeValidationServer("server-c", self.server_project_calls),
        ]

    def _sorted_servers(self, **kwargs):
        self.sorted_project_calls.append(kwargs.get("project_id"))
        return self.servers

    async def chat(self, messages, **kwargs):  # noqa: ANN001
        self.chat_project_calls.append(kwargs.get("project_id"))
        return {
            "message": {"content": "project scoped validation response"},
            "_istara_route": {
                "node_id": "router",
                "node_source": "local",
                "provider_type": "fake",
                "route_kind": "chat",
                "project_id": kwargs.get("project_id") or "",
                "model": kwargs.get("model") or "router-model",
                "outcome": "served",
            },
        }

    async def embed_batch(self, texts, **kwargs):  # noqa: ANN001
        self.embed_project_calls.append(kwargs.get("project_id"))
        return [[1.0, 0.0] for _ in texts]


@pytest.mark.asyncio
async def test_validation_helpers_forward_project_id_to_llm_and_embeddings(monkeypatch):
    from app.core import llm_router as llm_router_module
    from app.core import validation
    from app.core.agentic import agentic

    fake_router = _FakeValidationRouter()
    monkeypatch.setattr(llm_router_module, "llm_router", fake_router)
    # W8: consensus embeddings are dispatcher-routed; the project scope enters
    # through agentic.embed's engine resolution.
    embed_project_calls: list[str | None] = []

    async def embed_spy(**kwargs):  # noqa: ANN001
        embed_project_calls.append(kwargs.get("project_id"))
        return [[1.0, 0.0] for _ in (kwargs.get("texts") or [])]

    monkeypatch.setattr(agentic, "embed", embed_spy)

    adversarial = await validation.adversarial_review(
        "Review this",
        "Candidate output",
        project_id="project-a",
    )
    self_moa = await validation.self_moa("Validate this", n=2, project_id="project-a")
    debate = await validation.debate_rounds("Debate this", rounds=1, project_id="project-a")
    dual = await validation.dual_run("Compare this", project_id="project-a")
    ensemble = await validation.full_ensemble("Ensemble this", min_responses=2, project_id="project-a")

    assert fake_router.chat_project_calls == [
        "project-a",
        "project-a",
        "project-a",
        "project-a",
        "project-a",
    ]
    assert embed_project_calls == [
        "project-a",
        "project-a",
        "project-a",
        "project-a",
        "project-a",
    ]
    assert fake_router.sorted_project_calls == ["project-a", "project-a"]
    assert fake_router.server_project_calls == [
        "project-a",
        "project-a",
        "project-a",
        "project-a",
    ]
    assert adversarial.metadata["route_evidence"][0]["project_id"] == "project-a"
    assert self_moa.metadata["route_evidence"][0]["node_id"] == "router"
    assert debate.metadata["route_evidence"][0]["route_kind"] == "chat"
    assert dual.metadata["route_evidence"][0]["node_id"] == "server-a"
    assert ensemble.metadata["models_used"] == ["server-a", "server-b"]
    assert adversarial.metadata["validation_scope"] == "response_level_quality_signal"
    assert adversarial.metadata["formal_reliability"] is False
    assert debate.metadata["validation_scope"] == "response_level_quality_signal"
    assert debate.metadata["formal_reliability"] is False


@pytest.mark.asyncio
async def test_debate_and_adversarial_review_emit_coded_evidence_telemetry(monkeypatch):
    from app.core import llm_router as llm_router_module
    from app.core import validation
    from app.core import telemetry as telemetry_module

    fake_router = _FakeValidationRouter()
    record_event = AsyncMock()
    monkeypatch.setattr(llm_router_module, "llm_router", fake_router)
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
    assert debate.metadata["models_used"] == ["router-model", "router-model"]
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
    assert "llm_router._sorted_servers(project_id=project_id)" in validation_module
    assert "project_id=project_id" in validation_module
    # W8: consensus embeddings are dispatcher-routed, project scope intact.
    assert "agentic.embed(texts=texts, project_id=project_id)" in validation_module
