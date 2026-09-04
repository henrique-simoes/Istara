"""Governed qualitative coding-run orchestration (compatibility facade).

Implementation lives in cohesive sibling modules; every public and private
name is re-exported so existing product imports and test seams keep working
unchanged.
"""

from __future__ import annotations

import logging

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_router import llm_router
from app.core.research_validity import (
    DEFAULT_RELIABILITY_THRESHOLD,
    QUALITATIVE_CODING_PROTOCOL,
    build_qualitative_coding_prompt,
    evaluate_reliability_gate,
    graph_edge_metadata,
    item_level_promotion_statuses,
)
from app.core.telemetry import telemetry_recorder
from app.models.code_application import CodeApplication
from app.models.research_validity import (
    CodingRun,
    CodingRunCoder,
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)

# Compatibility re-exports (import seam preserved for product code and tests).
from app.services.research_validity_evidence_units import _chat_model_names  # noqa: F401
from app.services.research_validity_evidence_units import _coding_messages  # noqa: F401
from app.services.research_validity_evidence_units import _coding_repair_messages  # noqa: F401
from app.services.research_validity_evidence_units import _coding_unit_payload  # noqa: F401
from app.services.research_validity_evidence_units import _compact_source_text_for_coding  # noqa: F401
from app.services.research_validity_evidence_units import _is_qa_provisional_unit  # noqa: F401
from app.services.research_validity_evidence_units import _load_codebook  # noqa: F401
from app.services.research_validity_evidence_units import _load_units  # noqa: F401
from app.services.research_validity_evidence_units import _node_model_names  # noqa: F401
from app.services.research_validity_evidence_units import document_research_spine_summary  # noqa: F401
from app.services.research_validity_evidence_units import document_source_id  # noqa: F401
from app.services.research_validity_evidence_units import document_source_unit_count_map  # noqa: F401
from app.services.research_validity_evidence_units import persist_document_source_evidence_units  # noqa: F401
from app.services.research_validity_evidence_units import persist_task_nugget_evidence_units  # noqa: F401
from app.services.research_validity_evidence_units import record_source_evidence_unit_telemetry  # noqa: F401
from app.services.research_validity_reconciliation import _code_application_state  # noqa: F401
from app.services.research_validity_reconciliation import _is_reconciled_code_application  # noqa: F401
from app.services.research_validity_reconciliation import _is_unresolved_code_application  # noqa: F401
from app.services.research_validity_reconciliation import _load_traceability_findings  # noqa: F401
from app.services.research_validity_reconciliation import _refresh_coding_run_reconciliation_status  # noqa: F401
from app.services.research_validity_reconciliation import _task_finding_support_diagnostics  # noqa: F401
from app.services.research_validity_reconciliation import add_agent_initial_code_applications  # noqa: F401
from app.services.research_validity_reconciliation import assess_task_research_validity  # noqa: F401
from app.services.research_validity_reconciliation import build_evidence_graph_traceability  # noqa: F401
from app.services.research_validity_reconciliation import create_reconciliation_decision  # noqa: F401
from app.services.research_validity_reconciliation import mark_task_provisional_skill_artifacts  # noqa: F401
from app.services.research_validity_reconciliation import task_validation_payload_with_coding_run  # noqa: F401
from app.services.research_validity_route_evidence import _fallback_coder  # noqa: F401
from app.services.research_validity_route_evidence import _is_dashscope_endpoint  # noqa: F401
from app.services.research_validity_route_evidence import _is_qwen_rate_limit_error  # noqa: F401
from app.services.research_validity_route_evidence import _merge_coding_route_evidence  # noqa: F401
from app.services.research_validity_route_evidence import _pi_coder_runner  # noqa: F401
from app.services.research_validity_route_evidence import _pi_endpoint_identity  # noqa: F401
from app.services.research_validity_route_evidence import _run_pi_coder_with_qwen_fallback  # noqa: F401
from app.services.research_validity_route_evidence import _same_dashscope_key  # noqa: F401
from app.services.research_validity_schemas import ACCEPTED_PROMOTION_STATUSES  # noqa: F401
from app.services.research_validity_schemas import CODING_CORE_RESPONSE_SCHEMA  # noqa: F401
from app.services.research_validity_schemas import CODING_RESPONSE_SCHEMA  # noqa: F401
from app.services.research_validity_schemas import CoderRunner  # noqa: F401
from app.services.research_validity_schemas import CoderSpec  # noqa: F401
from app.services.research_validity_schemas import DASHSCOPE_COMPAT_BASE_URL  # noqa: F401
from app.services.research_validity_schemas import MAX_CODING_SOURCE_TEXT_CHARS  # noqa: F401
from app.services.research_validity_schemas import QWEN_FALLBACK_ONLY_MODELS  # noqa: F401
from app.services.research_validity_schemas import QWEN_RATE_LIMIT_FALLBACK_CHAINS  # noqa: F401
from app.services.research_validity_schemas import QwenRateLimitFallbackError  # noqa: F401
from app.services.research_validity_schemas import RECONCILED_CODE_APPLICATION_STATUSES  # noqa: F401
from app.services.research_validity_schemas import _application_items  # noqa: F401
from app.services.research_validity_schemas import _code_list  # noqa: F401
from app.services.research_validity_schemas import _confidence  # noqa: F401
from app.services.research_validity_schemas import _extract_json_payload  # noqa: F401
from app.services.research_validity_schemas import _json_list_value  # noqa: F401


