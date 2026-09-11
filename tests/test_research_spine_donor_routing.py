"""Research Spine donor routing tests for project-scoped benchmark orchestration."""

# Import-order guard: this suite imports app.services.research_validity_service
# at module level. That module sits on a latent module-level import cycle
# (research_validity -> skills.intercoder -> skill_factory -> file_processor
# -> embeddings -> pi_runtime.engine -> telemetry -> research_validity) that
# only resolves when the dispatcher plane (app.core.agentic) has been
# initialized first in the process. The cycle is pre-existing architecture
# debt outside this file; initializing the plane here keeps a standalone run
# of this file green.
import app.core.agentic  # noqa: F401

from types import SimpleNamespace

import pytest

from app.config import settings
from app.core.compute_registry import ComputeNode, ComputeRegistry
from app.services import research_validity_service


@pytest.mark.asyncio
async def test_project_chat_uses_project_donor_model_instead_of_global_lmstudio_default(
    monkeypatch,
):
    monkeypatch.setattr(settings, "strict_auto_routing", True)
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_host", "http://host.docker.internal:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "global-heavy-model")
    registry = ComputeRegistry()
    captured: dict[str, str | None] = {}
    node = ComputeNode(
        node_id="relay-admin-lmstudio",
        name="Admin LM Studio donor",
        host="http://host.docker.internal:1234",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        health_state="ready",
        websocket=object(),
        allowed_project_ids=["project-a"],
        loaded_models=["served-base-model", "served-base-model:2"],
        model_capabilities={
            "served-base-model": {"is_loaded": True, "loadable": True},
            "served-base-model:2": {
                "is_loaded": True,
                "loadable": True,
                "loaded_instance_alias": True,
            },
        },
    )

    async def relay_chat(messages, **kwargs):  # noqa: ANN001
        captured["model"] = kwargs.get("model")
        captured["project_id"] = kwargs.get("project_id")
        return {"message": {"role": "assistant", "content": "served by project donor"}}

    monkeypatch.setattr(node, "chat", relay_chat)
    registry.register_node(node)

    result = await registry.chat(
        [{"role": "user", "content": "hello"}],
        project_id="project-a",
    )

    assert result["message"]["content"] == "served by project donor"
    assert captured == {"model": "served-base-model:2", "project_id": "project-a"}
    assert node.last_served_model == "served-base-model:2"


@pytest.mark.asyncio
async def test_project_stream_uses_project_donor_model_instead_of_global_default(
    monkeypatch,
):
    monkeypatch.setattr(settings, "strict_auto_routing", True)
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_model", "global-heavy-model")
    registry = ComputeRegistry()
    captured: dict[str, str | None] = {}
    node = ComputeNode(
        node_id="relay-researcher",
        name="Researcher donor",
        host="http://192.0.2.10:8080",
        source="relay",
        provider_type="openai_compat",
        is_healthy=True,
        health_state="ready",
        websocket=object(),
        allowed_project_ids=["project-a"],
        loaded_models=["researcher-model"],
    )

    async def relay_chat(messages, **kwargs):  # noqa: ANN001
        captured["model"] = kwargs.get("model")
        captured["project_id"] = kwargs.get("project_id")
        return {
            "message": {"role": "assistant", "content": "streamed by project donor"}
        }

    monkeypatch.setattr(node, "chat", relay_chat)
    registry.register_node(node)

    chunks = [
        chunk
        async for chunk in registry.chat_stream(
            [{"role": "user", "content": "hello"}],
            project_id="project-a",
        )
    ]

    assert chunks == ["streamed by project donor"]
    assert captured == {"model": "researcher-model", "project_id": "project-a"}
    assert node.last_served_model == "researcher-model"


def test_research_validity_coder_selection_uses_distinct_project_donors(monkeypatch):
    nodes = [
        SimpleNamespace(
            node_id="donor-a",
            name="Donor A",
            is_healthy=True,
            loaded_models=["base-a", "base-a:2", "extra-a"],
            model_capabilities={
                "base-a": {"is_loaded": True},
                "base-a:2": {"is_loaded": True, "loaded_instance_alias": True},
                "extra-a": {"is_loaded": True},
            },
        ),
        SimpleNamespace(
            node_id="donor-b",
            name="Donor B",
            is_healthy=True,
            loaded_models=["model-b"],
            model_capabilities={},
        ),
        SimpleNamespace(
            node_id="donor-c",
            name="Donor C",
            is_healthy=True,
            loaded_models=["model-c"],
            model_capabilities={},
        ),
    ]

    class FakeRouter:
        def _sorted_servers(self, **kwargs):  # noqa: ANN001
            assert kwargs["project_id"] == "project-a"
            return nodes

    monkeypatch.setattr(research_validity_service, "llm_router", FakeRouter())

    coders = research_validity_service._select_project_coders("project-a", max_coders=3)

    assert [coder.node.node_id for coder in coders] == ["donor-a", "donor-b", "donor-c"]
    assert [coder.model_name for coder in coders] == ["base-a:2", "model-b", "model-c"]


