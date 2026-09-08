"""Shared policy for Pi endpoint creation and sparse updates.

POST and PUT are one authority boundary: catalog-derived transport fields,
endpoint validation, and credential custody must not drift between them.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from fastapi import HTTPException

from app.config import PiApiEndpoint, _read_pi_endpoint_secret

logger = logging.getLogger(__name__)


def provider_kind_for_catalog_api(api: str) -> str:
    """Map a pi-ai registry ``api`` value onto the Istara ``provider_kind``.

    Worker-side mirror: ``pi-runtime/src/provider.mjs::providerKindForRegistryApi``.
    The two tables MUST agree on every pi-ai KnownApi value —
    ``tests/pi_compat/test_transport_conformance.py::test_kind_mapping_parity_node_python``
    fails the gate on drift. Registry apis with no Istara transport fall through
    to the legacy rule so the worker's typed ``provider_transport_mismatch``
    rejection (not a misshapen request) is what surfaces at bind time.
    """
    normalized = str(api or "").lower()
    if normalized == "openai-codex-responses":
        return "openai_codex"
    if normalized == "openai-responses":
        return "openai_responses"
    if "anthropic" in normalized:
        return "anthropic_compat"
    return "openai_compat"


def reconciled_provider_kind(
    stored_kind: str,
    pi_provider: str = "",
    model: str = "",
    auth_provider: str = "",
) -> str:
    """Re-derive ``provider_kind`` for a catalog-managed endpoint (FIX F-4).

    F-1 repaired only the DERIVATION path (``_apply_catalog_fields`` on
    POST/PUT). Endpoints persisted BEFORE that fix carry a stale stored kind
    (``openai_compat`` for every ``openai-responses`` record) that would
    otherwise reach the worker verbatim and trip the typed
    ``provider_transport_mismatch`` rejection at bind time.

    Catalog-managed means non-empty ``pi_provider`` (falling back to
    ``auth_provider``) plus a non-empty ``model`` that resolves to a catalog
    record. Non-catalog endpoints (custom gateways, local serving, Petals,
    faux, LLMServer projections) return ``stored_kind`` untouched, preserving
    byte-identical legacy behavior (AC-1). Unknown providers/models and
    catalog-load failures also fail safe to ``stored_kind``.

    This is the single reconciliation helper: the resolver, the catalog
    manager, and the bind payload all funnel through it so a stale stored
    kind can never reach the worker, with no data migration required.
    """
    stored = str(stored_kind or "openai_compat")
    provider = str(pi_provider or auth_provider or "").strip().lower()
    model_id = str(model or "").strip()
    if not provider or not model_id:
        return stored
    try:
        from app.core.pi_runtime.catalog import load_catalog

        provider_models = load_catalog().get(provider)
        if not provider_models:
            return stored
        match = next((m for m in provider_models if m.get("id") == model_id), None)
        if not match:
            return stored
        api = str(match.get("api") or "").strip()
        if not api:
            return stored
        derived = provider_kind_for_catalog_api(api)
        if derived != stored:
            logger.debug(
                "pi endpoint: reconciled stale provider_kind %s -> %s for %s/%s",
                stored,
                derived,
                provider,
                model_id,
            )
        return derived
    except Exception:
        return stored


def _apply_catalog_fields(
    payload: dict[str, Any],
    provided_fields: set[str] | None = None,
    preserved_fields: set[str] | None = None,
) -> None:
    """Fill tier-4 catalog facts into a POST/PUT payload (plan W3.3).

    Merge law per §1.2 of the consensus plan — per field, never per record:

    - identity/transport fields (``provider_kind``, ``base_url``, ``model``,
      ``context_window``, ``max_tokens``) are catalog-managed and overwritten
      unconditionally — the bind-time reconciliation (F-4) independently
      guards ``provider_kind``.
    - capability advertisements (``supports_vision``, ``supports_reasoning``)
      are TRI-STATE operator overrides: tiers 1-3 may only RESTRICT the tier-4
      record, never enable beyond it, and an explicit value must survive POST
      and sparse PUT (AC-4). ``supports_reasoning=None`` (explicit null) means
      "defer to tier-4 authority" and is preserved, not collapsed.
    - per-Mtok rates are tier-2 operator contract pricing (DEC-M3): a
      provided or persisted operator rate always wins; the tier-4 list price
      only fills what the operator did not state.

    ``provided_fields`` are keys the client explicitly sent (pydantic
    ``model_fields_set``); ``preserved_fields`` are keys backfilled from the
    persisted endpoint on a sparse PUT. Both must survive verbatim — only the
    unset remainder is filled from the catalog.

    Provenance on identity change (FIX F-14): when a sparse PUT switches
    ``pi_provider``/``pi_model``, a persisted value that merely equals the
    OLD catalog record is a tier-4 fill, not a tier-2 operator override, and
    must NOT survive — otherwise the old model's rates/vision freeze and the
    AC-6 preflight is bypassed. ``prepare_pi_endpoint_payload`` strips such
    fills from ``preserved_fields`` before calling here (comparing the
    persisted endpoint against the old record); only a persisted value that
    DIFFERS from the old record (a genuine operator veto/contract rate) or a
    value in ``provided_fields`` survives. Same-model PUTs keep full
    preservation (AC-4).
    """
    provided = provided_fields or set()
    preserved = preserved_fields or set()
    provider = str(payload.get("pi_provider") or "").strip().lower()
    model_id = str(payload.get("pi_model") or "").strip()
    if not provider or not model_id:
        return

    from app.core.pi_runtime.catalog import load_catalog

    provider_models = load_catalog().get(provider)
    if not provider_models:
        raise HTTPException(status_code=400, detail=f"unknown pi provider: {provider}")
    match = next((model for model in provider_models if model["id"] == model_id), None)
    if not match:
        raise HTTPException(status_code=400, detail=f"unknown pi model: {model_id}")

    api = str(match.get("api", "").lower())
    payload["provider_kind"] = provider_kind_for_catalog_api(api)
    payload["base_url"] = match.get("baseUrl") or payload.get("base_url")
    payload["model"] = match["id"]
    payload["context_window"] = int(match.get("contextWindow") or 0)
    payload["max_tokens"] = int(match.get("maxTokens") or 0)
    # ``supports_vision``: monotonic restriction (tier 3 over tier 4). An
    # explicit operator value may narrow the record's modalities, never add
    # one; unset falls to the catalog advertisement.
    catalog_vision = "image" in (match.get("input") or [])
    if "supports_vision" in provided or "supports_vision" in preserved:
        payload["supports_vision"] = bool(payload.get("supports_vision")) and catalog_vision
    else:
        payload["supports_vision"] = catalog_vision
    # ``supports_reasoning``: tri-state. Explicit false is a tier-2 veto that
    # survives POST and sparse PUT (AC-4); explicit true cannot enable a
    # record that denies reasoning (monotonic); explicit null defers to the
    # tier-4 record and survives verbatim; unset fills from the record.
    if "reasoning" in match:
        catalog_reasoning = bool(match["reasoning"])
        if "supports_reasoning" in provided or "supports_reasoning" in preserved:
            advertised = payload.get("supports_reasoning")
            if advertised is None:
                payload["supports_reasoning"] = None
            else:
                payload["supports_reasoning"] = bool(advertised) and catalog_reasoning
        else:
            payload["supports_reasoning"] = catalog_reasoning
    cost = match.get("cost") or {}
    catalog_rates = {
        "cost_input_per_mtok": float(cost.get("input") or 0.0),
        "cost_output_per_mtok": float(cost.get("output") or 0.0),
        "cost_cache_read_per_mtok": float(cost.get("cacheRead") or 0.0),
        "cost_cache_write_per_mtok": float(cost.get("cacheWrite") or 0.0),
    }
    for rate_field, catalog_rate in catalog_rates.items():
        if rate_field in provided or rate_field in preserved:
            # Tier-2 operator contract pricing owns its fields outright
            # (DEC-M3) — including an explicit 0.0, which the admission
            # preflight below treats as unpriced rather than overwriting.
            payload[rate_field] = float(payload.get(rate_field) or 0.0)
        else:
            payload[rate_field] = catalog_rate
    payload["pi_provider"] = provider
    payload["auth_provider"] = str(payload.get("auth_provider") or provider).strip()
    payload["auth_method"] = str(payload.get("auth_method") or "api_key").strip()
    if not str(payload.get("keychain_service") or "").strip():
        payload["keychain_service"] = (
            f"istara-pi-oauth-{payload['auth_provider']}"
            if payload["auth_method"].startswith("oauth")
            else f"istara-pi-{provider}"
        )


# Every spend category the worker prices per run (pi-runtime/src/session.mjs
# ``_hasUnpricedSpend``). input/output are spent by every real turn; cache
# categories are conditional on provider caching behavior, so they cannot fail
# admission by themselves — but they are NAMED in the error so an operator can
# supply every needed tier-2 rate in one round-trip.
_PRICING_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("cost_input_per_mtok", "input"),
    ("cost_output_per_mtok", "output"),
    ("cost_cache_read_per_mtok", "cache_read"),
    ("cost_cache_write_per_mtok", "cache_write"),
)


def _governed_overlay_providers() -> set[str]:
    """Provider ids owned by governed custom-provider overlays (tier 5).

    Overlay pricing is hand-owned data (plan W1.2); its zero rates are a
    known overlay gap, NOT S-E3's upstream zero-pricing, so overlay endpoints
    keep today's admission behavior and the mid-run ``cost_budget_unpriced``
    terminal as their guard. Repricing an overlay is an owner decision.
    """
    try:
        from app.core.pi_runtime.catalog import catalog_provenance

        return {
            str(provider_id)
            for provider_id in (catalog_provenance().get("governed_custom_providers") or [])
        }
    except Exception:
        return set()


def _enforce_budget_pricing_preflight(payload: dict[str, Any]) -> None:
    """Admission-time pricing preflight for budgeted runs (plan W3.4 / S-E3).

    The supervisor budgets every run (``max_cost_usd`` defaults finite), and
    the worker fails a budgeted run closed when it spends tokens in a category
    left at a $0 rate. 121 of 1,312 upstream registry models are themselves
    zero-priced in pi-ai (including ``zai/glm-5.3``), so such an endpoint can
    never serve a budgeted turn — the failure would only surface mid-run.
    Admission instead fails here, naming the unpriced categories, unless the
    operator supplies tier-2 contract rates. Governed overlays are exempt
    (hand-owned pricing); non-catalog endpoints keep today's behavior.
    """
    provider = str(payload.get("pi_provider") or "").strip().lower()
    if not provider or provider in _governed_overlay_providers():
        return
    unpriced = [
        label
        for field, label in _PRICING_CATEGORIES
        if not (float(payload.get(field) or 0.0) > 0.0)
    ]
    guaranteed_unpriced = [label for label in unpriced if label in ("input", "output")]
    if not guaranteed_unpriced:
        return
    raise HTTPException(
        status_code=400,
        detail=(
            "pi_endpoint_unpriced: this model has no positive rate for budgeted runs "
            "in: "
            + ", ".join(unpriced)
            + " — supply operator contract rates (USD per 1M tokens) for the "
            "unpriced categories via cost_input_per_mtok/cost_output_per_mtok "
            "(+ cost_cache_read/write_per_mtok) on POST /api/settings/pi-endpoints "
            "(or PUT /api/settings/pi-endpoints/{endpoint_id} for an existing "
            "endpoint; the Settings > Pi Model Management form exposes the same "
            "contract-rate fields), or the run fails closed with cost_budget_unpriced"
        ),
    )


def _validate_endpoint_fields(payload: dict[str, Any]) -> None:
    payload["base_url"] = str(payload.get("base_url") or "").strip()
    payload["model"] = str(payload.get("model") or "").strip()
    payload["keychain_service"] = str(payload.get("keychain_service") or "").strip()
    if not payload["base_url"] or not payload["model"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "base_url and model are required — select a Pi provider+model "
                "from the catalog or provide them explicitly"
            ),
        )
    if not payload["base_url"].startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise HTTPException(status_code=400, detail="base_url must be https (or loopback)")
    if not payload["keychain_service"]:
        raise HTTPException(
            status_code=400,
            detail="keychain_service is required (Pi endpoints resolve secrets via Keychain)",
        )


# Catalog-managed fields whose persisted value needs provenance on a model
# switch (FIX F-14). Identity/transport fields are always overwritten by
# ``_apply_catalog_fields`` so they need no filtering; these are the fields
# where "persisted" is ambiguous between a tier-2 operator override and a
# tier-4 fill of the previous model.
_CATALOG_MANAGED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "cost_input_per_mtok",
    "cost_output_per_mtok",
    "cost_cache_read_per_mtok",
    "cost_cache_write_per_mtok",
    "supports_vision",
    "supports_reasoning",
)

_COST_FIELD_TO_CATALOG_KEY: dict[str, str] = {
    "cost_input_per_mtok": "input",
    "cost_output_per_mtok": "output",
    "cost_cache_read_per_mtok": "cacheRead",
    "cost_cache_write_per_mtok": "cacheWrite",
}


def _lookup_catalog_record(provider: str, model_id: str) -> dict[str, Any] | None:
    """Return the catalog record for ``provider/model_id`` or ``None``."""
    try:
        from app.core.pi_runtime.catalog import load_catalog

        provider_models = load_catalog().get(str(provider or "").strip().lower())
        if not provider_models:
            return None
        return next(
            (m for m in provider_models if m.get("id") == model_id),
            None,
        )
    except Exception:
        return None


def _persisted_equals_old_catalog(
    field: str, persisted_value: Any, old_record: dict[str, Any] | None
) -> bool:
    """True when the persisted value is a tier-4 fill of the OLD record.

    A fill must be refreshed from the NEW record on a model switch; only a
    value that DIFFERS from the old record is a genuine tier-2 override that
    survives the switch. ``None`` old record (legacy/unknown old model)
    cannot prove tier-2, so it counts as a fill (refresh).
    """
    if old_record is None:
        return True
    if field in _COST_FIELD_TO_CATALOG_KEY:
        old_rate = float((old_record.get("cost") or {}).get(_COST_FIELD_TO_CATALOG_KEY[field]) or 0.0)
        try:
            persisted_rate = float(persisted_value or 0.0)
        except (TypeError, ValueError):
            return False
        return persisted_rate == old_rate
    if field == "supports_vision":
        old_vision = "image" in (old_record.get("input") or [])
        return bool(persisted_value) == old_vision
    if field == "supports_reasoning":
        if persisted_value is None:
            return False  # explicit defer-to-tier-4 intent always survives
        if "reasoning" not in old_record:
            return False  # no old authority to compare against; keep verbatim
        return bool(persisted_value) == bool(old_record.get("reasoning"))
    return False


def prepare_pi_endpoint_payload(data: Any, existing: PiApiEndpoint | None = None) -> dict[str, Any]:
    """Resolve catalog fields and validate a POST or sparse PUT payload."""
    payload = data.model_dump()
    provided_fields = set(getattr(data, "model_fields_set", set()))
    preserved_fields: set[str] = set()
    if existing is not None:
        for field, value in existing.model_dump().items():
            if field not in provided_fields:
                payload[field] = value
                preserved_fields.add(field)
        payload["endpoint_id"] = existing.endpoint_id
    if existing is not None:
        old_provider = str(
            getattr(existing, "pi_provider", "")
            or getattr(existing, "auth_provider", "")
            or ""
        ).strip().lower()
        old_model = str(getattr(existing, "model", "") or "").strip()
        new_provider = str(payload.get("pi_provider") or "").strip().lower()
        new_model = str(payload.get("pi_model") or "").strip()
        provider_switched = "pi_provider" in provided_fields and new_provider != old_provider
        model_switched = "pi_model" in provided_fields and new_model != old_model
        if provider_switched and "pi_model" not in provided_fields:
            # Provider-only switch: keep the model id so the new provider's
            # record is resolved instead of skipping the catalog entirely.
            payload["pi_model"] = old_model
            new_model = old_model
        if provider_switched or model_switched:
            old_record = (
                _lookup_catalog_record(old_provider, old_model)
                if old_provider and old_model
                else None
            )
            existing_dump = existing.model_dump()
            for field in _CATALOG_MANAGED_PROVENANCE_FIELDS:
                if field in provided_fields or field not in preserved_fields:
                    continue  # explicit in this PUT always wins; nothing to do
                if _persisted_equals_old_catalog(
                    field, existing_dump.get(field), old_record
                ):
                    # Tier-4 fill of the previous model — refresh from the new
                    # record (and let the AC-6 preflight judge the new rates).
                    preserved_fields.discard(field)
                # else: genuine tier-2 override (veto/contract rate) survives.
    _apply_catalog_fields(
        payload,
        provided_fields=provided_fields,
        preserved_fields=preserved_fields,
    )
    _validate_endpoint_fields(payload)
    _enforce_budget_pricing_preflight(payload)
    return payload


def _custody_api_key(data: Any, payload: dict[str, Any]) -> None:
    api_key = str(data.api_key or "").strip()
    if not api_key:
        existing = _read_pi_endpoint_secret(
            str(payload.get("endpoint_id") or ""),
            str(payload.get("keychain_service") or ""),
            str(payload.get("keychain_account") or ""),
        )
        if not existing:
            raise HTTPException(status_code=400, detail="pi_api_key_required")
        return
    try:
        if sys.platform == "darwin":
            # Keep raw credentials in macOS Keychain; never mirror them into
            # a checkout .env on the host.
            from app.config import _write_macos_keychain_secret

            stored = _write_macos_keychain_secret(
                payload["keychain_service"],
                payload.get("keychain_account") or "default",
                api_key,
            )
            if not stored:
                raise RuntimeError("macos_keychain_write_failed")
        else:
            # Linux Docker has no macOS Keychain. Persist the endpoint-scoped
            # env secret into the configured writable runtime env file so the
            # resolver can bind the endpoint after a restart.
            from app.config import _pi_endpoint_secret_env_name
            from app.core.env_persistence import persist_env_value

            env_name = _pi_endpoint_secret_env_name(payload["endpoint_id"])
            persist_env_value(env_name, api_key)
            # Runtime persistence alone is not visible to the current process.
            # Bind the just-custodied endpoint immediately so Chat works without
            # requiring a backend restart.
            os.environ[env_name] = api_key
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - platform custody failure
        logger.warning(
            "pi endpoint: keychain write failed for %s: %s",
            payload.get("endpoint_id", "<unknown>"),
            exc,
        )
        raise HTTPException(status_code=503, detail="pi_api_key_custody_failed") from exc


def pi_endpoint_credential_status(endpoint: PiApiEndpoint) -> str:
    """Return a secret-free, passive credential state for Settings UX."""
    auth_method = str(endpoint.auth_method or "api_key").strip().lower()
    if auth_method.startswith("oauth"):
        return "stored" if endpoint.oauth_credential_encrypted else "missing"
    secret = _read_pi_endpoint_secret(
        endpoint.endpoint_id,
        endpoint.keychain_service,
        endpoint.keychain_account,
    )
    return "ready" if secret else "missing"


def _custody_oauth(data: Any, payload: dict[str, Any], existing: PiApiEndpoint | None) -> None:
    from app.core.field_encryption import encrypt_field
    from app.core.pi_runtime.oauth import consume_oauth_credential

    flow_id = str(data.oauth_flow_id or "").strip()
    if not flow_id:
        if existing is not None and payload.get("oauth_credential_encrypted"):
            return
        raise HTTPException(status_code=400, detail="oauth_flow_id is required after Pi login")
    try:
        credential = consume_oauth_credential(
            str(payload.get("auth_provider") or payload.get("pi_provider") or ""),
            flow_id,
        )
        payload["oauth_credential_encrypted"] = encrypt_field(
            json.dumps(credential, separators=(",", ":"))
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - provider custody guard
        raise HTTPException(status_code=503, detail="oauth_credential_custody_failed") from exc


def custody_pi_endpoint_credentials(
    data: Any, payload: dict[str, Any], existing: PiApiEndpoint | None = None
) -> None:
    """Custody a new credential and preserve an existing OAuth credential."""
    auth_method = str(payload.get("auth_method") or "api_key").strip().lower()
    if auth_method.startswith("oauth"):
        _custody_oauth(data, payload, existing)
    else:
        _custody_api_key(data, payload)
        payload.pop("oauth_credential_encrypted", None)
