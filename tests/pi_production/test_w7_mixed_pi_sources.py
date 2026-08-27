"""W7 Research Spine coverage for a mixed provider/Petals Pi catalog."""

import app.core.agentic  # noqa: F401  # initialize the dispatcher import plane
import pytest


def _coding_applications(unit_ids: list[str], source_quotes: dict[str, str]) -> list[dict]:
    return [
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


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


async def test_coding_run_mixes_provider_and_petals_routes_under_one_pi_catalog(
    monkeypatch, tmp_path, _agentic_core_on
):
    """One Spine run composes provider and consented Petals raters safely.

    The source-specific integration tests prove each catalog source alone. This
    boundary test proves one PiModelManager projection can select all three
    distinct model identities together, route each structured call through its
    source-specific transport, and persist both route kinds into an accepted
    Research Spine coding run.
    """
    import json
    import uuid
    from unittest.mock import AsyncMock

    from app.core import petals_bridge
    from app.core.agentic.dispatcher import AgenticDispatcher
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.engine import PiExecutionService
    from app.core.pi_runtime.model_manager import PiModelManager
    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-w7-mixed-pi-{suffix}"
    task_id = f"task-w7-mixed-pi-{suffix}"
    unit_ids = [f"eu-w7-mixed-{index}-{suffix}" for index in (1, 2)]
    source_quotes = {
        unit_id: f"Participant struggled with invitation setup {index}."
        for index, unit_id in enumerate(unit_ids, 1)
    }

    class _Donor:
        def __init__(self, node_id: str, model: str):
            self.node_id = node_id
            self.source = "relay"
            self.pi_served = True
            self.is_healthy = True
            self.loaded_models = [model]
            self.allowed_project_ids = [project_id]
            self.calls: list[dict] = []

        async def chat(self, messages, **kwargs):
            self.calls.append({"messages": messages, **kwargs})
            return {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"applications": _coding_applications(unit_ids, source_quotes)}
                    ),
                }
            }

    donors = {
        node.node_id: node
        for node in (
            _Donor("donor-b", "petals-model-b"),
            _Donor("donor-c", "petals-model-c"),
        )
    }

    class _Registry:
        _nodes = donors

    monkeypatch.setattr(petals_bridge, "_registry", lambda: _Registry())
    monkeypatch.setattr("app.config.settings.petals_bridge_enabled", True)

    provider_endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-provider-a",
        provider_kind="faux",
        base_url="",
        model="provider-model-a",
        api_key="faux",
        timeout_ms=1000,
        max_retries=0,
        provider_account_handle="provider-account-a",
    )
    manager = PiModelManager(endpoints=[provider_endpoint], include_local=False)
    # Avoid ambient LLMServer rows; ensure_db_projection still refreshes the
    # dynamic Petals projection on every selection/dispatch boundary.
    manager._db_projected = True

    class _Supervisor:
        def __init__(self):
            self.binds: dict[str, dict] = {}

        async def ensure_started(self):
            return None

        async def open_session(self, key, **_kwargs):
            return None

        async def bind_provider(self, key, payload):
            self.binds[key] = payload

        async def close_session(self, _key):
            return None

        async def run_turn(self, key, _user_text, _tool_handler, **_kwargs):
            payload = self.binds[key]
            endpoint_id = payload["endpoint_id"]
            if endpoint_id == "pi-provider-a":
                served_model = payload["model"]
                yield {
                    "type": "run.completed",
                    "usage": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
                    "stop_reason": "stop",
                    "structured": {
                        "applications": _coding_applications(unit_ids, source_quotes)
                    },
                    "served_model": served_model,
                    "route_evidence": {
                        "endpoint_id": endpoint_id,
                        "route_kind": "pi_model_management",
                        "model": served_model,
                        "served_model": served_model,
                    },
                }
                return

            node_id = endpoint_id.removeprefix("pi-petals-")
            bridged = await petals_bridge.chat_completions(
                {
                    "model": endpoint_id,
                    "messages": [{"role": "user", "content": "code evidence"}],
                    "purpose": "research.validity.coder",
                    "project_id": project_id,
                },
                pinned_node_id=node_id,
                project_id=project_id,
            )
            content = bridged["choices"][0]["message"]["content"]
            yield {
                "type": "run.completed",
                "usage": bridged["usage"],
                "stop_reason": "stop",
                "structured": json.loads(content),
                "served_model": bridged["_istara_route"]["model"],
                "route_evidence": bridged["_istara_route"],
            }

    supervisor = _Supervisor()
    pi_service = PiExecutionService(supervisor=supervisor, model_manager=manager)
    monkeypatch.setattr(pi_service, "_record_turn_telemetry", AsyncMock())
    dispatcher = AgenticDispatcher(pi_service=pi_service)
    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", AsyncMock())
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
    assert result["distinct_model_count"] == result["rater_count"] == 3
    assert {route["endpoint_id"] for route in result["route_evidence"]} == {
        "pi-provider-a",
        "pi-petals-donor-b",
        "pi-petals-donor-c",
    }
    assert {route["route_kind"] for route in result["route_evidence"]} == {
        "pi_model_management",
        "petals_bridge",
    }
    assert {route["model"] for route in result["route_evidence"]} == {
        "provider-model-a",
        "petals-model-b",
        "petals-model-c",
    }
    assert all(
        call["project_id"] == project_id
        for donor in donors.values()
        for call in donor.calls
    )
    assert all(len(donor.calls) == 1 for donor in donors.values())


async def _true_async():
    return True
