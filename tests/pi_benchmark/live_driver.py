"""Live T2/T3 execution through the Istara dispatcher path (Lane B).

This driver replaces the old synthetic T2/T3 path: every live unit is dispatched for
real through the approved DeepSeek ``deepseek-v4-pro`` route as the ONLY provider
(DEC-5: local routes are disabled — there is no local-model path), under a shared
crash-safe budget ledger (Lane A's :class:`BudgetLedger`). F-11 (CF-320): BOTH engines
dispatch through ``AgenticDispatcher.ensemble`` — the pi arm pinned to the
``pi-deepseek-default`` PiModelManager endpoint, the legacy arm through the production
ComputeRegistry path onto the benchmark-seeded node
(:mod:`tests.pi_benchmark.registry_seed`), so the legacy DUT is the real production
legacy loop (registry selection → openai-compat transport → ``attach_route_evidence``),
not a benchmark-only side path.

Routing per unit:

* ``moa_mode is None`` — one ``agentic.ensemble`` sample (``n=1, distinct=False``); the
  engine (``pi`` | ``legacy``) comes from the unit. Pi units pin
  ``pi-deepseek-default`` via ``TurnParams.endpoint_id``; legacy units leave it unset so
  production registry selection routes to the seeded ``benchmark-deepseek-registry``
  node (registered before the first legacy dispatch via the provider's runtime key).
* ``moa_mode in {"self_moa", "full_ensemble"}`` — the benchmark-safe
  ``agentic.ensemble`` path with the unit's ``engine``, DeepSeek model, and approved
  endpoint pinned. All slots use the approved endpoint (``distinct=False``); a requested
  full ensemble therefore records route collapse as degraded rather than discovering
  local/other configured endpoints. :mod:`tests.pi_benchmark.moa` turns that into evidence
  and a downgraded ensemble is recorded ``not_runnable``, never ``ok``.

Spend discipline (fail closed everywhere):

1. A worst-case reservation (estimated prompt tokens + bounded ``max_tokens`` output,
   times the number of model calls the unit makes: 1 for plain units, ``moa_n`` samples
   for self_moa, ``max(3, moa_n)`` slots for full_ensemble) is reserved BEFORE dispatch.
   ``BudgetExceeded`` becomes a ``not_runnable/budget_exceeded`` record — the wave records
   the block and continues; it never raises out.
2. After dispatch, actual cost is computed from the provider pricing over the captured
   token counts and committed against the reservation.
3. Usage is provider-reported when the outcome exposes it (``estimate=False``); otherwise
   it is reconstructed with the documented deterministic ``chars4`` estimator
   (``ceil(chars/4)`` per text) over the ACTUAL prompt/response text (``estimate=True``,
   ``estimator="chars4"``). Numbers are never invented: if a successful-looking dispatch
   yields neither usage nor text, the unit is recorded ``not_runnable/other``
   (``unknown_usage_fail_closed``) and the reservation is RETAINED.
4. A dispatch exception releases the reservation ONLY when provably pre-dispatch
   (:class:`PreDispatchError`); anything else (including timeouts) retains it — money may
   already be in flight.

Records are written crash-safe: ``<unit_id>.json.tmp`` then ``os.replace`` to
``<unit_id>.json``, so a partial write never counts as complete, and a pre-existing valid
record makes :func:`run_live_unit` skip re-dispatch (resume/idempotency).

Import-safe at T0: importing this module touches no backend, DB, network, keychain, or
model. The backend is imported lazily inside :func:`dispatch_unit` at call time only;
tests inject ``ensemble_fn``/``agentic_module``/``dispatch`` fakes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import types
from dataclasses import asdict, dataclass, replace as dc_replace
from pathlib import Path
from typing import Any

from tests.pi_benchmark import moa, schema

try:  # Lane A module; fall back to a local twin until it lands.
    from tests.pi_benchmark.budget_ledger import BudgetExceeded, LedgerStateError
except ImportError:  # pragma: no cover - exercised only while Lane A is unmerged

    class BudgetExceeded(RuntimeError):  # type: ignore[no-redef]
        """Fallback twin of Lane A's BudgetExceeded (same name, same semantics)."""

    class LedgerStateError(ValueError):  # type: ignore[no-redef]
        """Fallback twin of Lane A's LedgerStateError (same name, same semantics)."""


DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_ENDPOINT_ID = "pi-deepseek-default"
DEEPSEEK_PROVIDER = "deepseek"
# The benchmark has one explicitly approved DeepSeek route. Repeating this route is
# valid for self-MoA; full ensembles remain visibly degraded instead of discovering
# local or unrelated configured endpoints.
APPROVED_DEEPSEEK_ENDPOINT_IDS = frozenset({DEEPSEEK_ENDPOINT_ID})
PI_PROJECT_ID = "pi-benchmark"

# CF-321 engine_path vocabulary from the owner raw-capture requirements doc.
ENGINE_PATHS = {"pi": "pi_candidate", "legacy": "baseline_istara"}
ESTIMATOR_CHARS4 = "chars4"

