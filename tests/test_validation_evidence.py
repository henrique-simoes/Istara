"""Route-evidence integrity for multi-model validation methods.

F-M2/F-M4 regressions: ensemble sample failures must carry their reason, and
adversarial reviews must record which model criticized (not just that a
critique happened). Uses scripted dispatchers — no live models.
"""

import pytest

from app.core.agentic.types import EnsembleResult, TurnResult
from app.core import validation as validation_module


def test_turn_result_carries_error_reason():
    assert TurnResult(text="x").error is None
    assert TurnResult(text="", status="error", error="provider 403 quota").error == "provider 403 quota"


@pytest.mark.asyncio
async def test_dispatch_ensemble_logs_sample_error_with_endpoint(caplog):
    """F-M2: failed-sample warnings must name endpoint + reason, not status alone."""
    import logging

    from app.core import agentic as agentic_module

    class ScriptedDispatcher:
        async def ensemble(self, **kwargs):
            return EnsembleResult(
                samples=[
                    TurnResult(text="luna says ok", status="success", endpoint_id="pi-codex-luna", model="gpt-5.6-luna"),
                    TurnResult(text="", status="error", endpoint_id="pi-dashscope-qwen", model="qwen3.7-max-2026-06-08", error="403 free quota exhausted"),
                ],
                endpoint_ids=["pi-codex-luna", "pi-dashscope-qwen"],
                status="partial",
            )

    monkeypatch_agentic = ScriptedDispatcher()
    import unittest.mock as mock

    with mock.patch.object(agentic_module, "agentic", monkeypatch_agentic):
        with caplog.at_level(logging.WARNING, logger="app.core.validation"):
            responses, routes, endpoints = await validation_module._dispatch_ensemble(
                purpose="validation.probe",
                messages=[{"role": "user", "content": "hi"}],
                n=2,
                distinct=True,
                project_id="proj-test",
            )
    assert responses == ["luna says ok"]
    assert endpoints == ["pi-codex-luna", "pi-dashscope-qwen"]
    warnings = [r.message for r in caplog.records if "sample 1 failed" in r.message]
    assert warnings, "no failure warning logged"
    assert "pi-dashscope-qwen" in warnings[0] and "403 free quota exhausted" in warnings[0]


@pytest.mark.asyncio
async def test_adversarial_route_evidence_names_model(monkeypatch):
    """F-M4: adversarial route evidence must include model identity."""
    from app.core import agentic as agentic_module

    async def fake_completion(**kwargs):
        return TurnResult(
            text="The claim is overstated; spans show partial support.",
            status="success",
            endpoint_id="pi-codex-luna",
            model="gpt-5.6-luna",
            served_model="gpt-5.6-luna",
        )

    async def fake_embeddings(texts, project_id=None):
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(agentic_module.agentic, "completion", fake_completion)
    monkeypatch.setattr(validation_module, "_get_embeddings", fake_embeddings)

    result = await validation_module.adversarial_review(
        "Is auto-match trustworthy?",
        "Auto-match is always right.",
        project_id="proj-test",
    )
    routes = result.metadata["route_evidence"]
    assert routes, "adversarial review recorded no route evidence"
    assert routes[0].get("model") == "gpt-5.6-luna"
    assert routes[0].get("endpoint_id") == "pi-codex-luna"
    assert validation_module._models_used(routes) == ["gpt-5.6-luna"]


@pytest.mark.asyncio
async def test_dual_run_forwards_effort_to_dispatch():
    """Effort passthrough: dual_run(effort='low') must reach TurnParams."""
    from app.core import agentic as agentic_module

    captured = {}

    class ScriptedDispatcher:
        async def ensemble(self, **kwargs):
            captured.update(kwargs)
            return EnsembleResult(
                samples=[
                    TurnResult(text="a", status="success", endpoint_id="e1", model="m1"),
                    TurnResult(text="b", status="success", endpoint_id="e2", model="m2"),
                ],
                endpoint_ids=["e1", "e2"],
                status="success",
            )

    async def fake_embeddings(texts, project_id=None):
        return [[1.0, 0.0] for _ in texts]

    import unittest.mock as mock

    with mock.patch.object(agentic_module, "agentic", ScriptedDispatcher()):
        monkeypatch_emb = mock.patch.object(validation_module, "_get_embeddings", fake_embeddings)
        monkeypatch_emb.start()
        try:
            await validation_module.dual_run("hi", project_id="proj-test", effort="low")
        finally:
            monkeypatch_emb.stop()
    assert captured["params"].thinking_mode == "low"
