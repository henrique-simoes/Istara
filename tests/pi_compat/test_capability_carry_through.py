"""Capability carry-through conformance (build-stream 2026-09-08
pi-capability-inheritance, wave ``runtime-and-provider-integration``, plan W3).

The authority boundary (wave ``authority-and-boundary``) put pi-ai's tier-4
record behind the projection and the worker resolver. This module pins the
CARRY-THROUGH half — the fields must actually cross every boundary between
the shipped projection and a worker bind frame — plus the budget-integrity
admission preflight (S-E3) and the effort-ladder allowlist (W5.1):

- G8 carry-through: ``PiCatalogModel`` declares ``thinkingLevelMap``/``compat``
  so the loader cannot silently drop them again, and the settings catalog JSON
  carries them for registry models (null for governed overlays).
- Serializer drift contract: every key in every shipped catalog record is a
  declared ``PiCatalogModel`` field — a future pi-ai model field fails here
  loudly instead of vanishing at load (the exact G8 failure shape).
- Effort ladder: ``PI_THINKING_LEVEL_LADDER`` equals the union of
  ``thinkingLevelMap`` keys across the whole projection, so a pi-ai ladder
  change fails the backend gate (DEC-M2: never reimplement, only mirror).
- Tri-state advertisements (AC-4): an explicit ``supports_reasoning=false``
  veto survives POST and sparse PUT; explicit null defers to tier 4; an
  operator can never ENABLE beyond the record (monotonic restriction).
- Tier-2 pricing (DEC-M3): operator contract rates survive POST and sparse
  PUT; the tier-4 list price only fills what the operator did not state.
- Admission pricing preflight (S-E3/AC-6): an upstream zero-priced registry
  model is rejected at admission naming the unpriced categories, unless
  operator tier-2 rates are supplied; governed overlays and non-catalog
  endpoints keep today's behavior.
- Bind boundary (G12): ``_bind_payload`` forwards the advertised vision
  tri-state alongside ``supports_reasoning``.

All tests are offline: no network, no node required for the Python lanes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = (
    REPO_ROOT
    / "backend"
    / "app"
    / "core"
    / "pi_runtime"
    / "data"
    / "pi_models_catalog.json"
)

# S-E3/AC-6 unpriced-admission proof model. pi-ai 0.84.3 priced glm-5.3 at
# $0 across every category; upstream 0.85.1 repriced it to
# input 1.4 / output 4.4 / cacheRead 0.26 (intended-upstream, classified in
# docs/build-stream/pi-compat-20260908-0851-diff-proof.json). The proof moves
# to glm-5.3-highspeed, still $0 in every category in 0.85.1 — the preflight
# now guards 115 zero-priced upstream registry records (was 121) — counted
# under the admission code's own predicate (input or output rate not positive,
# governed `dashscope` overlay records excluded).
ZAI_ZERO_PRICED_MODEL = "glm-5.3-highspeed"
ZAI_PARTIAL_PRICED_MODEL = "glm-4.7"  # priced input/output, cacheWrite $0


def _raw_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _record(provider: str, model_id: str) -> dict:
    for model in _raw_catalog()[provider]:
        if model["id"] == model_id:
            return model
    raise AssertionError(f"{provider}/{model_id} missing from shipped catalog")


# ---------------------------------------------------------------------------
# G8 carry-through: the projection reaches the catalog API
# ---------------------------------------------------------------------------


def test_pi_catalog_model_declares_inherited_authority_fields():
    """G8 regression: the dataclass must declare the tier-4 fields.

    Wave 1 projected ``thinkingLevelMap``/``compat`` into the shipped file but
    left the dataclass without the fields, so the loader's
    ``__dataclass_fields__`` filter silently dropped them at load. Re-declaring
    is what makes ``pi_catalog_json()`` carry them.
    """
    from dataclasses import fields

    from app.core.pi_runtime.catalog import PiCatalogModel

    declared = {f.name for f in fields(PiCatalogModel)}
    assert "thinkingLevelMap" in declared
    assert "compat" in declared


def test_settings_catalog_json_carries_inherited_fields_for_registry_models():
    from app.core.pi_runtime.catalog import pi_catalog_json

    providers = {p["id"]: p for p in pi_catalog_json()}
    zai_models = {m["id"]: m for m in providers["zai"]["models"]}

    glm53 = zai_models[ZAI_ZERO_PRICED_MODEL]
    assert (
        glm53["thinkingLevelMap"]
        == _record("zai", ZAI_ZERO_PRICED_MODEL)["thinkingLevelMap"]
    )
    # The decisive zai compat fact (G5): the record says reasoning_effort is
    # supported even though URL detection alone would deny it.
    assert glm53["compat"]["supportsReasoningEffort"] is True
    assert glm53["compat"]["thinkingFormat"] == "zai"
    # DEC-M2: the emitted menu levels come from pi-ai's own derivation.
    assert glm53["thinkingLevels"] == ["low", "high", "max"]

    luna = {m["id"]: m for m in providers["openai-codex"]["models"]}["gpt-5.6-luna"]
    assert luna["thinkingLevelMap"]["minimal"] == "low"
    # G4: the tool-selection compat flags that select deferredToolsMode now
    # reach the API instead of being dropped at load.
    assert luna["compat"]["supportsAdditionalTools"] is True


def test_governed_overlay_models_carry_null_authority_fields():
    """Tier-5 overlays may leave the tier-4 fields null — tri-state preserved."""
    from app.core.pi_runtime.catalog import pi_catalog_json

    providers = {p["id"]: p for p in pi_catalog_json()}
    for model in providers["dashscope"]["models"][:5]:
        assert model["thinkingLevelMap"] is None or isinstance(
            model["thinkingLevelMap"], dict
        )
        assert model["compat"] is None or isinstance(model["compat"], dict)


def test_every_shipped_catalog_key_is_a_declared_serializer_field():
    """Serializer drift contract: a future pi-ai model field must fail loudly.

    The loader filters unknown keys via ``PiCatalogModel.__dataclass_fields__``
    — exactly the mechanism that silently dropped G8's fields. When pi-ai adds
    a model field and the projection is regenerated, this test fails until the
    serializer is consciously extended (the Python-side companion of the
    projection's ``model_field_set_hash``).
    """
    from dataclasses import fields

    from app.core.pi_runtime.catalog import PiCatalogModel

    declared = {f.name for f in fields(PiCatalogModel)}
    unknown: dict[str, set[str]] = {}
    for provider_id, models in _raw_catalog().items():
        if provider_id.startswith("__"):
            continue
        for model in models:
            extra = set(model) - declared
            if extra:
                unknown.setdefault(f"{provider_id}/{model.get('id')}", set()).update(
                    extra
                )
    assert not unknown, (
        "shipped catalog carries fields PiCatalogModel does not declare "
        f"(they would be silently dropped): {unknown}"
    )


def test_effort_ladder_matches_projection_map_key_union():
    """The backend ladder mirrors pi-ai's EXTENDED_THINKING_LEVELS.

    Derived from the projection itself: the union of ``thinkingLevelMap`` keys
    across every registry model is exactly pi-ai's ladder. If a pi bump adds,
    removes, or renames a level, regeneration changes the union and this gate
    fails until ``PI_THINKING_LEVEL_LADDER`` is consciously updated (W5.1).
    """
    from app.core.llm_thinking import PI_THINKING_LEVEL_LADDER

    map_keys: set[str] = set()
    for provider_id, models in _raw_catalog().items():
        if provider_id.startswith("__") or provider_id in ("dashscope",):
            continue  # governed overlays carry no tier-4 map
        for model in models:
            level_map = model.get("thinkingLevelMap")
            if isinstance(level_map, dict):
                map_keys.update(level_map.keys())
    assert map_keys, "projection carries no thinkingLevelMap keys — emitter drift"
    assert set(PI_THINKING_LEVEL_LADDER) == map_keys, (
        f"pi-ai effort ladder changed: projection keys {sorted(map_keys)} vs "
        f"backend ladder {sorted(PI_THINKING_LEVEL_LADDER)} — update "
        "PI_THINKING_LEVEL_LADDER and re-verify the worker clamp contract"
    )


# ---------------------------------------------------------------------------
# Effort allowlist (W5.1): unsupported effort is rejected, never clamped
# ---------------------------------------------------------------------------


def test_validate_model_effort_rejects_non_ladder_tokens():
    from app.core.llm_thinking import validate_model_effort

    for bad in ("medium_x", "turbo", "ultra", "banana"):
        with pytest.raises(ValueError, match="unsupported_model_effort"):
            validate_model_effort(bad)


def test_validate_model_effort_accepts_ladder_and_legacy_prompt_modes():
    from app.core.llm_thinking import PI_THINKING_LEVEL_LADDER, validate_model_effort

    assert validate_model_effort(None) == "server_default"
    assert validate_model_effort("server_default") == "server_default"
    for level in PI_THINKING_LEVEL_LADDER:
        assert validate_model_effort(level) == level
        assert validate_model_effort(level.upper()) == level
    # Legacy non-reasoning menu contract (ChatModelControls auto/on).
    assert validate_model_effort("auto") == "auto"
    assert validate_model_effort("on") == "on"


# ---------------------------------------------------------------------------
# Endpoint payload merge law: tri-state advertisements + tier-2 pricing
# ---------------------------------------------------------------------------


class _FakeRequest:
    """Minimal stand-in for ``PiEndpointRequest`` (pydantic fields_set)."""

    def __init__(self, payload: dict, provided: set[str]):
        self._payload = dict(payload)
        self._provided = set(provided)

    def model_dump(self) -> dict:
        return dict(self._payload)

    @property
    def model_fields_set(self) -> set[str]:
        return set(self._provided)


def _catalog_endpoint_payload(provider: str, model_id: str, **extra) -> dict:
    payload = {
        "endpoint_id": f"pi-{provider}-{model_id}".replace(".", "-"),
        "provider_kind": "openai_compat",
        "base_url": "",
        "model": "",
        "keychain_service": f"istara-pi-{provider}",
        "keychain_account": "",
        "timeout_ms": 30_000,
        "max_retries": 0,
        "cost_input_per_mtok": 0.0,
        "cost_output_per_mtok": 0.0,
        "cost_cache_read_per_mtok": 0.0,
        "cost_cache_write_per_mtok": 0.0,
        "context_window": 0,
        "max_tokens": 0,
        "supports_tools": True,
        "pi_provider": provider,
        "pi_model": model_id,
        "api_key": "",
        "supports_vision": False,
        "supports_reasoning": None,
        "auth_provider": "",
        "auth_method": "api_key",
        "oauth_flow_id": "",
    }
    payload.update(extra)
    return payload


def _prepare(
    provider: str, model_id: str, *, provided: set[str] | None = None, **extra
) -> dict:
    from app.core.pi_runtime.endpoint_policy import prepare_pi_endpoint_payload

    payload = _catalog_endpoint_payload(provider, model_id, **extra)
    fields_set = set(provided if provided is not None else {k for k in extra})
    return prepare_pi_endpoint_payload(_FakeRequest(payload, fields_set))


def test_explicit_reasoning_veto_survives_post():
    """AC-4: tier-2 false beats the tier-4 record — even on a reasoning model."""
    payload = _prepare(
        "deepseek",
        "deepseek-v4-pro",
        supports_reasoning=False,
    )
    assert payload["supports_reasoning"] is False


def test_explicit_reasoning_veto_survives_sparse_put():
    """AC-4: a sparse PUT that does not mention the capability keeps the veto."""
    from types import SimpleNamespace

    from app.core.pi_runtime.endpoint_policy import prepare_pi_endpoint_payload

    persisted = {
        "endpoint_id": "pi-deepseek-veto",
        "provider_kind": "openai_compat",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-pro",
        "keychain_service": "istara-pi-deepseek",
        "keychain_account": "",
        "timeout_ms": 30_000,
        "max_retries": 0,
        "cost_input_per_mtok": 8.0,  # operator contract rate (tier 2)
        "cost_output_per_mtok": 8.0,
        "cost_cache_read_per_mtok": 8.0,
        "cost_cache_write_per_mtok": 8.0,
        "context_window": 131072,
        "max_tokens": 8192,
        "supports_tools": True,
        "supports_vision": False,
        "supports_reasoning": False,  # persisted tier-2 veto
        "pi_provider": "deepseek",
        "auth_provider": "deepseek",
        "auth_method": "api_key",
        "oauth_credential_encrypted": "",
    }
    existing = SimpleNamespace(
        endpoint_id=persisted["endpoint_id"],
        model_dump=lambda: dict(persisted),
    )
    update = _FakeRequest(
        _catalog_endpoint_payload("deepseek", "deepseek-v4-pro", timeout_ms=45_000),
        provided={"timeout_ms", "endpoint_id"},
    )
    payload = prepare_pi_endpoint_payload(update, existing=existing)
    assert payload["timeout_ms"] == 45_000
    # Unrelated PUT: the veto AND the operator contract rates both survive.
    assert payload["supports_reasoning"] is False
    assert payload["cost_input_per_mtok"] == 8.0
    assert payload["cost_output_per_mtok"] == 8.0


def _real_post(provider: str, model_id: str, **extra):
    """POST via the real pydantic models (F-14: the _FakeRequest harness hid
    the sparse-PUT merge-law regression, so model-switch coverage uses the
    real ``PiEndpointRequest``/``PiApiEndpoint`` pair)."""
    from app.api.routes.settings import PiEndpointRequest
    from app.config import PiApiEndpoint
    from app.core.pi_runtime.endpoint_policy import prepare_pi_endpoint_payload

    payload = prepare_pi_endpoint_payload(
        PiEndpointRequest(
            endpoint_id=f"pi-{provider}-{model_id}".replace(".", "-"),
            keychain_service=f"istara-pi-{provider}",
            pi_provider=provider,
            pi_model=model_id,
            api_key="offline-test-key",
            **extra,
        )
    )
    persisted = PiApiEndpoint(
        **{k: v for k, v in payload.items() if k in PiApiEndpoint.model_fields}
    )
    return payload, persisted


def _real_sparse_put(persisted, **extra):
    """Sparse PUT via the real request model (only ``extra`` is provided)."""
    from app.api.routes.settings import PiEndpointRequest
    from app.core.pi_runtime.endpoint_policy import prepare_pi_endpoint_payload

    return prepare_pi_endpoint_payload(
        PiEndpointRequest(endpoint_id=persisted.endpoint_id, **extra),
        existing=persisted,
    )


def test_sparse_put_switch_priced_to_zero_priced_is_refused():
    """F-14: glm-4.7 (0.6/2.2) -> glm-5.3-highspeed ($0) must refuse like a
    direct POST. (Switched from glm-5.3: upstream 0.85.1 priced it.)"""
    _, persisted = _real_post("zai", "glm-4.7")
    assert persisted.cost_input_per_mtok == 0.6
    with pytest.raises(HTTPException) as excinfo:
        _real_sparse_put(persisted, pi_model="glm-5.3-highspeed")
    assert excinfo.value.status_code == 400
    assert str(excinfo.value.detail).startswith("pi_endpoint_unpriced")


def test_sparse_put_switch_to_zero_priced_admits_with_explicit_rates():
    """F-14: the same switch admits when the PUT states tier-2 rates."""
    _, persisted = _real_post("zai", "glm-4.7")
    payload = _real_sparse_put(
        persisted,
        pi_model="glm-5.3-highspeed",
        cost_input_per_mtok=1.0,
        cost_output_per_mtok=3.0,
        cost_cache_read_per_mtok=0.2,
        cost_cache_write_per_mtok=0.4,
    )
    assert payload["model"] == "glm-5.3-highspeed"
    assert payload["context_window"] == 1000000  # new record's transport
    assert payload["cost_input_per_mtok"] == 1.0
    assert payload["cost_output_per_mtok"] == 3.0


def test_sparse_put_switch_zero_priced_to_priced_refreshes_rates():
    """F-14 reverse: a contracted $0 endpoint switching to a priced model."""
    _, persisted = _real_post(
        "zai",
        "glm-5.3",
        cost_input_per_mtok=1.0,
        cost_output_per_mtok=3.0,
        cost_cache_read_per_mtok=0.2,
        cost_cache_write_per_mtok=0.4,
    )
    # Genuine tier-2 contract rates survive the switch (they differ from the
    # old $0 record), and the new record's transport is adopted.
    payload = _real_sparse_put(persisted, pi_model="glm-4.7")
    assert payload["model"] == "glm-4.7"
    assert payload["context_window"] == 204800
    assert payload["cost_input_per_mtok"] == 1.0
    assert payload["cost_output_per_mtok"] == 3.0


def test_sparse_put_switch_refreshes_vision_and_pricing_both_directions():
    """F-14: gpt-4 (text-only, 30/60) <-> gpt-4-turbo (vision, 10/30)."""
    _, persisted = _real_post("openai", "gpt-4")
    assert persisted.supports_vision is False
    forward = _real_sparse_put(persisted, pi_model="gpt-4-turbo")
    assert forward["model"] == "gpt-4-turbo"
    assert forward["supports_vision"] is True
    assert forward["cost_input_per_mtok"] == 10.0
    assert forward["cost_output_per_mtok"] == 30.0
    assert forward["context_window"] == 128000

    from app.config import PiApiEndpoint

    persisted_forward = PiApiEndpoint(
        **{k: v for k, v in forward.items() if k in PiApiEndpoint.model_fields}
    )
    backward = _real_sparse_put(persisted_forward, pi_model="gpt-4")
    assert backward["model"] == "gpt-4"
    assert backward["supports_vision"] is False
    assert backward["cost_input_per_mtok"] == 30.0
    assert backward["cost_output_per_mtok"] == 60.0


def test_sparse_put_switch_preserves_genuine_operator_veto():
    """F-14: an explicit veto (differs from the old record) survives a switch."""
    _, persisted = _real_post(
        "deepseek",
        "deepseek-v4-pro",
        supports_reasoning=False,
        cost_input_per_mtok=8.0,
        cost_output_per_mtok=8.0,
        cost_cache_read_per_mtok=8.0,
        cost_cache_write_per_mtok=8.0,
    )
    assert persisted.supports_reasoning is False
    payload = _real_sparse_put(persisted, pi_model="deepseek-v4-flash")
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["supports_reasoning"] is False
    assert payload["cost_input_per_mtok"] == 8.0


def test_explicit_reasoning_null_defers_and_survives():
    """Tri-state: explicit null means 'defer to tier 4' and is not collapsed."""
    payload = _prepare(
        "deepseek",
        "deepseek-v4-pro",
        supports_reasoning=None,
    )
    assert payload["supports_reasoning"] is None


def test_operator_cannot_enable_beyond_the_record():
    """Monotonic restriction: tiers 1-3 may never enable a denied capability."""
    payload = _prepare(
        "deepseek",
        "deepseek-v4-pro",
        supports_reasoning=True,
        supports_vision=True,
    )
    record = _record("deepseek", "deepseek-v4-pro")
    assert payload["supports_reasoning"] == bool(record["reasoning"])
    # A vision-capable advertisement cannot ADD the image modality.
    if "image" not in (record.get("input") or []):
        assert payload["supports_vision"] is False


def test_unset_advertisements_fill_from_catalog():
    payload = _prepare("deepseek", "deepseek-v4-pro")
    record = _record("deepseek", "deepseek-v4-pro")
    assert payload["supports_reasoning"] == bool(record["reasoning"])
    assert payload["supports_vision"] == ("image" in (record.get("input") or []))


def test_operator_tier2_rates_win_and_catalog_fills_the_rest():
    """DEC-M3: pi-ai owns list price; the operator owns contract price."""
    payload = _prepare(
        "deepseek",
        "deepseek-v4-pro",
        cost_input_per_mtok=9.5,
        cost_output_per_mtok=19.0,
    )
    assert payload["cost_input_per_mtok"] == 9.5
    assert payload["cost_output_per_mtok"] == 19.0
    # Untouched categories still fill from the tier-4 list price.
    record_cost = _record("deepseek", "deepseek-v4-pro")["cost"]
    assert payload["cost_cache_read_per_mtok"] == float(
        record_cost.get("cacheRead") or 0.0
    )
    assert payload["cost_cache_write_per_mtok"] == float(
        record_cost.get("cacheWrite") or 0.0
    )


# ---------------------------------------------------------------------------
# Admission pricing preflight (S-E3 / AC-6)
# ---------------------------------------------------------------------------


def test_upstream_zero_priced_model_fails_admission_naming_categories():
    """AC-6: zai/glm-5.3-highspeed is $0-priced in pi-ai itself — admission
    fails. (glm-5.3 held this role until upstream 0.85.1 priced it; see the
    ZAI_ZERO_PRICED_MODEL note.)"""
    with pytest.raises(HTTPException) as excinfo:
        _prepare("zai", ZAI_ZERO_PRICED_MODEL)
    assert excinfo.value.status_code == 400
    detail = str(excinfo.value.detail)
    assert detail.startswith("pi_endpoint_unpriced")
    for category in ("input", "output"):
        assert category in detail


def test_zero_priced_model_admits_with_operator_tier2_rates():
    """AC-6: supplied contract rates admit the endpoint."""
    payload = _prepare(
        "zai",
        ZAI_ZERO_PRICED_MODEL,
        cost_input_per_mtok=1.0,
        cost_output_per_mtok=3.0,
        cost_cache_read_per_mtok=0.2,
        cost_cache_write_per_mtok=0.4,
    )
    assert payload["cost_input_per_mtok"] == 1.0
    assert payload["cost_output_per_mtok"] == 3.0
    assert payload["pi_provider"] == "zai"
    assert payload["provider_kind"] == "openai_compat"


def test_conditionally_unpriced_cache_category_does_not_block_admission():
    """glm-4.7: priced input/output admits; conditional cache spend stays
    guarded by the retained mid-run ``cost_budget_unpriced`` terminal."""
    record = _record("zai", ZAI_PARTIAL_PRICED_MODEL)
    assert float(record["cost"]["input"]) > 0 and float(record["cost"]["output"]) > 0
    payload = _prepare("zai", ZAI_PARTIAL_PRICED_MODEL)
    assert payload["pi_provider"] == "zai"


def test_governed_overlay_endpoints_keep_today_admission_behavior():
    """Overlay pricing is hand-owned (W1.2): the preflight does not gate it."""
    model_id = min(
        m["id"]
        for m in _raw_catalog()["dashscope"]
        if not (m.get("cost") or {}).get("input")
    )
    payload = _prepare("dashscope", model_id)
    assert payload["pi_provider"] == "dashscope"
    assert payload["cost_input_per_mtok"] == 0.0


def test_non_catalog_endpoints_are_not_preflighted():
    """Manual endpoints keep legacy admission (AC-1 additive)."""
    from app.core.pi_runtime.endpoint_policy import prepare_pi_endpoint_payload

    payload = {
        "endpoint_id": "pi-manual-gateway",
        "provider_kind": "openai_compat",
        "base_url": "https://gateway.example.com/v1",
        "model": "gateway-model",
        "keychain_service": "istara-pi-manual",
        "keychain_account": "",
        "timeout_ms": 30_000,
        "max_retries": 0,
        "cost_input_per_mtok": 0.0,
        "cost_output_per_mtok": 0.0,
        "cost_cache_read_per_mtok": 0.0,
        "cost_cache_write_per_mtok": 0.0,
        "context_window": 0,
        "max_tokens": 0,
        "supports_tools": True,
        "pi_provider": "",
        "pi_model": "",
        "api_key": "",
        "supports_vision": False,
        "supports_reasoning": None,
        "auth_provider": "",
        "auth_method": "api_key",
        "oauth_flow_id": "",
    }
    prepared = prepare_pi_endpoint_payload(_FakeRequest(payload, set(payload)))
    assert prepared["cost_input_per_mtok"] == 0.0  # no tier-4 knowledge, no gate


# ---------------------------------------------------------------------------
# Bind boundary (G12): the advertised vision tri-state reaches the worker
# ---------------------------------------------------------------------------


def test_bind_payload_forwards_advertised_vision_and_reasoning():
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.engine import _bind_payload

    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-vision-check",
        provider_kind="openai_compat",
        base_url="https://api.example.com/v1",
        model="vision-model",
        api_key="offline-test-key",
        timeout_ms=30_000,
        max_retries=0,
        supports_vision=True,
        supports_reasoning=False,
    )
    payload = _bind_payload(endpoint)
    assert payload["supports_vision"] is True
    assert payload["supports_reasoning"] is False
    # Secrets/URL hygiene: the pricing block is present for real endpoints and
    # the receipt stays free of credential material.
    assert payload["pricing"]["input_per_mtok"] == 0.0


def test_bind_payload_keeps_fallback_vision_semantics_byte_compatible():
    """Legacy bindings: supports_vision=False binds text-only, as before G12.

    Pre-change the key was absent (worker saw undefined → ["text"]); sending
    False now is wire-identical for every fallback binding that never set it.
    """
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.engine import _bind_payload

    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-legacy-check",
        provider_kind="openai_compat",
        base_url="https://gateway.example.com/v1",
        model="legacy-model",
        api_key="offline-test-key",
        timeout_ms=30_000,
        max_retries=0,
    )
    payload = _bind_payload(endpoint)
    assert (
        payload["supports_vision"] is False
    )  # dataclass default, worker treats === false as text-only
    assert payload["supports_reasoning"] is None  # defer to tier 4/5 identity