# Reservation sizing (same discipline as the provider adapter). Per model call, reserve a
# margin of input-priced tokens — 2x the chars4 estimate, floored at MIN_RESERVE_INPUT_TOKENS
# — plus the full DEFAULT_MAX_TOKENS output bound. Under-reserving is unsafe: the ledger
# refuses a commit whose actual cost exceeds its reservation, so a too-tight reservation
# turns a normal call into a post-dispatch LedgerStateError that would otherwise wedge the
# wave. The B0 estimate gate (runner --plan-only) reads both constants.
MIN_RESERVE_INPUT_TOKENS = 256
DEFAULT_MAX_TOKENS = 1024


class PreDispatchError(RuntimeError):
    """Raised by a dispatch callable when the failure is PROVABLY pre-dispatch.

    Only a failure carrying this type lets the driver release the reservation; every
    other dispatch failure retains it (fail closed — the request may have reached the
    provider).
    """


class RouteAdmissionError(RuntimeError):
    """Raised when a dispatched sample does not prove an approved benchmark route."""

    def __init__(self, message: str, *, route: dict[str, Any] | None = None) -> None:
        self.route = dict(route or {})
        super().__init__(message)


@dataclass(frozen=True)
class LiveCapture:
    """What one live dispatch actually returned (text + truthful usage provenance)."""

    text: str
    usage: dict[str, int] | None  # input/output/cache_read/cache_write/total tokens, or None (unknown)
    estimate: bool                # True when usage came from the chars4 estimator
    endpoint_ids: tuple[str, ...]
    route_evidence: tuple[dict, ...]
    raw_method: str | None        # validation method served, for MoA units
    consensus_score: float | None = None
    consensus_confidence: str = ""
    samples: tuple[dict, ...] = ()   # per-sample {text, usage, stop_reason, tool_calls} for raw capture
    capture_errors: tuple[str, ...] = ()  # raw-capture write failures (fail-soft, surfaced in extensions)


# ── token estimation / usage normalisation ──────────────────────────────────


def _chars4(text: str) -> int:
    """The one documented estimator: ceil(chars / 4) over actual text (``chars4``)."""
    return -(-len(text) // 4)


def _estimate_usage(*, prompt: str, system: str, output_texts: list[str]) -> dict[str, int]:
    input_tokens = _chars4(system + prompt)
    output_tokens = sum(_chars4(t) for t in output_texts)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": input_tokens + output_tokens,
    }


_USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "total_tokens")


def _normalize_usage(raw: Any) -> dict[str, int] | None:
    """Normalise a provider-reported usage block (dict or attribute object).

    Usable only when both input and output token counts are present; anything partial is
    rejected so the caller falls back to the documented estimator rather than zero-filling
    real spend. A missing ``total_tokens`` is filled by arithmetic (input + output).
    """
    if raw is None:
        return None
    getter = raw.get if isinstance(raw, dict) else lambda key, default=None: getattr(raw, key, default)
    values = {key: getter(key) for key in _USAGE_KEYS}
    if values["input_tokens"] is None or values["output_tokens"] is None:
        return None
    usage = {
        "input_tokens": int(values["input_tokens"]),
        "output_tokens": int(values["output_tokens"]),
        "cache_read_tokens": int(values["cache_read_tokens"] or 0),
        "cache_write_tokens": int(values["cache_write_tokens"] or 0),
    }
    usage["total_tokens"] = (
        int(values["total_tokens"])
        if values["total_tokens"] is not None
        else usage["input_tokens"] + usage["output_tokens"]
    )
    return usage


def _sum_sample_usage(samples: list[Any]) -> dict[str, int] | None:
    """Sum usable per-sample usage blocks; None when no sample exposes usage."""
    blocks = [b for b in (_normalize_usage(getattr(s, "usage", None)) for s in samples) if b]
    if not blocks:
        return None
    return {key: sum(block[key] for block in blocks) for key in _USAGE_KEYS}


# ── dispatch ────────────────────────────────────────────────────────────────


async def _init_db_best_effort() -> None:
    """Open the usage-ledger DB so the dispatcher can write exact rows (fail-soft)."""
    try:
        from app.models.database import init_db

        await init_db()
    except Exception:  # pragma: no cover - live-only path; ledger write is best-effort
        pass


def _sample_route_node_id(sample: Any) -> str:
    """Endpoint identity for one sample, tolerating both arm shapes.

    Pi samples carry ``endpoint_id`` directly (PiModelManager identity). Legacy
    samples carry the registry's ``route_evidence`` dict (``node_id``) propagated
    by ``agentic/legacy.py::_normalize_chat`` — that IS the legacy endpoint
    identity (F-11/AC-7 route truth for the legacy arm).
    """
    direct = str(getattr(sample, "endpoint_id", "") or "")
    if direct:
        return direct
    route = getattr(sample, "route_evidence", None)
    if isinstance(route, dict):
        return str(route.get("node_id") or "")
    return ""


