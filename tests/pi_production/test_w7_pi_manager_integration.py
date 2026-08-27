"""Integration characterization for W7's real Pi Model Management catalog."""

from types import SimpleNamespace

import app.core.agentic  # noqa: F401  # initialize the dispatcher import plane
import pytest


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


async def test_coding_run_uses_real_pi_model_manager_for_identity_distinct_coders(
    monkeypatch, tmp_path, _agentic_core_on
):
    """Selection, dispatch, and Spine acceptance must share real Pi identities."""
    import uuid

    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.engine import PiExecutionService
    from app.core.pi_runtime.model_manager import PiModelManager
    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-w7-real-pi-{suffix}"
    task_id = f"task-w7-real-pi-{suffix}"
    unit_ids = [f"eu-w7-real-1-{suffix}", f"eu-w7-real-2-{suffix}"]
    source_quotes = {
        unit_id: f"Participant struggled with invitation setup {index}."
        for index, unit_id in enumerate(unit_ids, 1)
    }

    manager = PiModelManager(
        endpoints=[
            ResolvedPiEndpoint(
                endpoint_id=f"ep-{name}",
                provider_kind="faux",
                base_url="",
                model=f"model-{name}",
                api_key="faux",
                timeout_ms=1000,
                max_retries=0,
                provider_account_handle=f"account-{name}",
            )
            for name in ("a", "b", "c")
        ],
        include_local=False,
    )
    # The test exercises the real read-only manager projection without a DB
    # catalog; no production endpoint state is written.
    manager._db_projected = True
    service = PiExecutionService(model_manager=manager)
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager", lambda: manager
    )

    class _RecordingDispatcher:
        def __init__(self):
            self.calls = []

        def model_manager(self):
            return manager

        def pi_execution_service(self):
            return service

        async def structured(self, **kwargs):
            self.calls.append(kwargs)
            applications = [
                {
                    "evidence_unit_id": unit_id,
                    "codes": [
                        "collaboration-disorientation"
                        if unit_id == unit_ids[0]
                        else "invitation-friction"
                    ],
                    "primary_code": (
                        "collaboration-disorientation"
                        if unit_id == unit_ids[0]
                        else "invitation-friction"
                    ),
                    "quote": source_quotes[unit_id],
                    "confidence": 0.92,
                    "rationale": "The participant is blocked by team invitation setup.",
                }
                for unit_id in unit_ids
            ]
            return SimpleNamespace(
                text="",
                value={"applications": applications},
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id=kwargs["params"].endpoint_id,
                tool_calls=[],
            )

    dispatcher = _RecordingDispatcher()
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr(
        research_validity_service,
        "_use_pi_coding_plane",
        lambda db, pid: _true_async(),
    )

    class _SentinelRouter:
        def _sorted_servers(self, **kwargs):
            raise AssertionError("legacy coder selection must not run on the Pi plane")

    monkeypatch.setattr(research_validity_service, "llm_router", _SentinelRouter())
    await init_db()
    async with async_session() as db:
        for index, unit_id in enumerate(unit_ids, 1):
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    task_id=task_id,
                    source_id="interview-01",
                    stable_id=f"interview-01#EU-{index:04d}",
                    unit_index=index,
                    source_text=source_quotes[unit_id],
                    source_location=f"interview-01:{index}",
                )
            )
        await db.commit()
        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=task_id,
            evidence_unit_ids=unit_ids,
            created_by="test-researcher",
        )

    assert result["promotion_status"] == "accepted"
    assert result["reliability_method"] == "fleiss_kappa_with_krippendorff_alpha_companion"
    assert result["distinct_model_count"] == 3
    assert result["rater_count"] == 3
    assert [kwargs["params"].endpoint_id for kwargs in dispatcher.calls] == [
        "ep-a",
        "ep-b",
        "ep-c",
    ]
    assert [kwargs["params"].model for kwargs in dispatcher.calls] == [
        "model-a",
        "model-b",
        "model-c",
    ]
    assert all(kwargs["pi_service"] is service for kwargs in dispatcher.calls)
    assert {route["endpoint_id"] for route in result["route_evidence"]} == {
        "ep-a",
        "ep-b",
        "ep-c",
    }


async def _true_async():
    return True
