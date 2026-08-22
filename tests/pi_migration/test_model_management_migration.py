from types import SimpleNamespace

from app.core.pi_runtime.model_management_compat import plan_migration


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