def _capture_from_outcome(outcome: Any, *, prompt: str, system: str) -> LiveCapture:
    samples = list(getattr(outcome, "samples", None) or [])
    ok_samples = [s for s in samples if getattr(s, "status", None) == "success" and getattr(s, "text", "")]
    endpoint_ids = tuple(str(e) for e in (getattr(outcome, "endpoint_ids", None) or ()))
    if not endpoint_ids:
        endpoint_ids = tuple(_sample_route_node_id(s) for s in samples)
    route_evidence = []
    for index, sample in enumerate(samples):
        if getattr(sample, "status", None) != "success" or not getattr(sample, "text", ""):
            continue
        endpoint_id = (
            _sample_route_node_id(sample)
            or (endpoint_ids[index] if index < len(endpoint_ids) else "")
        )
        route_evidence.append({"endpoint_id": endpoint_id, "route_kind": "agentic_ensemble"})
    text = str(getattr(ok_samples[0], "text", "")) if ok_samples else ""
    usage = _normalize_usage(getattr(outcome, "usage", None)) or _sum_sample_usage(samples)
    estimate = False
    if usage is None and text:
        usage = _estimate_usage(prompt=prompt, system=system, output_texts=[text])
        estimate = True
    sample_dicts = tuple(
        {
            "text": str(getattr(sample, "text", "") or ""),
            "usage": _normalize_usage(getattr(sample, "usage", None)),
            "stop_reason": getattr(sample, "stop_reason", None),
            "tool_calls": list(getattr(sample, "tool_calls", None) or []),
            "status": getattr(sample, "status", None),
        }
        for sample in samples
    )
    return LiveCapture(
        text=text,
        usage=usage,
        estimate=estimate,
        endpoint_ids=endpoint_ids,
        route_evidence=tuple(route_evidence),
        raw_method=None,
        samples=sample_dicts,
    )


def _is_approved_route(engine: str, endpoint_id: str) -> bool:
    """Approved route identity per arm (AC-7 route truth).

    Pi units must serve from the pinned PiModelManager endpoint or — in the petals
    era (CF-338) — from bridge-projected ``pi-petals-*`` endpoints (projection
    itself enforces donor consent + health; the prefix is identity, not a bypass).
    Legacy units must serve from the benchmark-seeded registry node (F-11).
    Anything else is a rejected route, never a silently accepted one.
    """
    import tests.pi_benchmark.registry_seed as registry_seed

    if engine == "legacy":
        return endpoint_id == registry_seed.BENCHMARK_NODE_ID
    return endpoint_id in APPROVED_DEEPSEEK_ENDPOINT_IDS or endpoint_id.startswith("pi-petals-")


def _benchmark_route_evidence(
    *, samples: list[Any], endpoint_ids: tuple[str, ...], engine: str,
) -> tuple[dict, ...]:
    """Validate and redact the route identity returned by the benchmark dispatcher."""
    evidence: list[dict] = []
    for index, sample in enumerate(samples):
        endpoint_id = (
            _sample_route_node_id(sample)
            or (endpoint_ids[index] if index < len(endpoint_ids) else "")
        )
        if not endpoint_id:
            raise RouteAdmissionError(
                "benchmark sample has no endpoint identity",
                route={"route_kind": "agentic_ensemble", "admission": "rejected"},
            )
        if not _is_approved_route(engine, endpoint_id):
            raise RouteAdmissionError(
                f"benchmark route not approved: {endpoint_id!r}",
                route={
                    "endpoint_id": endpoint_id,
                    "route_kind": "agentic_ensemble",
                    "admission": "rejected",
                },
            )
        provider = str(getattr(sample, "provider", "") or DEEPSEEK_PROVIDER)
        model = str(getattr(sample, "model", "") or DEEPSEEK_MODEL)
        if provider != DEEPSEEK_PROVIDER or model != DEEPSEEK_MODEL:
            raise RouteAdmissionError(
                "benchmark sample provider/model is not DeepSeek-approved",
                route={
                    "endpoint_id": endpoint_id,
                    "provider": provider,
                    "model": model,
                    "route_kind": "agentic_ensemble",
                    "admission": "rejected",
                },
            )
        if getattr(sample, "status", None) != "success" or not getattr(sample, "text", ""):
            continue
        evidence.append({
            "endpoint_id": endpoint_id,
            "provider": provider,
            "model": model,
            "engine": engine,
            "route_kind": "agentic_ensemble",
        })
    return tuple(evidence)


def _benchmark_moa_capture(
    outcome: Any, *, prompt: str, system: str, engine: str, served_method: str,
) -> LiveCapture:
    """Capture MoA directly from the dispatcher without validation/embedding side effects."""
    samples = list(getattr(outcome, "samples", None) or [])
    endpoint_ids = tuple(str(e) for e in (getattr(outcome, "endpoint_ids", None) or ()))
    if not endpoint_ids:
        endpoint_ids = tuple(_sample_route_node_id(s) for s in samples)
    route_evidence = _benchmark_route_evidence(
        samples=samples, endpoint_ids=endpoint_ids, engine=engine,
    )
    responses = [
        str(getattr(sample, "text", ""))
        for sample in samples
        if getattr(sample, "status", None) == "success" and getattr(sample, "text", "")
    ]
    usage = _normalize_usage(getattr(outcome, "usage", None)) or _sum_sample_usage(samples)
    estimate = False
    if usage is None and responses:
        usage = _estimate_usage(prompt=prompt, system=system, output_texts=responses)
        estimate = True
    consensus_score = None
    consensus_confidence = ""
    if responses:
        # Consensus is deterministic and local. Do not call the validation embedding
        # helper: that work sits outside the benchmark's shared budget ledger and may
        # select a local embedding provider.
        from app.core.consensus import compute_consensus

        consensus = compute_consensus(responses, embeddings=None, method=served_method)
        consensus_score = consensus.agreement_score
        consensus_confidence = consensus.confidence
    sample_dicts = tuple(
        {
            "text": str(getattr(sample, "text", "") or ""),
            "usage": _normalize_usage(getattr(sample, "usage", None)),
            "stop_reason": getattr(sample, "stop_reason", None),
            "tool_calls": list(getattr(sample, "tool_calls", None) or []),
            "status": getattr(sample, "status", None),
        }
        for sample in samples
    )
    return LiveCapture(
        text=responses[0] if responses else "",
        usage=usage,
        estimate=estimate,
        endpoint_ids=endpoint_ids,
        route_evidence=route_evidence,
        raw_method=served_method,
        consensus_score=consensus_score,
        consensus_confidence=consensus_confidence,
        samples=sample_dicts,
    )