def test_research_validity_coder_selection_collapses_case_variant_model_ids(
    monkeypatch,
):
    """Donor aliases differing only by case must not fabricate a rater."""
    nodes = [
        SimpleNamespace(
            node_id="donor-a",
            name="Donor A",
            is_healthy=True,
            loaded_models=["Model-A"],
            model_capabilities={},
        ),
        SimpleNamespace(
            node_id="donor-b",
            name="Donor B",
            is_healthy=True,
            loaded_models=["model-a"],
            model_capabilities={},
        ),
        SimpleNamespace(
            node_id="donor-c",
            name="Donor C",
            is_healthy=True,
            loaded_models=["model-c"],
            model_capabilities={},
        ),
    ]

    class FakeRouter:
        def _sorted_servers(self, **kwargs):  # noqa: ANN001
            return nodes

    monkeypatch.setattr(research_validity_service, "llm_router", FakeRouter())

    coders = research_validity_service._select_project_coders("project-a", max_coders=3)

    assert [coder.model_name for coder in coders] == ["Model-A", "model-c"]


def test_coding_applications_resolve_source_units_by_stable_id_index_or_quote():
    units = [
        SimpleNamespace(
            id="uuid-a",
            stable_id="document:one#EU-0004",
            unit_index=4,
            source_text="Patient could not tell whether the prep task was required.",
        ),
        SimpleNamespace(
            id="uuid-b",
            stable_id="document:one#EU-0005",
            unit_index=5,
            source_text="Care coordinator manually reconciled portal and SMS reminders.",
        ),
    ]
    unit_by_id = {unit.id: unit for unit in units}

    assert (
        research_validity_service._resolve_application_unit(
            {"stable_id": "document:one#EU-0004"},
            unit_by_id=unit_by_id,
            units=units,
        ).id
        == "uuid-a"
    )
    assert (
        research_validity_service._resolve_application_unit(
            {"unit_index": 5},
            unit_by_id=unit_by_id,
            units=units,
        ).id
        == "uuid-b"
    )
    assert (
        research_validity_service._resolve_application_unit(
            {"quote": "Care coordinator manually reconciled portal and SMS reminders."},
            unit_by_id=unit_by_id,
            units=units,
        ).id
        == "uuid-b"
    )


def test_coding_application_parser_accepts_common_model_json_variants():
    units = [
        SimpleNamespace(
            id="uuid-a",
            stable_id="document:one#EU-0004",
            unit_index=4,
            source_text="Patient could not tell whether the prep task was required.",
        )
    ]
    unit_by_id = {unit.id: unit for unit in units}

    for payload in (
        {
            "code_applications": [
                {
                    "stable_id": "document:one#EU-0004",
                    "codes": ["prep_confusion"],
                    "quote": units[0].source_text,
                }
            ]
        },
        {
            "coding_applications": [
                {
                    "unit_index": 4,
                    "primary_code": "prep_confusion",
                    "quote": units[0].source_text,
                }
            ]
        },
        {
            "items": [
                {
                    "evidence_unit_id": "uuid-a",
                    "codes": ["prep_confusion"],
                    "quote": units[0].source_text,
                }
            ]
        },
        {
            "evidence_unit_id": "uuid-a",
            "codes": ["prep_confusion"],
            "quote": units[0].source_text,
        },
    ):
        usable = research_validity_service._usable_coding_applications(
            payload,
            unit_by_id=unit_by_id,
            units=units,
        )

        assert len(usable) == 1
        assert usable[0][1].id == "uuid-a"
        assert usable[0][2] == ["prep_confusion"]


