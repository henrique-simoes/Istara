"""Adaptive validation scoring guardrails."""

import pytest

from app.core.adaptive_validation import AdaptiveSelector, _sample_confidence_weight


def test_sample_confidence_weight_penalizes_tiny_samples():
    assert _sample_confidence_weight(0) == 0
    assert 0 < _sample_confidence_weight(1) < _sample_confidence_weight(4)
    assert _sample_confidence_weight(5) == 1
    assert _sample_confidence_weight(100) == 1


class _Server:
    def __init__(self, name, models):
        self.name = name
        self.is_healthy = True
        self.loaded_models = models
        self.model_capabilities = {model: {"supports_tools": True} for model in models}


class _Router:
    def __init__(self, servers):
        self.servers = servers

    def _sorted_servers(self, **_kwargs):
        return self.servers


@pytest.mark.asyncio
async def test_adaptive_selector_prefers_full_ensemble_when_three_models_are_healthy(monkeypatch):
    from app.core import llm_router as llm_router_module

    monkeypatch.setattr(
        llm_router_module,
        "llm_router",
        _Router([
            _Server("mac-studio", ["google/gemma-4-e4b"]),
            _Server("colima-qwen", ["qwen3.5:4b-q4"]),
            _Server("colima-gemma", ["gemma4:e2b-q4"]),
        ]),
    )

    assert await AdaptiveSelector().select_method("project-a", "user-interviews", "agent-a") == "full_ensemble"


@pytest.mark.asyncio
async def test_adaptive_selector_uses_self_moa_only_when_compute_constrained(monkeypatch):
    from app.core import llm_router as llm_router_module

    monkeypatch.setattr(
        llm_router_module,
        "llm_router",
        _Router([_Server("mac-studio", ["google/gemma-4-e4b"])]),
    )

    assert await AdaptiveSelector().select_method("project-a", "user-interviews", "agent-a") == "self_moa"