async def dispatch_unit(
    *,
    unit: Any,
    tier: str,
    prompt: str,
    system: str = "",
    moa_n: int = 3,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    ensemble_fn: Any = None,
    agentic_module: Any = None,
    provider: Any = None,
    capture: Any = None,
) -> LiveCapture:
    """Dispatch one unit through the backend dispatcher path and capture what came back.

    ``ensemble_fn``/``agentic_module`` inject fakes for tests; when both are None the
    backend is imported lazily here (and only here). Injected ``ensemble_fn`` receives the
    same kwargs as ``agentic.ensemble`` except ``params`` is a plain dict
    (``{"endpoint_id", "model", "max_tokens"}``) so tests never import backend types.

    F-11 (CF-320): BOTH engines dispatch through ``AgenticDispatcher.ensemble`` — the
    pi arm onto the pinned ``pi-deepseek-default`` endpoint, the legacy arm through the
    production registry path onto the benchmark-seeded node
    (:mod:`tests.pi_benchmark.registry_seed`). The seeded node is registered before the
    first legacy dispatch using the provider's runtime-resolved key.

    CF-321: when ``capture`` (a :class:`tests.pi_benchmark.raw_capture.RawCaptureWriter`)
    is provided, every prompt and output is retained as gzipped JSONL per the owner
    raw-capture requirements. Capture writes are fail-soft: failures never lose a paid
    dispatch result; they are returned in ``LiveCapture.capture_errors``.
    """
    engine = getattr(unit, "engine", None)
    if engine not in {"pi", "legacy"}:
        raise PreDispatchError(f"unsupported benchmark engine: {engine!r}")
    api_key: str | None = None
    if engine == "legacy":
        if provider is None:
            raise PreDispatchError("approved DeepSeek provider is required to seed the legacy registry node")
        try:
            api_key = provider.load_api_key()
        except Exception as exc:
            raise PreDispatchError(f"legacy registry seed failed: {exc}") from exc
        import tests.pi_benchmark.registry_seed as registry_seed

        try:
            registry_seed.ensure_benchmark_legacy_node(api_key=api_key)
        except Exception as exc:
            raise PreDispatchError(f"legacy registry seed failed: {exc}") from exc
    moa_mode = getattr(unit, "moa_mode", None)
    secret_values = (api_key,) if api_key else ()
    capture_errors: list[str] = []

    def _record_prompts(slots: int, temperatures: list[float]) -> None:
        if capture is None:
            return
        engine_path = ENGINE_PATHS[engine]
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        for index in range(slots):
            settings = {
                "max_tokens": max_tokens,
                "temperature": temperatures[index] if index < len(temperatures) else None,
                "thinking": "off",
                "timeout_s": 60,
                "retry_policy": "transient_registry_retry",
                "deepseek_key_present": True,
            }
            try:
                capture.record_prompt(
                    call_id=f"{unit.unit_id}:{engine}:{index + 1}",
                    scenario_id=getattr(unit, "scenario_id", ""),
                    engine_path=engine_path,
                    provider=DEEPSEEK_PROVIDER,
                    model=DEEPSEEK_MODEL,
                    adapter_mode="agentic_dispatcher",
                    settings=settings,
                    messages=messages,
                    secret_values=secret_values,
                )
            except Exception as exc:  # fail-soft: never lose a paid dispatch
                capture_errors.append(f"prompt_capture:{index + 1}:{exc}")

    def _record_outputs(cap: LiveCapture, latency_s: float) -> None:
        if capture is None:
            return
        engine_path = ENGINE_PATHS[engine]
        samples = cap.samples or (
            {"text": cap.text, "usage": cap.usage, "stop_reason": None, "tool_calls": [], "status": "success"},
        )
        for index, sample in enumerate(samples):
            usage = sample.get("usage")
            cost = None
            if usage and provider is not None:
                try:
                    cost = provider.estimate_cost(
                        input_tokens=int(usage.get("input_tokens", 0) or 0),
                        output_tokens=int(usage.get("output_tokens", 0) or 0),
                        cache_read_tokens=int(usage.get("cache_read_tokens", 0) or 0),
                        cache_write_tokens=int(usage.get("cache_write_tokens", 0) or 0),
                    )
                except Exception:
                    cost = None
            try:
                capture.record_output(
                    call_id=f"{unit.unit_id}:{engine}:{index + 1}",
                    scenario_id=getattr(unit, "scenario_id", ""),
                    engine_path=engine_path,
                    provider=DEEPSEEK_PROVIDER,
                    model=DEEPSEEK_MODEL,
                    content=str(sample.get("text") or ""),
                    tool_calls=list(sample.get("tool_calls") or []),
                    stop_reason=sample.get("stop_reason"),
                    error=None if sample.get("status") == "success" else str(sample.get("status") or "error"),
                    latency_s=round(latency_s, 4),
                    usage=usage,
                    cost_usd=cost,
                    secret_values=secret_values,
                )
            except Exception as exc:  # fail-soft
                capture_errors.append(f"output_capture:{index + 1}:{exc}")

    if moa_mode in moa.MOA_MODES:
        if agentic_module is None:
            await _init_db_best_effort()
            from app.core.agentic import agentic as agentic_module  # lazy (live path only)
        from app.core.agentic.types import TurnParams

        slots = moa.requested_slots(moa_mode, moa_n)
        temperatures = list(moa.self_moa_temperatures(moa_n)) if moa_mode == "self_moa" else []
        params = TurnParams(
            endpoint_id=DEEPSEEK_ENDPOINT_ID if engine == "pi" else None,
            model=DEEPSEEK_MODEL, max_tokens=max_tokens,
        )
        _record_prompts(slots, temperatures)
        started = time.perf_counter()
        # CF-338 (petals P3): full_ensemble requests TRUE distinct slots. Without
        # petals donors the pi catalog has only pi-deepseek-default (and the legacy
        # registry only the seeded node), so resolution fails closed and the unit is
        # recorded degraded — the same truthful result as the old forced-collapse,
        # now produced by real distinct-resolution instead of a hardcoded one. With
        # consented pi-petals-* endpoints projected, full_ensemble gets genuine
        # multi-node diversity with per-slot route evidence.
        outcome = await agentic_module.ensemble(
            purpose=f"pi_benchmark.{tier}",
            project_id=PI_PROJECT_ID,
            system=system or None,
            messages=[{"role": "user", "content": prompt}],
            n=slots,
            distinct=moa_mode == "full_ensemble",
            minimum_n=slots if moa_mode == "full_ensemble" else None,
            temperatures=temperatures or None,
            params=params,
            engine=unit.engine,
            spine_phase="review",
        )
        elapsed = time.perf_counter() - started
        # ``distinct=False`` is intentional: it forces every slot onto the one approved
        # DeepSeek endpoint. A full ensemble is then explicitly degraded by MoA evidence
        # instead of discovering local/other configured endpoints.
        cap = _benchmark_moa_capture(
            outcome, prompt=prompt, system=system, engine=unit.engine, served_method=moa_mode,
        )
        _record_outputs(cap, elapsed)
        return dc_replace(cap, capture_errors=tuple(capture_errors))

    # The pi arm pins the approved PiModelManager endpoint; the legacy arm leaves
    # endpoint_id unset so the production registry selection routes to the seeded
    # benchmark node (F-11: registry routing IS the legacy DUT behavior).
    params_payload = {
        "endpoint_id": DEEPSEEK_ENDPOINT_ID if engine == "pi" else None,
        "model": DEEPSEEK_MODEL,
        "max_tokens": max_tokens,
    }
    call_kwargs = dict(
        purpose=f"pi_benchmark.{unit.phase}",
        project_id=PI_PROJECT_ID,
        system=system or None,
        messages=[{"role": "user", "content": prompt}],
        n=1,
        distinct=False,
        engine=unit.engine,
    )
    _record_prompts(1, [])
    started = time.perf_counter()
    if ensemble_fn is not None:
        outcome = await ensemble_fn(params=params_payload, **call_kwargs)
    else:
        await _init_db_best_effort()
        from app.core.agentic import agentic  # lazy backend import (live path only)
        from app.core.agentic.types import TurnParams

        outcome = await agentic.ensemble(params=TurnParams(**params_payload), **call_kwargs)
    elapsed = time.perf_counter() - started
    cap = _capture_from_outcome(outcome, prompt=prompt, system=system)
    _record_outputs(cap, elapsed)
    return dc_replace(cap, capture_errors=tuple(capture_errors))


