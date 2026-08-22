from types import SimpleNamespace

import pytest

from app.core.pi_runtime.model_management_compat import SUPPORTED_PROVIDERS, plan_migration
from app.core.pi_runtime.model_manager import PiModelManager


@pytest.mark.parametrize("provider", sorted(SUPPORTED_PROVIDERS))
def test_plan_state_matches_catalog_projection_for_every_provider(provider):
    """Plan state and Pi catalog projection must agree for every provider.

    Regression for F-1: vllm/sglang/llamacpp/mlx used to be planned as
    `projected` while the catalog silently dropped the row (config loss at the
    migration gate), and anthropic_compat was plan-blocked while the catalog
    projected it. The manager imports SUPPORTED_PROVIDERS by construction, so
    this asserts the shared contract end to end.
    """
    row = SimpleNamespace(
        id=f"row-{provider}",
        name=f"{provider} server",
        provider_type=provider,
        host="http://localhost:8080/v1",
        is_local=True,
        is_relay=False,
        priority=10,
        capabilities='{"models": ["m1"], "context_window": 8192}',
        api_key="",
    )
    mapping = plan_migration([row])["mappings"][0]
    entry = PiModelManager._project_llm_server(row)
    # Plan outcome == catalog outcome: projected rows reach the catalog.
    assert mapping["state"] == "projected"
    assert mapping["canonical_endpoint_id"] == f"pi-llm-row-{provider}"
    assert entry is not None
    assert entry.endpoint_id == f"pi-llm-row-{provider}"
    expected_kind = "anthropic_compat" if provider.startswith("anthropic") else "openai_compat"
    assert entry.provider_kind == expected_kind
    assert entry.base_url == "http://localhost:8080/v1"
    assert entry.context_window == 8192


def test_plan_and_catalog_reject_unsupported_providers_identically():
    """A provider outside the shared set is blocked by the plan AND dropped by
    the catalog — never planned as projected while silently lost."""
    row = SimpleNamespace(
        id="row-unsupported",
        name="Unsupported",
        provider_type="future_provider",
        host="http://localhost:8080/v1",
        is_local=True,
        is_relay=False,
        priority=10,
        capabilities="{}",
        api_key="",
    )
    mapping = plan_migration([row])["mappings"][0]
    assert mapping["state"] == "blocked"
    assert mapping["reason"] == "unsupported_provider"
    assert PiModelManager._project_llm_server(row) is None


def test_plan_is_idempotent_and_preserves_source_rows():
    rows = [SimpleNamespace(id="a", name="A", provider_type="ollama", host="http://localhost:11434", is_local=True, is_relay=False, priority=1, capabilities="{}")]
    first = plan_migration(rows)
    second = plan_migration(rows)
    assert first == second
    assert first["delete_source_rows"] is False
    assert first["mappings"][0]["canonical_endpoint_id"] == "pi-llm-a"
    assert first["rollback"]["available"] is True


def test_plan_fails_closed_without_silent_fallback():
    rows = [
        SimpleNamespace(id="relay", provider_type="ollama", host="http://relay", is_relay=True),
        SimpleNamespace(id="bad", provider_type="unknown", host="http://bad", is_relay=False),
        SimpleNamespace(id="host", provider_type="ollama", host="", is_relay=False),
    ]
    plan = plan_migration(rows)
    assert plan["counts"] == {"projected": 0, "legacy_only": 1, "blocked": 2}
    assert {item["reason"] for item in plan["mappings"]} == {"relay_not_pi_catalog", "unsupported_provider", "invalid_host"}
