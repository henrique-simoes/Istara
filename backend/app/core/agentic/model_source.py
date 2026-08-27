"""Unified model-source resolution — pi model management serves BOTH engines.

CF-SPEC-1 Phase 6 (DEC-10): the agentic engine a user selects owns the LOOP
(tool orchestration, steering, budgets); pi model management owns provider
communication for either engine. This resolver answers one question per turn:

    which concrete endpoint/model should serve this request, and from which
    source plane?

Precedence (owner-approved):
  1. Explicit user selection wins outright (the chat picker's model).
  2. The Pi-managed catalog resolves that selection, including local
     Ollama/LM Studio entries and the sanctioned, identity-pinned Petals
     projection when donation consent, health, and project scope admit it.
  3. The legacy donation-pool path remains a compatibility boundary only when
     no Pi catalog identity resolves; it is never returned as a false Pi source.

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


async def _configured_pi_endpoint(model: str | None, project_id: str | None = None):
    """Return one admitted pi-managed endpoint matching *model*, else None.

    Endpoints whose provider_kind is ``openai_codex`` are excluded here: that
    wire family is the Pi engine's native transport (Responses API), not the
    OpenAI-compatible chat shape this bridge speaks. Users select those models
    with the Pi core; the Istara core resolves every other plane.
    """
    try:
        manager = _pi_manager()
        await manager.ensure_db_projection()
        candidates = [
            info
            for info in manager.catalog()
            if getattr(info, "provider_kind", "") != "openai_codex"
            and not (
                getattr(settings, "llm_provider_contract_stub", False)
                and getattr(info, "kind", "") == "local"
            )
        ]
        if model:
            candidates = [
                info for info in candidates if str(getattr(info, "model", "")) == model
            ]
        for target in candidates:
            try:
                return manager.resolve(
                    endpoint_id=getattr(target, "endpoint_id", None),
                    model=model or None,
                    project_id=project_id,
                )
            except Exception:  # noqa: BLE001 — skip an inadmissible candidate
                # A project-scoped Petals projection may be visible in the
                # catalog but not authorized for this request. Continue to a
                # later admitted endpoint instead of letting catalog order
                # decide availability or leaking cross-project capacity.
                continue
        return None
    except Exception:  # noqa: BLE001 — resolution is best-effort; registry path remains
        logger.debug("model_source: pi-managed resolution unavailable", exc_info=True)
        return None


async def resolve_model_source(
    model: str | None = None, project_id: str | None = None
) -> ModelSource | None:
    """Resolve one turn's model source by the approved precedence.

    Returns ``None`` when no non-stub source can serve the request; callers
    fail closed with their own actionable error.
    """
    # Every selection, including local Ollama/LM Studio defaults, resolves
    # through PiModelManager.  Returning a separate local-direct source here
    # would make the legacy preflight disagree with the actual provider
    # service, which already uses the Pi manager.
    if model:
        endpoint = await _configured_pi_endpoint(model, project_id)
        if endpoint is None:
            return None
        return ModelSource(
            plane=PLANE_PI_MANAGED,
            endpoint_id=endpoint.endpoint_id,
            base_url=endpoint.base_url,
            api_key=endpoint.api_key,
            model=endpoint.model,
        )

    # No explicit selection: PiModelManager owns the default catalog choice.
    endpoint = await _configured_pi_endpoint(None, project_id)
    if endpoint is not None:
        return ModelSource(
            plane=PLANE_PI_MANAGED,
            endpoint_id=endpoint.endpoint_id,
            base_url=endpoint.base_url,
            api_key=endpoint.api_key,
            model=endpoint.model,
        )
    return None


async def has_non_stub_source(project_id: str | None = None) -> bool:
    """Whether ANY non-stub source could serve a legacy-plane turn right now."""
    return await resolve_model_source(None, project_id=project_id) is not None
