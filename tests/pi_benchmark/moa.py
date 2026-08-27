"""Research Spine MoA routing validation for the live benchmark (Lane B).

The backend's MoA entry points (:func:`app.core.validation.self_moa` and
:func:`app.core.validation.full_ensemble`) route through the AgenticDispatcher ensemble
verb and *fail closed on insufficient topology*: a ``full_ensemble`` request silently
degrades down the chain ``full_ensemble -> dual_run -> self_moa`` when fewer distinct
endpoints are admitted than requested, and the returned ``ValidationResult.method``
reports the method actually served. The Research Spine contract makes a downgraded
ensemble a *blocked/degraded* unit, never a reportable success — this module is the pure,
offline decision logic that detects that downgrade from the returned result and from a
dry-run topology probe.

Everything here is pure logic over duck-typed inputs; no backend, DB, network, or model
is imported, so the module is import-safe at determinism tier T0 and unit-tested with
fakes. The live driver (:mod:`tests.pi_benchmark.live_driver`) calls
:func:`assess_validation_result` and maps the verdict onto a run record.

Downgrade-string convention (one convention, used everywhere): ``"<requested>-><served>"``
when the served method differs from the requested one (e.g. ``"full_ensemble->dual_run"``),
``"partial_coder"`` when fewer successful responses/routes than requested were served,
``"single_coder"`` when a full_ensemble *was* served over fewer distinct routes than the
requested slots, and ``"model_identity_collapse"`` when endpoint diversity is present but
the served model identities are missing or duplicated.  The last case matters because the
Research Spine requires independent model identities, not merely endpoint replicas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

MOA_MODES: tuple[str, ...] = ("self_moa", "full_ensemble")

# The backend's self-MoA temperature sweep (app.core.validation.self_moa): the first
# three samples use [0.3, 0.7, 1.0], samples 4-5 extend with [0.5, 0.9]. Replicated here
# so the MoA evidence can record the *requested* sweep without importing the backend.
_SELF_MOA_BASE_TEMPS: tuple[float, ...] = (0.3, 0.7, 1.0)
_SELF_MOA_EXTRA_TEMPS: tuple[float, ...] = (0.5, 0.9)

RECONCILED = "reconciled"
DEGRADED = "degraded"
BLOCKED = "blocked"
NOT_RUN = "not_run"


@dataclass(frozen=True)
class MoaEvidence:
    """Verdict on one MoA-routed unit, carried in the record's ``extensions.moa``."""

    requested_mode: str            # "self_moa" | "full_ensemble"
    requested_samples: int         # moa_n samples (self_moa) or requested slots (full_ensemble)
    temperatures: tuple[float, ...]
    served_mode: str               # ValidationResult.method actually served
    response_count: int
    served_route_ids: tuple[str, ...]      # endpoint ids actually served (redacted ids ok)
    distinct_served_routes: int
    served_model_ids: tuple[str, ...]      # model identities actually served
    distinct_served_models: int
    coder_count: int               # successful responses actually used
    consensus_score: float | None  # consensus.agreement_score when exposed, else None
    consensus_confidence: str      # consensus.confidence when exposed, else ""
    source_unit_ids: tuple[str, ...]       # all dispatcher endpoint ids (attempt provenance)
    formal_reliability: bool        # true only when a formal coding run supplies it
    research_spine_eligible: bool   # response consensus alone is never Spine acceptance
    reconciliation_status: str     # "reconciled" | "degraded" | "blocked" | "not_run"
    downgrade: str | None          # None | "<requested>-><served>" | "partial_coder" | "single_coder" | "model_identity_collapse"
    degraded: bool


def self_moa_temperatures(n: int) -> tuple[float, ...]:
    """The temperature sweep the backend requests for ``self_moa(n=...)``."""
    temps = list(_SELF_MOA_BASE_TEMPS[:n])
    if n > len(_SELF_MOA_BASE_TEMPS):
        temps.extend(_SELF_MOA_EXTRA_TEMPS[: n - len(_SELF_MOA_BASE_TEMPS)])
    return tuple(temps)


