"""Cross-engine ensemble provenance through the Pi Model Management authority."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_replacement import PI_ENGINE_VALUES
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.model_manager import PiModelManager

from .harness import faux_endpoint, final_text


def _isolated(manager: PiModelManager) -> PiModelManager:
    """Keep the deterministic catalog database-independent."""
    manager._db_projected = True  # noqa: SLF001
    return manager


class _ServedIdentitySupervisor:
    """Small supervisor seam that emits provider-reported model identities."""

    def __init__(self) -> None:
        self.bindings: dict[str, dict] = {}
        self.calls: list[str] = []

    async def ensure_started(self) -> None:
        return None

    async def open_session(self, key: str, **_kwargs) -> None:
        self.calls.append(key)

    async def bind_provider(self, key: str, payload: dict) -> None:
        self.bindings[key] = payload

    async def run_turn(self, key: str, _user_text: str, _tool_handler, **_kwargs):
        payload = self.bindings[key]
        yield {
            "type": "run.completed",
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "stop",
            # This is the provider receipt, intentionally distinct from the
            # configured request label in the endpoint payload.
            "served_model": f"served/{payload['model']}",
        }

    async def close_session(self, key: str) -> None:
        self.bindings.pop(key, None)


@pytest.mark.asyncio
async def test_all_loop_selectors_preserve_distinct_served_identities(monkeypatch):
    """Every public loop selector retains three provider-served rater identities.

    This is an authority/provenance oracle only: it exercises the real
    ``AgenticDispatcher`` and ``PiExecutionService`` with a deterministic
    supervisor seam. It does not claim live provider quality or Fleiss/
    Krippendorff reliability; the Research Spine coding gate owns those checks.
    """

    endpoints = [
        replace(
            faux_endpoint([final_text(f"answer-{name}")], endpoint_id=f"pi-rater-{name}"),
            model=f"configured-{name}",
        )
        for name in ("a", "b", "c")
    ]
    manager = _isolated(PiModelManager(endpoints=endpoints, include_local=False))
    supervisor = _ServedIdentitySupervisor()
    service = PiExecutionService(supervisor=supervisor, model_manager=manager)
    monkeypatch.setattr(service, "_record_turn_telemetry", AsyncMock())
    monkeypatch.setattr(
        "app.core.agentic.dispatcher.record_agentic_usage", AsyncMock()
    )

    results = {}
    # The API exposes aliases for the Pi path.  They must all normalize to the
    # same PiExecutionService/PiModelManager authority, or a selector could
    # silently bypass the three-rater Research Spine ensemble.
    for engine in ("legacy", *sorted(PI_ENGINE_VALUES)):
        results[engine] = await AgenticDispatcher(pi_service=service).ensemble(
            purpose=f"identity-parity.{engine}",
            project_id="project-spine",
            messages=[{"role": "user", "content": "independently code this span"}],
            n=3,
            distinct=True,
            engine=engine,
            params=TurnParams(),
        )

    expected_endpoints = {"pi-rater-a", "pi-rater-b", "pi-rater-c"}
    expected_served = {"served/configured-a", "served/configured-b", "served/configured-c"}
    for result in results.values():
        assert result.status == "success"
        assert set(result.endpoint_ids) == expected_endpoints
        assert {sample.model for sample in result.samples} == {
            "configured-a",
            "configured-b",
            "configured-c",
        }
        assert {sample.served_model for sample in result.samples} == expected_served
        assert all(sample.served_model != sample.model for sample in result.samples)
