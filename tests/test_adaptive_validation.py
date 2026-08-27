"""Adaptive validation scoring and Pi-catalog authority guardrails."""

import pytest

from app.core.adaptive_validation import AdaptiveSelector, _sample_confidence_weight


def test_sample_confidence_weight_penalizes_tiny_samples():
    assert _sample_confidence_weight(0) == 0
    assert 0 < _sample_confidence_weight(1) < _sample_confidence_weight(4)
    assert _sample_confidence_weight(5) == 1
    assert _sample_confidence_weight(100) == 1


class _PiManager:
    def __init__(self, identities_by_project):
        self.identities_by_project = identities_by_project
        self.project_ids = []

    async def ensure_db_projection(self):
        return None

    def available_model_identities(self, *, project_id=None):
        self.project_ids.append(project_id)
        return self.identities_by_project.get(project_id, ())


class _Dispatcher:
    def __init__(self, manager):
        self.manager = manager

    def model_manager(self):
        return self.manager


@pytest.mark.asyncio
async def test_adaptive_selector_prefers_full_ensemble_when_three_models_are_healthy(monkeypatch):
    from app.core import agentic as agentic_module

    manager = _PiManager({"project-a": ("model-a", "model-b", "model-c")})
    monkeypatch.setattr(
        agentic_module,
        "agentic",
        _Dispatcher(manager),
    )

    assert await AdaptiveSelector().select_method("project-a", "user-interviews", "agent-a") == "full_ensemble"
    assert manager.project_ids == ["project-a"]


@pytest.mark.asyncio
async def test_adaptive_selector_uses_self_moa_only_when_compute_constrained(monkeypatch):
    from app.core import agentic as agentic_module

    manager = _PiManager({"project-a": ("model-a",)})
    monkeypatch.setattr(
        agentic_module,
        "agentic",
        _Dispatcher(manager),
    )

    assert await AdaptiveSelector().select_method("project-a", "user-interviews", "agent-a") == "self_moa"


@pytest.mark.asyncio
async def test_adaptive_selector_uses_project_scoped_catalog_and_excludes_other_project_models(
    monkeypatch,
):
    from app.core import agentic as agentic_module

    manager = _PiManager(
        {
            "project-a": ("model-a", "model-b"),
            "project-b": ("model-a", "model-b", "donor-only-for-b"),
        }
    )
    monkeypatch.setattr(agentic_module, "agentic", _Dispatcher(manager))

    # A globally visible third donor must not turn project-a's two-model
    # admission into a three-model full ensemble.
    assert await AdaptiveSelector().select_method("project-a", "", "") == "dual_run"
    assert manager.project_ids == ["project-a"]