def requested_slots(requested_mode: str, moa_n: int) -> int:
    """Distinct routes a MoA unit asks the dispatcher for.

    ``self_moa`` samples one endpoint ``moa_n`` times, so the sample count is ``moa_n``.
    ``full_ensemble`` requests ``min_responses + 1`` distinct endpoints and the backend
    requires ``min_responses >= 2`` (anything less is a dual_run), so the requested slot
    count is ``max(3, moa_n)`` — the live driver calls
    ``full_ensemble(min_responses=requested_slots - 1)``.
    """
    if requested_mode == "self_moa":
        return moa_n
    if requested_mode == "full_ensemble":
        return max(3, moa_n)
    raise ValueError(f"invalid moa mode {requested_mode!r}")


def _endpoint_ids_from(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return successful served ids separately from attempted/source ids.

    ``endpoint_ids`` is the dispatcher-level list and can include failed samples.  Only
    route evidence is emitted for successful samples by the backend validation path, so it
    is the authoritative source for served-route counts.  Keep all endpoint ids separately
    as provenance rather than allowing failed routes to make a partial MoA look complete.
    """
    route_evidence = tuple(metadata.get("route_evidence") or ())
    evidence_ids = tuple(
        str(route.get("endpoint_id")) for route in route_evidence if route.get("endpoint_id")
    )
    endpoint_ids = tuple(str(e) for e in (metadata.get("endpoint_ids") or ()))
    return evidence_ids, endpoint_ids or evidence_ids


def _model_ids_from(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return served model identities from successful route evidence.

    Route evidence is intentionally the source of truth for *served* identities.  The
    dispatcher-level endpoint list may include failed attempts, and an endpoint id is not
    a model identity: several endpoint replicas can all serve one model.  Missing model
    identities are retained as absent (rather than guessed from endpoint ids) so a live
    run cannot pass the independent-model gate by omission.
    """
    route_evidence = tuple(metadata.get("route_evidence") or ())
    return tuple(
        str(route.get("model")).strip()
        for route in route_evidence
        if route.get("model") and str(route.get("model")).strip()
    )


def assess_validation_result(
    *,
    requested_mode: str,
    requested_samples: int,
    temperatures: tuple[float, ...] = (),
    result: Any,
) -> MoaEvidence:
    """Assess a ``validation.ValidationResult``-shaped object against what was requested.

    ``result`` is duck-typed: ``.method``, ``.responses`` (successful responses used),
    ``.consensus.agreement_score`` / ``.consensus.confidence``, and ``.metadata`` carrying
    ``endpoint_ids`` and ``route_evidence`` (each route a dict with an ``endpoint_id`` and,
    for full_ensemble acceptance, a served ``model`` identity).  The consensus fields are
    response-category agreement only; they are not Fleiss' kappa or a formal coding run.
    """
    if requested_mode not in MOA_MODES:
        raise ValueError(f"invalid requested_mode {requested_mode!r}")

    served_mode = str(getattr(result, "method", "") or "")
    responses = list(getattr(result, "responses", None) or [])
    metadata = dict(getattr(result, "metadata", None) or {})
    consensus = getattr(result, "consensus", None)
    consensus_score = getattr(consensus, "agreement_score", None) if consensus is not None else None
    confidence = str(getattr(consensus, "confidence", "") or "") if consensus is not None else ""

    served_route_ids, source_unit_ids = _endpoint_ids_from(metadata)
    served_model_ids = _model_ids_from(metadata)
    distinct_served = len({route for route in served_route_ids if route})
    distinct_served_models = len({model for model in served_model_ids if model})
    response_count = len(responses)
    successful_route_count = len(served_route_ids)

    downgrade: str | None = None
    degraded = False
    if response_count > 0:
        if served_mode != requested_mode:
            # The fail-closed chain served a different method than requested.
            downgrade = f"{requested_mode}->{served_mode}"
            degraded = True
        elif response_count < requested_samples or successful_route_count < requested_samples:
            # Dispatcher endpoint_ids may include failed samples; successful coders and
            # successful route evidence must both cover the requested MoA width.
            downgrade = "partial_coder"
            degraded = True
        elif requested_mode == "full_ensemble" and distinct_served < requested_samples:
            # Method held but diversity collapsed: fewer distinct routes than slots.
            downgrade = "single_coder"
            degraded = True
        elif requested_mode == "full_ensemble" and distinct_served_models < requested_samples:
            # Endpoint diversity is not model independence: replicas or missing identity
            # metadata cannot satisfy the Research Spine's independent-coder requirement.
            downgrade = "model_identity_collapse"
            degraded = True
        elif requested_mode == "self_moa" and distinct_served > 1:
            # A temperature sweep must collapse to ONE route; more is a routing anomaly.
            degraded = True

    if response_count == 0:
        reconciliation_status = BLOCKED
        degraded = True
    elif downgrade is not None:
        reconciliation_status = DEGRADED
    elif degraded or confidence == "insufficient":
        reconciliation_status = DEGRADED
    else:
        reconciliation_status = RECONCILED

    return MoaEvidence(
        requested_mode=requested_mode,
        requested_samples=requested_samples,
        temperatures=tuple(float(t) for t in temperatures),
        served_mode=served_mode,
        response_count=response_count,
        served_route_ids=served_route_ids,
        distinct_served_routes=distinct_served,
        served_model_ids=served_model_ids,
        distinct_served_models=distinct_served_models,
        coder_count=response_count,
        consensus_score=float(consensus_score) if consensus_score is not None else None,
        consensus_confidence=confidence,
        source_unit_ids=source_unit_ids,
        formal_reliability=False,
        research_spine_eligible=False,
        reconciliation_status=reconciliation_status,
        downgrade=downgrade,
        degraded=degraded,
    )


def not_run_evidence(
    *, requested_mode: str, requested_samples: int, temperatures: tuple[float, ...] = (),
) -> MoaEvidence:
    """Evidence placeholder for a MoA unit that was blocked before dispatch."""
    return MoaEvidence(
        requested_mode=requested_mode,
        requested_samples=requested_samples,
        temperatures=tuple(float(t) for t in temperatures),
        served_mode="",
        response_count=0,
        served_route_ids=(),
        distinct_served_routes=0,
        served_model_ids=(),
        distinct_served_models=0,
        coder_count=0,
        consensus_score=None,
        consensus_confidence="",
        source_unit_ids=(),
        formal_reliability=False,
        research_spine_eligible=False,
        reconciliation_status=NOT_RUN,
        downgrade=None,
        degraded=True,
    )


def record_status_for(evidence: MoaEvidence) -> tuple[str, str | None]:
    """Map MoA evidence onto a run-record ``(status, not_runnable_reason)``.

    A downgraded or otherwise degraded MoA unit is ``not_runnable`` with the typed reason
    ``other`` (the schema's reason enum has no MoA-specific value; the machine-readable
    detail lives in ``extensions.moa``). Only a clean, reconciled unit is ``ok``.
    """
    if evidence.degraded:
        return "not_runnable", "other"
    return "ok", None


def validate_topology(*, available_endpoint_ids: Iterable[str], requested_slots: int) -> dict[str, Any]:
    """Dry-run topology probe: what the dispatcher's fail-closed chain *would* serve.

    Pure computation over the id list — it never calls a provider, the dispatcher, or any
    element of ``available_endpoint_ids`` (ids may be opaque sentinels in tests), so it
    spends nothing. Duplicate ids count once (distinct by identity), mirroring the
    backend's ``distinct=True`` admission.

    Mirrors the backend chain for a ``full_ensemble`` request of ``requested_slots``
    distinct routes: enough distinct routes -> ``full_ensemble``; 2..slots-1 ->
    ``dual_run`` degrade; exactly 1 -> ``self_moa`` degrade; 0 -> ``blocked``.
    """
    if requested_slots < 1:
        raise ValueError("requested_slots must be >= 1")
    distinct = len(set(available_endpoint_ids))
    if distinct >= requested_slots:
        would_serve, would_degrade, downgrade = "full_ensemble", False, None
    elif distinct >= 2:
        would_serve, would_degrade, downgrade = "dual_run", True, "full_ensemble->dual_run"
    elif distinct == 1:
        would_serve, would_degrade, downgrade = "self_moa", True, "full_ensemble->self_moa"
    else:
        would_serve, would_degrade, downgrade = "blocked", True, None
    return {
        "requested_slots": requested_slots,
        "available_distinct": distinct,
        "would_serve_mode": would_serve,
        "would_degrade": would_degrade,
        "downgrade": downgrade,
    }