logger = logging.getLogger(__name__)


def _select_project_coders(project_id: str, max_coders: int) -> list[CoderSpec]:
    coders: list[CoderSpec] = []
    seen_models: set[str] = set()
    seen_nodes: set[str] = set()
    nodes = [
        node
        for node in llm_router._sorted_servers(project_id=project_id)
        if getattr(node, "is_healthy", False)
    ]

    def add_coder(node: Any, model_name: str) -> bool:
        node_id = str(getattr(node, "node_id", "") or getattr(node, "name", "")).strip()
        model_identity = str(model_name or node_id).strip()
        normalized_identity = model_identity.casefold()
        if not model_identity or normalized_identity in seen_models:
            return False
        seen_models.add(normalized_identity)
        seen_nodes.add(node_id)
        coders.append(
            CoderSpec(
                node=node,
                coder_id=f"model-coder:{model_identity}",
                model_name=model_name,
            )
        )
        return len(coders) >= max(1, max_coders)

    # First pass: one primary chat model per healthy project-authorized donor.
    # This preserves the multi-model/donor contract instead of letting one
    # LM Studio server's advertised model list consume every coder slot.
    for node in nodes:
        model_names = _node_model_names(node)
        primary = model_names[0] if model_names else ""
        if add_coder(node, primary):
            return coders

    # Second pass: only after distinct donor routes are represented, use extra
    # distinct models from those same nodes if policy asks for more coders.
    for node in nodes:
        node_id = str(getattr(node, "node_id", "") or getattr(node, "name", "")).strip()
        if node_id not in seen_nodes:
            continue
        for model_name in (_node_model_names(node) or [""])[1:]:
            if add_coder(node, model_name):
                return coders
    return coders