def test_research_validity_coding_prompt_compacts_long_source_units():
    long_text = (
        "Important opening source quote. " + ("context detail " * 120)
    ) + "Important closing source quote."

    class Unit:
        def to_dict(self):  # noqa: ANN001
            return {
                "id": "unit-long",
                "stable_id": "doc#EU-0001",
                "unit_index": 1,
                "source_id": "doc",
                "source_text": long_text,
                "start_offset": 0,
                "end_offset": len(long_text),
            }

    messages = research_validity_service._coding_messages([Unit()], None, 0.6)
    content = messages[-1]["content"]

    assert "<evidence_units>" in content
    assert "Important opening source quote." in content
    assert "Important closing source quote." in content
    assert "source_text_original_chars" in content
    assert "source_text_truncated_for_coding" in content
    assert "source span compacted for model context" in content
    assert len(content) < len(long_text) + 5500


@pytest.mark.asyncio
async def test_pi_coder_runner_dispatches_structured_with_coding_schema(monkeypatch):
    """W9: ``_default_coder_runner`` was retired with the legacy plane; the
    dual-coder path runs through ``_pi_coder_runner`` → ``agentic.structured``
    with the coding schema, pinned to the coder's endpoint."""
    captured: dict[str, object] = {}

    class _StubAgentic:
        async def structured(self, **kwargs):  # noqa: ANN001
            captured.update(kwargs)
            return SimpleNamespace(
                text='{"applications": []}',
                value={"applications": []},
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id="endpoint-a",
                model="model-a",
                served_model="model-a",
                tool_calls=[],
            )

    monkeypatch.setattr("app.core.agentic.agentic", _StubAgentic())

    coder = research_validity_service.CoderSpec(
        node=SimpleNamespace(
            node_id="donor-a",
            provider_type="ollama",
            endpoint_id="endpoint-a",
        ),
        coder_id="model-coder:model-a",
        model_name="model-a",
    )

    result = await research_validity_service._pi_coder_runner(
        coder,
        [{"role": "user", "content": "code these evidence units"}],
        "model-a",
        "project-a",
    )

    assert captured["purpose"] == "validity.coder"
    assert captured["schema"] is research_validity_service.CODING_RESPONSE_SCHEMA
    assert "applications" in captured["schema"]["properties"]
    assert captured["project_id"] == "project-a"
    assert captured["params"].endpoint_id == "endpoint-a"
    assert result["_istara_route"]["endpoint_id"] == "endpoint-a"


@pytest.mark.asyncio
async def test_pi_coder_runner_forwards_request_scoped_pi_service(monkeypatch):
    """Selection and structured dispatch must carry one explicit Pi service."""
    captured: dict[str, object] = {}

    class _StubAgentic:
        async def structured(self, **kwargs):  # noqa: ANN001
            captured.update(kwargs)
            return SimpleNamespace(
                value={"applications": []},
                endpoint_id="endpoint-a",
                model="model-a",
                served_model="model-a",
            )

    scoped_service = object()
    monkeypatch.setattr("app.core.agentic.agentic", _StubAgentic())
    coder = research_validity_service.CoderSpec(
        node=SimpleNamespace(
            node_id="donor-a",
            name="donor-a",
            source="pi",
            provider_type="ollama",
            endpoint_id="endpoint-a",
        ),
        coder_id="model-coder:model-a",
        model_name="model-a",
        pi_service=scoped_service,
    )

    await research_validity_service._pi_coder_runner(
        coder,
        [{"role": "user", "content": "code these evidence units"}],
        "model-a",
        "project-a",
    )

    assert captured["pi_service"] is scoped_service


@pytest.mark.asyncio
async def test_pi_coder_runner_rejects_mismatched_served_endpoint(monkeypatch):
    """A provider cannot rewrite the endpoint identity used for spine evidence."""
    from types import SimpleNamespace

    class _MismatchedAgentic:
        async def structured(self, **_kwargs):  # noqa: ANN001
            return SimpleNamespace(
                value={"applications": []},
                endpoint_id="endpoint-other",
            )

    monkeypatch.setattr("app.core.agentic.agentic", _MismatchedAgentic())
    coder = research_validity_service.CoderSpec(
        node=SimpleNamespace(
            node_id="donor-a",
            provider_type="ollama",
            endpoint_id="endpoint-a",
        ),
        coder_id="model-coder:model-a",
        model_name="model-a",
    )

    with pytest.raises(ValueError, match="Pi coder endpoint mismatch"):
        await research_validity_service._pi_coder_runner(
            coder,
            [{"role": "user", "content": "code these evidence units"}],
            "model-a",
            "project-a",
        )