# ── unit orchestration ──────────────────────────────────────────────────────


def default_prompt_builder(unit: Any, scenario: Any) -> str:
    """Deterministic smoke prompt for one unit.

    Scenarios that carry rich prompt content (industry pack: real BFCL/τ-bench
    tasks) are used verbatim — these prompts exist to measure scenario quality.
    Otherwise the generic smoke prompt validates the live ROUTE (dispatcher ->
    DeepSeek -> capture -> ledger), with a task line derived deterministically from
    (scenario id, seed) so reruns are stable.
    """
    rich = str(getattr(scenario, "prompt", "") or "")
    if rich:
        return rich
    digest = hashlib.sha256(f"{scenario.id}|{unit.seed}".encode()).hexdigest()[:8]
    return (
        "[pi-benchmark smoke prompt — route validation, not the full scenario corpus]\n"
        f"Scenario {scenario.id} ({scenario.title}), seed {unit.seed}.\n"
        f"Task {digest}: in three sentences, describe how you would approach this "
        "scenario and name the first risk you would check."
    )


def _model_calls(unit: Any, moa_n: int) -> int:
    """Model calls one unit makes: 1 plain, moa_n self_moa samples, slots ensemble routes."""
    moa_mode = getattr(unit, "moa_mode", None)
    if moa_mode in moa.MOA_MODES:
        return moa.requested_slots(moa_mode, moa_n)
    return 1


