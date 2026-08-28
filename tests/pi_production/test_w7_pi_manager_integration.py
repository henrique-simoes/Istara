"""Integration characterization for W7's real Pi Model Management catalog."""

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
    from app.core.agentic.dispatcher import AgenticDispatcher
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
    class _ManagedStructuredService:
        """Deterministic provider seam behind the real dispatcher.

        W1 already proves the real supervised Node worker and forced structured
        protocol. This fixture keeps W7 focused on the higher-level invariant:
        the real ``AgenticDispatcher`` and its paired manager must carry the
        exact selected endpoint/model into every Research Spine coder call.
        """

        def __init__(self):
            self.calls = []

        def model_manager(self):
            return manager

        async def run_structured(self, **kwargs):
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
            return {
                "text": "",
                "value": {"applications": applications},
                "status": "success",
                "usage": {},
                "stop_reason": "stop",
                "endpoint_id": kwargs["params"].endpoint_id,
                "model": kwargs["params"].model,
                # This is the provider receipt used by the strict coder
                # adapter; a configured/request model is not sufficient.
                "served_model": kwargs["params"].model,
                "tool_calls": [],
            }

    service = _ManagedStructuredService()
    dispatcher = AgenticDispatcher(pi_service=service)
    async def no_op_usage(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op_usage)
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

    assert result["promotion_status"] == "accepted", result
    assert result["reliability_method"] == "fleiss_kappa_with_krippendorff_alpha_companion"
    assert result["distinct_model_count"] == 3
    assert result["rater_count"] == 3
    assert [kwargs["params"].endpoint_id for kwargs in service.calls] == [
        "ep-a",
        "ep-b",
        "ep-c",
    ]
    assert [kwargs["params"].model for kwargs in service.calls] == [
        "model-a",
        "model-b",
        "model-c",
    ]
    assert all(kwargs["purpose"] == "validity.coder" for kwargs in service.calls)
    assert {route["endpoint_id"] for route in result["route_evidence"]} == {
        "ep-a",
        "ep-b",
        "ep-c",
    }


async def test_coding_run_qwen_rate_limit_fallback_preserves_three_model_gate(
    monkeypatch, _agentic_core_on
):
    """The real manager/dispatcher path records a Qwen fallback as one rater."""
    import uuid
    from unittest.mock import AsyncMock

    from app.core.agentic.dispatcher import AgenticDispatcher
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.model_manager import PiModelManager
    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-w7-qwen-fallback-{suffix}"
    unit_ids = [f"eu-w7-qwen-1-{suffix}", f"eu-w7-qwen-2-{suffix}"]
    quotes = {unit_id: f"Participant reported invitation friction {index}." for index, unit_id in enumerate(unit_ids, 1)}
    dashscope_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    endpoint_specs = (
        ("ep-luna", "gpt-5.6-luna", "openai-codex", "codex-key"),
        ("ep-plus", "qwen3.7-plus", "dashscope", "same-dashscope-key"),
        ("ep-flash", "qwen3.7-flash", "dashscope", "same-dashscope-key"),
        ("ep-plus-dated", "qwen3.7-plus-2026-05-26", "dashscope", "same-dashscope-key"),
        ("ep-flash-dated", "qwen3.7-flash-2026-07-15", "dashscope", "same-dashscope-key"),
    )
    endpoints = [
        ResolvedPiEndpoint(
            endpoint_id=endpoint_id,
            provider_kind="openai_compat",
            base_url=dashscope_url if provider == "dashscope" else "https://codex.invalid",
            model=model,
            api_key=api_key,
            timeout_ms=1000,
            max_retries=0,
            pi_provider=provider,
            provider_account_handle=f"account-{provider}",
        )
        for endpoint_id, model, provider, api_key in endpoint_specs
    ]
    manager = PiModelManager(endpoints=endpoints, include_local=False)
    manager._db_projected = True

    class _ManagedStructuredService:
        def __init__(self):
            self.calls = []

        def model_manager(self):
            return manager

        async def run_structured(self, **kwargs):
            self.calls.append(kwargs)
            model = kwargs["params"].model
            if model == "qwen3.7-plus":
                raise RuntimeError("pi_bridge_http_429")
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
                    "quote": quotes[unit_id],
                    "confidence": 0.92,
                    "rationale": "The participant is blocked by invitation setup.",
                }
                for unit_id in unit_ids
            ]
            return {
                "text": "",
                "value": {"applications": applications},
                "status": "success",
                "usage": {},
                "stop_reason": "stop",
                "endpoint_id": kwargs["params"].endpoint_id,
                "model": model,
                "served_model": model,
                "tool_calls": [],
            }

    service = _ManagedStructuredService()
    dispatcher = AgenticDispatcher(pi_service=service)
    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", AsyncMock())
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr(
        research_validity_service,
        "_use_pi_coding_plane",
        lambda db, pid: _true_async(),
    )
    await init_db()
    async with async_session() as db:
        for index, unit_id in enumerate(unit_ids, 1):
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    source_id="interview-qwen",
                    stable_id=f"interview-qwen#EU-{index:04d}",
                    unit_index=index,
                    source_text=quotes[unit_id],
                    source_location=f"interview-qwen:{index}",
                )
            )
        await db.commit()
        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            evidence_unit_ids=unit_ids,
            created_by="test-researcher",
        )

    assert result["promotion_status"] == "accepted"
    assert result["distinct_model_count"] == 3
    assert [call["params"].model for call in service.calls] == [
        "gpt-5.6-luna",
        "qwen3.7-plus",
        "qwen3.7-plus-2026-05-26",
        "qwen3.7-flash",
    ]
    assert all(call["params"].thinking_mode == "high" for call in service.calls)
    fallback_routes = [
        route for route in result["route_evidence"] if route.get("fallback_reason") == "rate_limit"
    ]
    assert len(fallback_routes) == 1
    assert fallback_routes[0]["requested_model"] == "qwen3.7-plus"
    assert fallback_routes[0]["served_model"] == "qwen3.7-plus-2026-05-26"
    assert fallback_routes[0]["fallback_same_key_verified"] is True
    assert fallback_routes[0]["fallback_attempts"] == [
        {"model": "qwen3.7-plus", "endpoint_id": "ep-plus", "outcome": "rate_limited"},
        {
            "model": "qwen3.7-plus-2026-05-26",
            "endpoint_id": "ep-plus-dated",
            "outcome": "served",
        },
    ]
    assert {
        route["served_model"] for route in result["route_evidence"] if route.get("outcome") == "served"
    } == {"gpt-5.6-luna", "qwen3.7-plus-2026-05-26", "qwen3.7-flash"}


