"""Unified model-source resolution — pi model management serves BOTH engines.

CF-SPEC-1 Phase 6 (DEC-10): the agentic engine a user selects owns the LOOP
(tool orchestration, steering, budgets); pi model management owns provider
communication for either engine. This resolver answers one question per turn:

    which concrete endpoint/model should serve this request, and from which
    source plane?

Precedence (owner-approved):
  1. Explicit user selection wins outright (the chat picker's model).
  2. An explicit local endpoint configured by the user.
  3. A pi-managed endpoint (execution-only bridge: never advertised to the
     compute pool, so donor-collision and research-spine routing guarantees
     are preserved).
  4. The donation pool (Petals) — handled by the existing compute-registry
     path; this resolver returns None and the caller proceeds as before.

Provenance is explicit on every resolved source so usage/UI surfaces can show
exactly where a turn was served from.

Stub planes are structurally unresolvable here: when the deployment declares
its Ollama-compatible plane as a deterministic wire stub
(``llm_provider_contract_stub``), that plane is invisible to this resolver —
Istara never executes chat over stubs in any environment (DEC-10).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

PLANE_PI_MANAGED = "pi-managed"
PLANE_LOCAL_DIRECT = "local-direct"


@dataclass(frozen=True)
class ModelSource:
    """One concrete, ready-to-call model endpoint plus its provenance."""

    plane: str
    endpoint_id: str
    base_url: str
    api_key: str
    model: str


def _pi_manager():
    from app.core.pi_runtime.model_manager import PiModelManager

    return PiModelManager()


def _configured_pi_endpoint(model: str | None):
    """Return one admitted pi-managed endpoint matching *model*, else None.

    Endpoints whose provider_kind is ``openai_codex`` are excluded here: that
    wire family is the Pi engine's native transport (Responses API), not the
    OpenAI-compatible chat shape this bridge speaks. Users select those models
    with the Pi core; the Istara core resolves every other plane.
    """
    try:
        manager = _pi_manager()
        candidates = [
            info
            for info in manager.catalog()
            if getattr(info, "provider_kind", "") != "openai_codex"
        ]
        if not candidates:
            return None
        if model:
            matches = [
                info for info in candidates if str(getattr(info, "model", "")) == model
            ]
            if not matches:
                return None
            target = matches[0]
        else:
            target = candidates[0]
        return manager.resolve(
            endpoint_id=getattr(target, "endpoint_id", None), model=model or None
        )
    except Exception:  # noqa: BLE001 — resolution is best-effort; registry path remains
        logger.debug("model_source: pi-managed resolution unavailable", exc_info=True)
        return None


def _local_direct_model() -> str | None:
    """The explicitly configured local model, or None when absent/stub-marked.

    On deployments whose Ollama-compatible plane is a declared wire stub, this
    plane does not exist as far as chat is concerned (DEC-10: Istara never uses
    stubs).
    """
    if getattr(settings, "llm_provider_contract_stub", False):
        return None
    for attr in ("ollama_model", "lmstudio_model"):
        value = str(getattr(settings, attr, "") or "").strip()
        if value and value.lower() != "default":
            return value
    return None


async def resolve_model_source(model: str | None = None) -> ModelSource | None:
    """Resolve one turn's model source by the approved precedence.

    Returns ``None`` when no non-stub source can serve the request; callers
    fail closed with their own actionable error.
    """
    # 1/2/3 — an explicit model selection resolves across planes by name.
    if model:
        endpoint = _configured_pi_endpoint(model)
        if endpoint is not None:
            return ModelSource(
                plane=PLANE_PI_MANAGED,
                endpoint_id=endpoint.endpoint_id,
                base_url=endpoint.base_url,
                api_key=endpoint.api_key,
                model=endpoint.model,
            )
        if _local_direct_model() == model:
            base = (
                settings.lmstudio_host
                if model == getattr(settings, "lmstudio_model", None)
                else settings.ollama_host
            )
            return ModelSource(
                plane=PLANE_LOCAL_DIRECT,
                endpoint_id="local-direct",
                base_url=str(base),
                api_key="",
                model=model,
            )
        return None  # donation pool / compute registry path handles its own routing

    # No explicit selection: preserve the legacy plane's historical default
    # (local/registry routing). A pi-managed endpoint becomes the fallback ONLY
    # where the local plane is a declared wire stub — so Istara never dies on
    # acceptance-style stacks once the user has configured an endpoint, while
    # normal dev machines keep serving from their local provider by default.
    local_model = _local_direct_model()
    if local_model:
        return ModelSource(
            plane=PLANE_LOCAL_DIRECT,
            endpoint_id="local-direct",
            base_url=str(settings.ollama_host),
            api_key="",
            model=local_model,
        )
    endpoint = _configured_pi_endpoint(None)
    if endpoint is not None:
        return ModelSource(
            plane=PLANE_PI_MANAGED,
            endpoint_id=endpoint.endpoint_id,
            base_url=endpoint.base_url,
            api_key=endpoint.api_key,
            model=endpoint.model,
        )
    return None


async def has_non_stub_source() -> bool:
    """Whether ANY non-stub source could serve a legacy-plane turn right now."""
    return await resolve_model_source(None) is not None