def _is_budget_exceeded(exc: BaseException) -> bool:
    # Name-based fallback keeps the two lanes decoupled: a Lane A BudgetExceeded raised
    # through a sys.modules-injected fake is still recognised before the modules merge.
    return isinstance(exc, BudgetExceeded) or type(exc).__name__ == "BudgetExceeded"


def _is_ledger_state_error(exc: BaseException) -> bool:
    # Same name-based fallback as _is_budget_exceeded: recognise Lane A's LedgerStateError
    # even when it is raised through a sys.modules-injected fake ledger.
    return isinstance(exc, LedgerStateError) or type(exc).__name__ == "LedgerStateError"


def _moa_evidence_from_capture(*, moa_mode: str, moa_n: int, capture: LiveCapture) -> moa.MoaEvidence:
    """Assess a MoA unit from its LiveCapture via a ValidationResult-shaped shim.

    The dispatcher’s route evidence carries one entry per successful response, while the
    endpoint list may also contain failed samples.  Consensus evidence is copied through
    the capture boundary so the resulting record retains the backend's score/confidence.
    """
    shim = types.SimpleNamespace(
        method=capture.raw_method or "",
        responses=list(capture.route_evidence),
        consensus=types.SimpleNamespace(
            agreement_score=capture.consensus_score,
            confidence=capture.consensus_confidence,
        ),
        metadata={
            "endpoint_ids": list(capture.endpoint_ids),
            "route_evidence": [dict(r) for r in capture.route_evidence],
        },
    )
    temperatures = moa.self_moa_temperatures(moa_n) if moa_mode == "self_moa" else ()
    return moa.assess_validation_result(
        requested_mode=moa_mode,
        requested_samples=moa.requested_slots(moa_mode, moa_n),
        temperatures=temperatures,
        result=shim,
    )