def _resolve_application_unit(
    raw_app: dict,
    *,
    unit_by_id: dict[str, EvidenceUnit],
    units: list[EvidenceUnit],
) -> EvidenceUnit | None:
    """Resolve model output to the prompted evidence unit without trusting prose alone."""
    stable_by_id = {
        str(getattr(unit, "stable_id", "") or "").strip(): unit
        for unit in units
        if str(getattr(unit, "stable_id", "") or "").strip()
    }
    unique_unit_indexes: dict[int, EvidenceUnit | None] = {}
    for unit in units:
        unit_index = getattr(unit, "unit_index", None)
        if unit_index is None:
            continue
        try:
            index_key = int(unit_index)
        except (TypeError, ValueError):
            continue
        if index_key in unique_unit_indexes:
            unique_unit_indexes[index_key] = None
        else:
            unique_unit_indexes[index_key] = unit

    for key in (
        "evidence_unit_id",
        "unit_id",
        "id",
        "evidence_unit_stable_id",
        "stable_id",
    ):
        value = str(raw_app.get(key) or "").strip()
        if not value:
            continue
        if value in unit_by_id:
            return unit_by_id[value]
        if value in stable_by_id:
            return stable_by_id[value]
        for stable_id, unit in stable_by_id.items():
            if stable_id and (value.endswith(stable_id) or stable_id.endswith(value)):
                return unit

    for key in ("unit_index", "evidence_unit_index", "index"):
        value = raw_app.get(key)
        if value in (None, ""):
            continue
        try:
            index_key = int(value)
        except (TypeError, ValueError):
            continue
        resolved = unique_unit_indexes.get(index_key)
        if resolved is not None:
            return resolved

    quote = str(raw_app.get("quote") or raw_app.get("source_quote") or "").strip()
    if len(quote) >= 16:
        matches = [
            unit
            for unit in units
            if quote in (unit.source_text or "")
            or (unit.source_text and len(unit.source_text) >= 16 and unit.source_text in quote)
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _usable_coding_applications(
    parsed: dict,
    *,
    unit_by_id: dict[str, EvidenceUnit],
    units: list[EvidenceUnit],
) -> list[tuple[dict, EvidenceUnit, list[str]]]:
    usable: list[tuple[dict, EvidenceUnit, list[str]]] = []
    for raw_app in _application_items(parsed):
        unit = _resolve_application_unit(
            raw_app,
            unit_by_id=unit_by_id,
            units=units,
        )
        if not unit:
            continue
        quote = str(raw_app.get("quote") or raw_app.get("source_quote") or "").strip()
        if not quote or quote not in str(unit.source_text or ""):
            continue
        codes = _code_list(raw_app)
        if not codes:
            continue
        usable.append((raw_app, unit, codes))
    return usable


def _has_complete_unit_coverage(
    usable: list[tuple[dict, EvidenceUnit, list[str]]],
    *,
    unit_by_id: dict[str, EvidenceUnit],
) -> bool:
    """Return whether one coder supplied a usable result for every requested unit."""
    covered = {unit.id for _, unit, _ in usable}
    return covered == set(unit_by_id)


def _merge_coverage_applications(
    original: list[tuple[dict, EvidenceUnit, list[str]]],
    repair: list[tuple[dict, EvidenceUnit, list[str]]],
) -> list[tuple[dict, EvidenceUnit, list[str]]]:
    """Union one coder's usable applications across its bounded coverage repair.

    Both attempts come from the same pinned coder identity under the same
    protocol, so the per-unit union is still a single rater's coding; the
    repair attempt wins per unit it covered. Replacing instead of merging
    would discard units the first attempt had already grounded.
    """
    merged = list(repair)
    covered = {unit.id for _, unit, _ in repair}
    for app, unit, codes in original:
        if unit.id not in covered:
            merged.append((app, unit, codes))
            covered.add(unit.id)
    return merged


async def _use_pi_coding_plane(db: AsyncSession, project_id: str) -> bool:
    """Research coding always uses the Pi model-management authority.

    The project's agentic-engine choice controls loop semantics, not provider
    discovery or independent-coder identity.  Keeping this compatibility seam
    makes the invariant explicit while older tests/extensions still patch it.
    """
    del db, project_id
    return True


async def _select_pi_coders(
    max_coders: int,
    *,
    project_id: str | None = None,
    manager: Any | None = None,
    pi_service: Any | None = None,
) -> list[CoderSpec]:
    """Select independent coders backed by distinct Pi-managed models.

    Exact endpoint identities remain pinned as route evidence, while
    ``resolve_distinct`` fails closed when the catalog has fewer distinct model
    identities than requested. Endpoint replicas never fabricate diversity.
    """
    from types import SimpleNamespace

    if pi_service is not None:
        service_manager_accessor = getattr(pi_service, "model_manager", None)
        if not callable(service_manager_accessor):
            raise ValueError("Pi execution service has no paired model manager")
        service_manager = service_manager_accessor()
        if manager is None:
            manager = service_manager
        elif service_manager is not manager:
            raise ValueError("Pi execution service is not paired with selected model manager")
    if manager is None:
        from app.core.pi_runtime.model_manager import PiModelManager

        manager = PiModelManager()
    # Read-only DB projection of persisted LLMServer endpoint identities;
    # it never connects to a server or loads a model.
    await manager.ensure_db_projection()
    requested_count = max(1, max_coders)
    preferred_ids = [
        str(endpoint_id).strip()
        for endpoint_id in getattr(settings, "pi_research_endpoint_ids", [])
        if str(endpoint_id).strip()
    ]
    endpoints = []
    seen_models: set[str] = set()
    attempted_ids: list[str] = []
    if preferred_ids:
        from app.core.pi_runtime.endpoints import PiEndpointResolutionError

        excluded_models = {str(model).strip().casefold() for model in QWEN_FALLBACK_ONLY_MODELS}
        for endpoint_id in preferred_ids:
            if len(endpoints) >= requested_count:
                break
            attempted_ids.append(endpoint_id)
            try:
                endpoint = manager.resolve(
                    endpoint_id=endpoint_id,
                    model=None,
                    project_id=project_id,
                )
            except PiEndpointResolutionError as exc:
                logger.warning(
                    "Preferred Research Spine endpoint %s unavailable; using healthy catalog fallback: %s",
                    endpoint_id,
                    exc,
                )
                continue
            model_identity = str(endpoint.model or "").strip().casefold()
            if (
                not model_identity
                or model_identity in excluded_models
                or model_identity in seen_models
            ):
                continue
            seen_models.add(model_identity)
            endpoints.append(endpoint)

        remaining = requested_count - len(endpoints)
        if remaining:
            endpoints.extend(
                manager.resolve_distinct(
                    remaining,
                    project_id=project_id,
                    exclude=tuple(attempted_ids),
                    exclude_models=tuple(QWEN_FALLBACK_ONLY_MODELS) + tuple(seen_models),
                )
            )
    else:
        # No user preference: preserve healthy donor/catalog selection exactly.
        endpoints = manager.resolve_distinct(
            requested_count,
            project_id=project_id,
            exclude_models=QWEN_FALLBACK_ONLY_MODELS,
        )
    return [
        CoderSpec(
            node=SimpleNamespace(
                node_id=endpoint.endpoint_id,
                name=endpoint.endpoint_id,
                source="pi",
                provider_type=endpoint.provider_kind,
                endpoint_id=endpoint.endpoint_id,
                provider_account_handle=getattr(endpoint, "provider_account_handle", ""),
            ),
            coder_id=f"model-coder:{endpoint.endpoint_id}",
            model_name=endpoint.model,
            pi_manager=manager,
            pi_service=pi_service,
            pi_endpoint_identity=_pi_endpoint_identity(endpoint),
        )
        for endpoint in endpoints
    ]


async def run_independent_coding_run(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str | None = None,
    evidence_unit_ids: list[str] | None = None,
    codebook_version_id: str | None = None,
    threshold: float = DEFAULT_RELIABILITY_THRESHOLD,
    max_coders: int = 3,
    limit: int = 50,
    created_by: str = "",
    coder_runner: CoderRunner | None = None,
) -> dict:
    """Run project-authorized independent model coders and persist reliability state."""
    units = await _load_units(
        db,
        project_id=project_id,
        task_id=task_id,
        evidence_unit_ids=evidence_unit_ids,
        limit=limit,
    )
    codebook = await _load_codebook(
        db, project_id=project_id, codebook_version_id=codebook_version_id
    )
    run_id = str(uuid.uuid4())
    trace_id = uuid.uuid4().hex[:36]
    coding_run = CodingRun(
        id=run_id,
        project_id=project_id,
        task_id=task_id,
        codebook_version_id=codebook.id if codebook else codebook_version_id,
        status="running" if units else "blocked",
        threshold=threshold,
        created_by=created_by,
    )
    db.add(coding_run)
    await db.commit()
    await db.refresh(coding_run)
    await telemetry_recorder.record_research_validity_event(
        trace_id=trace_id,
        operation="coding_run.start",
        project_id=project_id,
        coding_run_id=run_id,
        codebook_version_id=coding_run.codebook_version_id or "",
    )

    if not units:
        coding_run.status = "blocked"
        coding_run.promotion_status = "blocked"
        coding_run.fallback_reason = "No evidence units are available for coding."
        coding_run.completed_at = datetime.now(UTC)
        await db.commit()
        return coding_run.to_dict()

    # Fail-closed provisional boundary: synthetic-QA evidence units may never
    # be promoted to accepted/reportable states, regardless of reliability
    # scores. Block the whole run rather than silently skipping units.
    provisional_unit_ids = [unit.id for unit in units if _is_qa_provisional_unit(unit)]
    if provisional_unit_ids:
        coding_run.status = "blocked"
        coding_run.promotion_status = "blocked"
        coding_run.fallback_reason = (
            "Synthetic QA evidence units are provisional-only and can never be "
            f"promoted (blocked unit count: {len(provisional_unit_ids)})."
        )
        coding_run.completed_at = datetime.now(UTC)
        await db.commit()
        return coding_run.to_dict()

    runner = coder_runner or _pi_coder_runner
    use_pi_qwen_fallback = False
    pi_selection_error: str | None = None
    if coder_runner is None and await _use_pi_coding_plane(db, project_id):
        # Coders are distinct Pi-managed model identities, each pinned to its
        # exact endpoint and coded through the
        # AgenticDispatcher structured verb (``validity.coder``).
        try:
            # The default runner dispatches through the process-wide
            # AgenticDispatcher singleton. Reuse its engine-owned manager for
            # selection so endpoint/model identity cannot drift between
            # selection and the structured call. Test doubles may not expose
            # this accessor; retain the direct selector seam for those tests.
            from app.core.agentic import agentic

            service_accessor = getattr(agentic, "pi_execution_service", None)
            manager_accessor = getattr(agentic, "model_manager", None)
            if callable(service_accessor):
                pi_service = service_accessor()
                manager = pi_service.model_manager()
                coders = await _select_pi_coders(
                    max_coders=max_coders,
                    project_id=project_id,
                    manager=manager,
                    pi_service=pi_service,
                )
            elif callable(manager_accessor):
                coders = await _select_pi_coders(
                    max_coders=max_coders,
                    project_id=project_id,
                    manager=manager_accessor(),
                )
            else:
                coders = await _select_pi_coders(max_coders=max_coders, project_id=project_id)
            use_pi_qwen_fallback = True
        except Exception as exc:
            # Fail-closed: fewer distinct Pi models than requested coders (or
            # an unavailable catalog) means
            # validation unavailable — never fabricate diversity from fewer
            # endpoints and never switch engines silently. The empty coder
            # set flows into the existing reliability-gate "blocked"
            # handling below.
            logger.warning("Dual-coder Pi selection failed closed: %s", exc)
            coders = []
            pi_selection_error = str(exc)
    else:
        coders = _select_project_coders(project_id, max_coders=max_coders)
    messages = _coding_messages(units, codebook, threshold)
    prompt_hash = sha256(
        json.dumps(messages, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    unit_by_id = {unit.id: unit for unit in units}
    gate_applications: list[dict] = []
    persisted_count = 0
    route_evidence: list[dict] = []
    if pi_selection_error:
        route_evidence.append(
            {
                "coder_id": "",
                "model": "",
                "outcome": "failed",
                "error": pi_selection_error[:160],
            }
        )

    for coder in coders:
        donor_id = getattr(coder.node, "node_id", "") or getattr(coder.node, "name", "")
        await telemetry_recorder.record_research_validity_event(
            trace_id=trace_id,
            operation="coding_run.model_selected",
            project_id=project_id,
            status="success",
            model_name=coder.model_name,
            donor_id=donor_id,
            route_id=donor_id,
            coding_run_id=run_id,
            codebook_version_id=coding_run.codebook_version_id or "",
        )
        active_coder = coder
        try:
            if use_pi_qwen_fallback:
                response, active_coder = await _run_pi_coder_with_qwen_fallback(
                    coder,
                    messages,
                    coder.model_name or None,
                    project_id,
                    runner=runner,
                )
            else:
                response = await runner(coder, messages, coder.model_name or None, project_id)
            content = response.get("message", {}).get("content", "")
            parsed = _extract_json_payload(content)
            usable_applications = _usable_coding_applications(
                parsed,
                unit_by_id=unit_by_id,
                units=units,
            )
            coverage_repair_attempts = 0
            while (
                not _has_complete_unit_coverage(usable_applications, unit_by_id=unit_by_id)
                and coverage_repair_attempts < 2
            ):
                coverage_repair_attempts += 1
                repair_messages = _coding_repair_messages(units, codebook, threshold)
                if use_pi_qwen_fallback:
                    repair_response, repaired_coder = await _run_pi_coder_with_qwen_fallback(
                        active_coder,
                        repair_messages,
                        active_coder.model_name or None,
                        project_id,
                        runner=runner,
                    )
                    active_coder = repaired_coder
                else:
                    repair_response = await runner(
                        active_coder,
                        repair_messages,
                        active_coder.model_name or None,
                        project_id,
                    )
                repair_content = repair_response.get("message", {}).get("content", "")
                repair_parsed = _extract_json_payload(repair_content)
                repair_usable = _usable_coding_applications(
                    repair_parsed,
                    unit_by_id=unit_by_id,
                    units=units,
                )
                if repair_usable:
                    response = _merge_coding_route_evidence(response, repair_response)
                    merged_route = dict(response.get("_istara_route", {}) or {})
                    merged_route["coverage_repair"] = "per_unit_union"
                    merged_route["coverage_repair_attempts"] = coverage_repair_attempts
                    response = {**response, "_istara_route": merged_route}
                    parsed = repair_parsed
                    usable_applications = _merge_coverage_applications(
                        usable_applications, repair_usable
                    )
            if not _has_complete_unit_coverage(usable_applications, unit_by_id=unit_by_id):
                raise ValueError(
                    "coder response lacked complete evidence-unit coverage "
                    f"({len({unit.id for _, unit, _ in usable_applications})}/"
                    f"{len(unit_by_id)})"
                )
        except Exception as exc:
            failure_route = {
                "coder_id": coder.coder_id,
                "model": coder.model_name,
                "outcome": "failed",
                "error": str(exc)[:160],
            }
            if isinstance(exc, QwenRateLimitFallbackError):
                failure_route["fallback_reason"] = "rate_limit"
                failure_route["fallback_attempts"] = exc.attempts
            route_evidence.append(failure_route)
            await telemetry_recorder.record_research_validity_event(
                trace_id=trace_id,
                operation="donor.failed",
                project_id=project_id,
                status="error",
                model_name=coder.model_name,
                donor_id=donor_id,
                route_id=donor_id,
                coding_run_id=run_id,
                codebook_version_id=coding_run.codebook_version_id or "",
                error_type="coding_runner_failed",
                error_message=str(exc)[:160],
            )
            continue

        route = response.get("_istara_route", {}) if isinstance(response, dict) else {}
        if not route:
            route = {
                "node_id": getattr(coder.node, "node_id", "") or getattr(coder.node, "name", ""),
                "node_source": getattr(coder.node, "source", ""),
                "provider_type": getattr(coder.node, "provider_type", ""),
                "model": coder.model_name,
                "route_kind": "coding_run",
                "outcome": "served",
            }
        route_evidence.append(route)
        served_donor_id = route.get("node_id", "") or donor_id
        served_route_id = f"{served_donor_id}:{route.get('served_request_count', '')}"
        await telemetry_recorder.record_research_validity_event(
            trace_id=trace_id,
            operation="donor.served",
            project_id=project_id,
            status="success",
            model_name=route.get("model") or coder.model_name,
            donor_id=served_donor_id,
            route_id=served_route_id,
            coding_run_id=run_id,
            codebook_version_id=coding_run.codebook_version_id or "",
        )
        db.add(
            CodingRunCoder(
                id=str(uuid.uuid4()),
                coding_run_id=run_id,
                project_id=project_id,
                coder_id=active_coder.coder_id,
                coder_type="llm",
                model_name=route.get("model") or coder.model_name,
                donor_id=served_donor_id,
                route_id=served_route_id,
                route_evidence_json=json.dumps(route),
            )
        )

        for raw_app, unit, codes in usable_applications:
            confidence = _confidence(raw_app.get("confidence"))
            gate_applications.append(
                {
                    "coder_id": active_coder.coder_id,
                    "model_name": route.get("model") or coder.model_name,
                    "donor_id": served_donor_id,
                    "route_id": served_route_id,
                    # Preserve endpoint identity as provenance only. Model
                    # identity determines independence at the reliability gate.
                    "endpoint_id": (
                        route.get("endpoint_id")
                        or getattr(coder.node, "endpoint_id", "")
                        or served_donor_id
                    ),
                    "provider_account_handle": route.get("provider_account_handle") or "",
                    "model_checkpoint": route.get("model") or coder.model_name,
                    "prompt_hash": prompt_hash,
                    "codebook_version_id": coding_run.codebook_version_id or "",
                    "protocol_version": route.get("protocol_version")
                    or QUALITATIVE_CODING_PROTOCOL["version"],
                    "decoding_profile": route.get("decoding_profile") or {"temperature": 0.2},
                    "conversation_scope": route.get("conversation_scope")
                    or "fresh_session_per_coder_call",
                    "cache_scope": route.get("cache_scope")
                    or "provider_prefix_cache_no_response_reuse",
                    "evidence_unit_id": unit.id,
                    "codes": codes,
                }
            )
            for code_id in codes:
                code_app = CodeApplication(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    task_id=task_id,
                    codebook_version_id=coding_run.codebook_version_id,
                    code_id=code_id,
                    evidence_unit_id=unit.id,
                    coding_run_id=run_id,
                    source_document_id=unit.source_document_id,
                    source_text=str(raw_app.get("quote") or unit.source_text),
                    source_location=unit.source_location,
                    start_offset=unit.start_offset,
                    end_offset=unit.end_offset,
                    coder_id=active_coder.coder_id,
                    coder_type="llm",
                    model_name=route.get("model") or coder.model_name,
                    donor_id=served_donor_id,
                    route_id=served_route_id,
                    route_evidence_json=json.dumps(route),
                    confidence=confidence,
                    reasoning=str(raw_app.get("rationale") or raw_app.get("memo") or ""),
                )
                db.add(code_app)
                db.add(
                    ResearchEvidenceEdge(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        source_type="evidence_unit",
                        source_id=unit.id,
                        relation="coded_as",
                        target_type="code_application",
                        target_id=code_app.id,
                        evidence_unit_id=unit.id,
                        coding_run_id=run_id,
                        task_id=task_id,
                        codebook_version_id=coding_run.codebook_version_id,
                        metadata_json=json.dumps(
                            graph_edge_metadata(
                                retrieval_mode="hybrid",
                                review_status="pending",
                                reliability_status="pending",
                                route_evidence=route,
                            )
                        ),
                    )
                )
                persisted_count += 1

    reliability = evaluate_reliability_gate(
        gate_applications,
        threshold=threshold,
        minimum_distinct_models=max_coders,
        require_rater_provenance=True,
    )
    promotion_status = reliability["promotion_status"]
    item_statuses = reliability.get("item_promotion_statuses") or item_level_promotion_statuses(
        reliability.get("matrix", {}),
        promotion_status,
    )
    await telemetry_recorder.record_research_validity_event(
        trace_id=trace_id,
        operation="coding_run.reliability",
        project_id=project_id,
        status="success" if promotion_status == "accepted" else "degraded",
        reliability_score=reliability.get("kappa"),
        coding_run_id=run_id,
        codebook_version_id=coding_run.codebook_version_id or "",
    )
    if promotion_status != "accepted":
        await telemetry_recorder.record_research_validity_event(
            trace_id=trace_id,
            operation="coding_run.low_consensus",
            project_id=project_id,
            status="degraded",
            reliability_score=reliability.get("kappa"),
            coding_run_id=run_id,
            codebook_version_id=coding_run.codebook_version_id or "",
        )
    application_rows = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.coding_run_id == run_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for row in application_rows:
        item_status = item_statuses.get(row.evidence_unit_id or "", promotion_status)
        row.promotion_status = item_status
        row.reliability_status = "accepted" if item_status == "accepted" else item_status
    coding_run.status = "completed" if persisted_count else "blocked"
    coding_run.completed_at = datetime.now(UTC)
    coding_run.reliability_method = reliability.get("method", "")
    coding_run.rater_count = reliability.get("rater_count", 0)
    coding_run.distinct_model_count = reliability.get("distinct_model_count", 0)
    coding_run.kappa = reliability.get("kappa")
    coding_run.alpha = reliability.get("alpha")
    coding_run.promotion_status = promotion_status
    coding_run.fallback_reason = reliability.get("fallback_reason", "")
    coding_run.route_evidence_json = json.dumps(route_evidence)
    coding_run.matrix_json = json.dumps(reliability.get("matrix", {}))
    coding_run.disagreement_json = json.dumps(reliability.get("low_agreement_codes", []))
    await db.commit()
    await db.refresh(coding_run)
    await telemetry_recorder.record_research_validity_event(
        trace_id=trace_id,
        operation="coding_run.complete",
        project_id=project_id,
        status="success" if persisted_count else "error",
        reliability_score=coding_run.kappa,
        coding_run_id=run_id,
        codebook_version_id=coding_run.codebook_version_id or "",
    )
    payload = coding_run.to_dict()
    payload["code_application_count"] = persisted_count
    return payload


async def run_task_coding_run_and_mark_review(
    db: AsyncSession,
    *,
    task: Any,
    project_id: str,
    evidence_unit_ids: list[str],
    created_by: str,
) -> dict:
    """Run task evidence coding and mirror gate status onto task review data."""
    coding_run = await run_independent_coding_run(
        db,
        project_id=project_id,
        task_id=task.id,
        evidence_unit_ids=evidence_unit_ids,
        limit=len(evidence_unit_ids),
        created_by=created_by,
    )
    task.validation_result = task_validation_payload_with_coding_run(
        task.validation_result,
        coding_run,
    )
    if coding_run.get("promotion_status") != "accepted":
        task.what_to_review = (
            "Research-validity coding needs reconciliation or human review: "
            f"{coding_run.get('promotion_status')}"
        )
    await db.commit()
    return coding_run
