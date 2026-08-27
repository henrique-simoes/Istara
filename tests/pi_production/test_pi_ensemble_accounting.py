"""Research Spine accounting oracles for the Pi-managed ensemble seam.

These tests deliberately stub only the provider completion result.  The
dispatcher, Pi execution service, model manager, and usage ledger remain real,
so the tests catch a partial-exact aggregate without loading a live model.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.model_manager import PiModelManager
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db


def _project_id() -> str:
    return f"pi-ensemble-accounting-{uuid.uuid4().hex[:12]}"


def _endpoints() -> list[ResolvedPiEndpoint]:
    return [
        ResolvedPiEndpoint(
            endpoint_id=f"pi-accounting-{name}",
            provider_kind="openai_compat",
            base_url=f"http://{name}.invalid/v1",
            model=f"model-{name}",
            api_key="test-key",
            timeout_ms=30_000,
            max_retries=0,
        )
        for name in ("a", "b")
    ]


class _ScriptedPiService(PiExecutionService):
    def __init__(self, responses: list[dict]) -> None:
        manager = PiModelManager(endpoints=_endpoints(), include_local=False)
        manager._db_projected = True
        super().__init__(model_manager=manager)
        self._responses = list(responses)

    async def run_completion(self, **kwargs):  # noqa: ANN003
        response = dict(self._responses.pop(0))
        endpoint_id = kwargs["params"].endpoint_id
        response.setdefault("endpoint_id", endpoint_id)
        response.setdefault("model", endpoint_id.replace("pi-accounting-", "model-"))
        response.setdefault("status", "success")
        return response


async def _rows(project_id: str) -> list[AgenticUsageRow]:
    async with async_session() as db:
        result = await db.execute(
            select(AgenticUsageRow).where(AgenticUsageRow.project_id == project_id)
        )
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_pi_ensemble_mixed_provider_usage_is_estimated_as_one_dispatch():
    """A missing real-provider receipt must not leave a partial exact total."""
    await init_db()
    project_id = _project_id()
    service = _ScriptedPiService([
        {
            "text": "rater A",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
                "cost_usd": 0.01,
                "turns": 1,
            },
        },
        {"text": "rater B without a provider usage receipt", "usage": {}},
    ])

    result = await AgenticDispatcher(pi_service=service).ensemble(
        purpose="research_spine.pi_ensemble.mixed_usage",
        project_id=project_id,
        system="independent coder",
        messages=[{"role": "user", "content": "extract evidence"}],
        n=2,
        distinct=True,
        params=TurnParams(),
        engine="pi",
    )

    assert result.status == "success"
    assert result.usage == {}
    rows = await _rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.engine == "pi"
    assert row.estimate == 1
    assert row.input_tokens > 0 and row.output_tokens > 0
    assert row.total_tokens == row.input_tokens + row.output_tokens
    assert row.turns == 2
    assert row.cost_usd == 0


@pytest.mark.asyncio
async def test_pi_ensemble_all_zero_provider_placeholder_is_estimated():
    """pi-ai's all-zero placeholder is not a provider receipt."""
    await init_db()
    project_id = _project_id()
    service = _ScriptedPiService([
        {"text": "rater A", "usage": {"input_tokens": 100, "output_tokens": 10}},
        {
            "text": "rater B with adapter placeholder",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        },
    ])

    result = await AgenticDispatcher(pi_service=service).ensemble(
        purpose="research_spine.pi_ensemble.zero_placeholder",
        project_id=project_id,
        system="independent coder",
        messages=[{"role": "user", "content": "extract evidence"}],
        n=2,
        distinct=True,
        params=TurnParams(),
        engine="pi",
    )

    assert result.status == "success"
    assert result.usage == {}
    row = (await _rows(project_id))[0]
    assert row.estimate == 1
    assert row.turns == 2


@pytest.mark.asyncio
async def test_pi_ensemble_all_provider_usage_is_aggregated_exactly():
    """Fully reported samples retain cache, cost, total, and turn accounting."""
    await init_db()
    project_id = _project_id()
    service = _ScriptedPiService([
        {
            "text": "rater A",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
                "cache_read": 4,
                "cache_write": 1,
                "total_tokens": 115,
                "cost_usd": 0.01,
                "turns": 1,
            },
        },
        {
            "text": "rater B",
            "usage": {
                "input_tokens": 200,
                "output_tokens": 20,
                "cache_read": 6,
                "cache_write": 2,
                "total_tokens": 228,
                "cost_usd": 0.02,
                "turns": 1,
            },
        },
    ])

    result = await AgenticDispatcher(pi_service=service).ensemble(
        purpose="research_spine.pi_ensemble.exact_usage",
        project_id=project_id,
        system="independent coder",
        messages=[{"role": "user", "content": "extract evidence"}],
        n=2,
        distinct=True,
        params=TurnParams(),
        engine="pi",
    )

    assert result.status == "success"
    assert result.usage == {
        "input_tokens": 300,
        "output_tokens": 30,
        "cache_read": 10,
        "cache_write": 3,
        "total_tokens": 343,
        "cost_usd": pytest.approx(0.03),
        "turns": 2,
        "estimate": False,
    }
    rows = await _rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 0
    assert row.input_tokens == 300 and row.output_tokens == 30
    assert row.cache_read == 10 and row.cache_write == 3
    assert row.total_tokens == 343
    assert row.cost_usd == pytest.approx(0.03)
    assert row.turns == 2