def _build_unit_record(
    *,
    unit: Any, scenario: Any, config: Any, status: str,
    not_runnable_reason: str | None = None, usage: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble + validate one record via the shared schema helpers."""

    # The unit's own phase (from the manifest) is the identity — a wave's CLI --phase
    # is only a default and must not rewrite a unit's record identity.
    unit_config = config
    unit_phase = str(getattr(unit, "phase", "") or "")
    if unit_phase and unit_phase != getattr(config, "phase", None):
        unit_config = dc_replace(config, phase=unit_phase)
    record = schema.build_record(
        config=unit_config,
        scenario=scenario,
        engine=unit.engine,
        seed=unit.seed,
        repeat=unit.repeat,
        # Deterministic per-unit order assignment (stable across resume/waves).
        pair_index=int(hashlib.sha256(unit.unit_id.encode()).hexdigest()[:8], 16),
        git_sha=schema.git_provenance()[0],
        git_dirty=schema.git_provenance()[1],
        ts=schema._utc_now_iso(),
        status=status,
        not_runnable_reason=not_runnable_reason,
        metrics=None,  # live quality metrics need judge/probe scoring — never fabricated
        usage=usage,
        extensions=extensions,
    )
    if record["record_id"] != unit.unit_id:
        # MoA units append the mode to the unit id; the durable identity (file name,
        # ledger call id, resume key) is the manifest's unit_id, so the record adopts
        # it verbatim. pair_id (engine/moa-free) stays as computed.
        record["record_id"] = unit.unit_id
    return record


def _stamp_live_provenance(
    record: dict[str, Any], provider: Any, capture: LiveCapture | None = None,
) -> dict[str, Any]:
    """Stamp only the route actually returned by the dispatcher.

    The injected budget provider is a pricing/accounting dependency, not proof of the
    dispatcher route. A fingerprint is therefore derived from redacted route evidence;
    blocked-before-dispatch records carry null live identity instead of a guessed one.
    """
    route_evidence = tuple(capture.route_evidence) if capture is not None else ()
    if route_evidence:
        import tests.pi_benchmark.registry_seed as registry_seed

        approved_all = APPROVED_DEEPSEEK_ENDPOINT_IDS | {registry_seed.BENCHMARK_NODE_ID}
        normalized_routes = []
        for route in route_evidence:
            normalized = dict(route)
            endpoint_id = str(normalized.get("endpoint_id") or "")
            if endpoint_id in approved_all:
                normalized.setdefault("provider", DEEPSEEK_PROVIDER)
                normalized.setdefault("model", DEEPSEEK_MODEL)
            elif endpoint_id.startswith("pi-petals-"):
                # Petals slots are donated compute, NOT DeepSeek — never stamp the
                # DeepSeek identity on them (CF-338 route truth).
                normalized.setdefault("provider", "petals")
            normalized_routes.append(normalized)
        safe_routes = [
            {
                key: str(route[key])
                for key in ("endpoint_id", "provider", "model", "engine", "route_kind")
                if route.get(key)
            }
            for route in normalized_routes
        ]
        encoded = json.dumps(safe_routes, sort_keys=True, separators=(",", ":"))
        providers = {route.get("provider") for route in normalized_routes if route.get("provider")}
        label = "deepseek-route" if providers <= {DEEPSEEK_PROVIDER} else "mixed-route"
        record["provenance"]["endpoint_fingerprint"] = (
            f"{label}:{hashlib.sha256(encoded.encode()).hexdigest()[:12]}"
        )
        models = {route.get("model") for route in normalized_routes if route.get("model")}
        record["provenance"]["model_id"] = models.pop() if len(models) == 1 else None
    else:
        record["provenance"]["model_id"] = None
        record["provenance"]["endpoint_fingerprint"] = None
    schema.validate_record(record)  # re-validate after the provenance override
    return record


async def run_live_unit(
    *,
    unit: Any,
    scenario: Any,
    config: Any,
    ledger: Any,
    provider: Any,
    records_dir: Path,
    dispatch: Any = dispatch_unit,
    prompt_builder: Any = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    moa_n: int = 3,
    wave: int | None = None,
) -> dict[str, Any]:
    """Execute one unit end-to-end (reserve -> dispatch -> commit -> record) and return
    its schema-valid record. Every outcome — ok or blocked — produces a record; nothing
    is silently dropped and no exception for an expected failure mode escapes.
    """
    records_dir = Path(records_dir)
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")
    final_path = records_dir / f"{unit.unit_id}.json"
    if final_path.is_file():
        try:  # crash-safe resume: a complete record means this unit is already done
            existing = json.loads(final_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and existing.get("status"):
                return existing
        except (OSError, json.JSONDecodeError):
            pass  # corrupt file: re-run and overwrite atomically

    build_prompt = prompt_builder or default_prompt_builder
    prompt = build_prompt(unit, scenario)
    system = ""
    moa_mode = getattr(unit, "moa_mode", None)
    extensions: dict[str, Any] = {"unit_id": unit.unit_id}
    if wave is not None:
        extensions["wave"] = {"index": wave}

    # 1-2. Worst-case reservation BEFORE any dispatch. Reserve a margin of input-priced
    # tokens (2x the chars4 estimate, floored at MIN_RESERVE_INPUT_TOKENS) plus the full
    # max_tokens output bound, per model call. See the module header: under-reserving would
    # let a real call's actual cost exceed its reservation, which the ledger refuses at
    # commit — crashing (and, without the guards below, permanently wedging) the wave.
    prompt_tokens = _chars4(system + prompt)
    reserve_input_tokens = max(2 * prompt_tokens, MIN_RESERVE_INPUT_TOKENS)
    worst_case = provider.estimate_cost(
        input_tokens=reserve_input_tokens, output_tokens=max_tokens
    ) * _model_calls(unit, moa_n)
    try:
        ledger.reserve(
            unit.unit_id, worst_case, kind="benchmark",
            meta={"tier": config.tier, "phase": config.phase, "moa_mode": moa_mode},
        )
    except Exception as exc:
        if _is_budget_exceeded(exc):
            extensions["detail"] = {"reason": f"reservation refused: {exc}"}
            if moa_mode in moa.MOA_MODES:
                extensions["moa"] = asdict(moa.not_run_evidence(
                    requested_mode=moa_mode,
                    requested_samples=moa.requested_slots(moa_mode, moa_n),
                    temperatures=moa.self_moa_temperatures(moa_n) if moa_mode == "self_moa" else (),
                ))
            record = _build_unit_record(
                unit=unit, scenario=scenario, config=config, status="not_runnable",
                not_runnable_reason="budget_exceeded", extensions=extensions,
            )
            schema.write_record_atomic(records_dir, unit.unit_id, _stamp_live_provenance(record, provider))
            return record
        if _is_ledger_state_error(exc):
            # Resume after a crash that reserved this unit but never wrote its record: the
            # reservation is already outstanding and cannot be re-booked. Retain it as
            # worst-case spend and record the interruption. Re-raising here (the old
            # behaviour) would permanently wedge the wave — every resume would hit the same
            # outstanding reservation and crash again.
            extensions["detail"] = "interrupted_unknown_usage"
            if moa_mode in moa.MOA_MODES:
                extensions["moa"] = asdict(moa.not_run_evidence(
                    requested_mode=moa_mode,
                    requested_samples=moa.requested_slots(moa_mode, moa_n),
                    temperatures=moa.self_moa_temperatures(moa_n) if moa_mode == "self_moa" else (),
                ))
            record = _build_unit_record(
                unit=unit, scenario=scenario, config=config, status="not_runnable",
                not_runnable_reason="other", extensions=extensions,
            )
            schema.write_record_atomic(records_dir, unit.unit_id, _stamp_live_provenance(record, provider))
            return record
        raise  # config/programming failure (e.g. LedgerClosed): stop the wave loudly

    # 3. Dispatch; map failures onto typed not_runnable records.
    try:
        dispatch_kwargs = dict(
            unit=unit, tier=config.tier, prompt=prompt, system=system,
            moa_n=moa_n, max_tokens=max_tokens,
        )
        # The default benchmark dispatcher uses the provider opened by the runner.
        # Custom test/integration dispatchers retain their existing narrow contract.
        if dispatch is dispatch_unit:
            dispatch_kwargs["provider"] = provider
            import tests.pi_benchmark.raw_capture as raw_capture

            dispatch_kwargs["capture"] = raw_capture.RawCaptureWriter(
                records_dir.parent / "raw-llm-calls"
            )
        capture = await dispatch(**dispatch_kwargs)
        if getattr(capture, "capture_errors", None):
            extensions.setdefault("detail", {})
            if isinstance(extensions["detail"], dict):
                extensions["detail"]["capture_errors"] = list(capture.capture_errors)
    except PreDispatchError as exc:
        ledger.release(unit.unit_id, reason=f"pre_dispatch:{exc}")
        extensions["detail"] = {"reason": f"pre-dispatch failure: {exc}"}
        record = _build_unit_record(
            unit=unit, scenario=scenario, config=config, status="not_runnable",
            not_runnable_reason="startup_failure", extensions=extensions,
        )
        schema.write_record_atomic(records_dir, unit.unit_id, _stamp_live_provenance(record, provider))
        return record
    except (TimeoutError, asyncio.TimeoutError) as exc:
        # Retain the reservation: the request may still be in flight and billable.
        extensions["detail"] = {"reason": f"dispatch timeout (reservation retained): {exc}"}
        record = _build_unit_record(
            unit=unit, scenario=scenario, config=config, status="not_runnable",
            not_runnable_reason="timeout", extensions=extensions,
        )
        schema.write_record_atomic(records_dir, unit.unit_id, _stamp_live_provenance(record, provider))
        return record
    except Exception as exc:
        if isinstance(exc, RouteAdmissionError):
            extensions["detail"] = {"reason": "route_admission_failed"}
            if exc.route:
                extensions["route_evidence"] = [
                    {key: str(value) for key, value in exc.route.items() if value is not None}
                ]
        else:
            extensions["detail"] = {"reason": f"dispatch failure (reservation retained): {exc}"}
        record = _build_unit_record(
            unit=unit, scenario=scenario, config=config, status="not_runnable",
            not_runnable_reason="startup_failure", extensions=extensions,
        )
        schema.write_record_atomic(records_dir, unit.unit_id, _stamp_live_provenance(record, provider))
        return record

    # 4. Successful-looking dispatch with neither usage nor text: fail closed.
    if capture.usage is None:
        extensions["detail"] = "unknown_usage_fail_closed"
        if capture.route_evidence:
            extensions["route_evidence"] = [dict(route) for route in capture.route_evidence]
        record = _build_unit_record(
            unit=unit, scenario=scenario, config=config, status="not_runnable",
            not_runnable_reason="other", extensions=extensions,
        )
        schema.write_record_atomic(
            records_dir, unit.unit_id, _stamp_live_provenance(record, provider, capture)
        )
        return record

    # 5. Commit actual cost from provider pricing over the captured tokens.
    if capture.route_evidence:
        extensions["route_evidence"] = [dict(route) for route in capture.route_evidence]
    usage = capture.usage
    actual_cost = round(provider.estimate_cost(
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cache_read_tokens=usage.get("cache_read_tokens", 0),
        cache_write_tokens=usage.get("cache_write_tokens", 0),
    ), 7)
    try:
        ledger.commit(unit.unit_id, actual_cost, usage=dict(usage), meta={"estimate": capture.estimate})
    except Exception as exc:
        if not _is_ledger_state_error(exc):
            raise  # config/programming failure (e.g. LedgerClosed): stop the wave loudly
        # Actual cost exceeded the worst-case reservation (or the reservation lifecycle is
        # otherwise inconsistent). Fail closed: the commit appended nothing, so the
        # reservation stays booked as worst-case spend; record the accounting failure and
        # return. Never crash the wave here — a crash would leave no record and wedge resume.
        extensions["detail"] = "accounting_fail_closed"
        record = _build_unit_record(
            unit=unit, scenario=scenario, config=config, status="not_runnable",
            not_runnable_reason="other", extensions=extensions,
        )
        schema.write_record_atomic(
            records_dir, unit.unit_id, _stamp_live_provenance(record, provider, capture)
        )
        return record

    # 6. Build the ok / moa-degraded record.
    moa_mode = getattr(unit, "moa_mode", None)
    status, reason = "ok", None
    if moa_mode in moa.MOA_MODES:
        evidence = _moa_evidence_from_capture(moa_mode=moa_mode, moa_n=moa_n, capture=capture)
        extensions["moa"] = asdict(evidence)
        status, reason = moa.record_status_for(evidence)
        if status != "ok":
            extensions["detail"] = "moa_downgrade_fail_closed"
    extensions.setdefault("detail", "live capture through the Istara dispatcher (deepseek-v4-pro)")
    usage_block = {
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cache_tokens": usage.get("cache_read_tokens", 0) + usage.get("cache_write_tokens", 0),
        "total_tokens": usage["total_tokens"],
        "cost_usd": actual_cost,
        "estimate": capture.estimate,
        "estimator": ESTIMATOR_CHARS4 if capture.estimate else None,
    }
    record = _build_unit_record(
        unit=unit, scenario=scenario, config=config, status=status,
        not_runnable_reason=reason, usage=usage_block, extensions=extensions,
    )
    schema.write_record_atomic(
        records_dir, unit.unit_id, _stamp_live_provenance(record, provider, capture)
    )
    return record


def run_live_unit_sync(**kwargs: Any) -> dict[str, Any]:
    """Sync wrapper around :func:`run_live_unit` for the (sync) runner."""
    return asyncio.run(run_live_unit(**kwargs))