async def test_coding_run_uses_project_scoped_petals_projection_and_preserves_route_receipts(
    monkeypatch, tmp_path, _agentic_core_on
):
    """The production coding path must carry three Petals identities into the Spine gate.

    This deliberately crosses all three boundaries that the standalone bridge
    and the Pi manager tests cannot prove together: registry -> Petals catalog
    projection, Pi structured dispatch, and Research Spine reliability/
    provenance persistence.  The donor transport is deterministic and local;
    no live provider or model is loaded.
    """
    import json
    import uuid
    from unittest.mock import AsyncMock

    from app.core import petals_bridge
    from app.core.agentic.dispatcher import AgenticDispatcher
    from app.core.pi_runtime.engine import PiExecutionService
    from app.core.pi_runtime.model_manager import PiModelManager
    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-w7-petals-pi-{suffix}"
    task_id = f"task-w7-petals-pi-{suffix}"
    unit_ids = [f"eu-w7-petals-1-{suffix}", f"eu-w7-petals-2-{suffix}"]
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
            return {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"applications": applications}),
                }
            }

    donors = {
        node.node_id: node
        for node in (
            _Donor("donor-a", "petals-model-a"),
            _Donor("donor-b", "petals-model-b"),
            _Donor("donor-c", "petals-model-c"),
        )
    }

    class _Registry:
        _nodes = donors

    monkeypatch.setattr(petals_bridge, "_registry", lambda: _Registry())
    monkeypatch.setattr("app.config.settings.petals_bridge_enabled", True)

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

        async def run_turn(self, key, user_text, _tool_handler, **_kwargs):
            payload = self.binds[key]
            endpoint_id = payload["endpoint_id"]
            node_id = endpoint_id.removeprefix("pi-petals-")
            bridged = await petals_bridge.chat_completions(
                {
                    "model": endpoint_id,
                    "messages": [{"role": "user", "content": user_text}],
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
                "provider_message": {"role": "assistant", "content": content},
                "structured": json.loads(content),
                "served_model": bridged["_istara_route"]["model"],
                "route_evidence": bridged["_istara_route"],
            }

    manager = PiModelManager(endpoints=[], include_local=False)
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
    assert result["distinct_model_count"] == 3
    assert result["rater_count"] == 3
    assert {route["route_kind"] for route in result["route_evidence"]} == {"petals_bridge"}
    assert {route["node_id"] for route in result["route_evidence"]} == {
        "donor-a",
        "donor-b",
        "donor-c",
    }
    assert {route["endpoint_id"] for route in result["route_evidence"]} == {
        "pi-petals-donor-a",
        "pi-petals-donor-b",
        "pi-petals-donor-c",
    }
    assert all(
        call["project_id"] == project_id
        for donor in donors.values()
        for call in donor.calls
    )
    assert all(len(donor.calls) == 1 for donor in donors.values())


async def _true_async():
    return True
