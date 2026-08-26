"""Governed qualitative coding-run orchestration."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.codebook_version import CodebookVersion
from app.models.research_validity import (
    CodingRun,
    CodingRunCoder,
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)

CoderRunner = Callable[[Any, list[dict], str | None, str], Awaitable[dict]]
logger = logging.getLogger(__name__)
ACCEPTED_PROMOTION_STATUSES = {"accepted", "accepted_after_reconciliation"}
# A reliability pass may mark an item ``accepted`` when all coders agree, but
# that is still only a candidate until an explicit reconciliation decision is
# persisted. Reports must use this narrower, post-reconciliation state.
RECONCILED_CODE_APPLICATION_STATUSES = {"accepted", "reconciled"}
MAX_CODING_SOURCE_TEXT_CHARS = 700
CODING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "applications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "evidence_unit_id": {"type": "string"},
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "primary_code": {"type": "string"},
                    "quote": {"type": "string"},
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                    "memo": {"type": "string"},
                    "span_start": {"type": "integer"},
                    "span_end": {"type": "integer"},
                    "ambiguity": {"type": "string"},
                    "needs_codebook_revision": {"type": "boolean"},
                },
                "required": [
                    "evidence_unit_id",
                    "codes",
                    "primary_code",
                    "quote",
                    "confidence",
                ],
            },
        }
    },
    "required": ["applications"],
}


def _json_list_value(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item or "").strip()]


@dataclass(slots=True)
class CoderSpec:
    node: Any
    coder_id: str
    model_name: str
    # Production Pi selections retain the manager and exact resolved identity
    # so a catalog mutation can be rejected before dispatch.
    pi_manager: Any | None = None
    pi_endpoint_identity: tuple[str, ...] | None = None


def document_source_id(document_id: str, version: int | None = 1) -> str:
    """Stable source id for raw document evidence units."""
    return f"document:{document_id}:v{int(version or 1)}"


async def persist_document_source_evidence_units(
    db: AsyncSession,
    *,
    project_id: str,
    document_id: str,
    source_text: str,
    source_location: str = "",
    source_document_id: str | None = None,
    source_type: str = "document",
    method: str = "document",
    phase: str = "",
    task_id: str | None = None,
    version: int | None = 1,
    metadata: dict[str, Any] | None = None,
) -> list[EvidenceUnit]:
    """Persist raw-source evidence units for a document without creating findings.

    Documents are ingestion inputs to the Research Spine. They must become
    evidence units before any trusted Atomic Research artifact can be promoted.
    """
    from app.core.research_validity import segment_evidence_units

    text = str(source_text or "").strip()
    if not text:
        return []

    doc_source_id = document_source_id(document_id, version)
    source_doc_id = source_document_id or document_id
    existing = (
        (
            await db.execute(
                select(EvidenceUnit)
                .where(
                    EvidenceUnit.project_id == project_id,
                    EvidenceUnit.source_document_id == source_doc_id,
                    EvidenceUnit.source_id == doc_source_id,
                )
                .order_by(EvidenceUnit.unit_index)
            )
        )
        .scalars()
        .all()
    )
    if existing:
        return list(existing)

    units = segment_evidence_units(
        project_id=project_id,
        source_text=text,
        source_id=doc_source_id,
        source_location=source_location or doc_source_id,
        method=method or "",
        phase=phase or "",
    )
    persisted: list[EvidenceUnit] = []
    for unit in units:
        unit_metadata = {
            **unit.metadata,
            **(metadata or {}),
            "document_id": document_id,
            "document_version": int(version or 1),
            "candidate_only": False,
            "spine_policy": "raw_document_source_units_feed_independent_multi_model_validation",
        }
        evidence_unit = EvidenceUnit(
            id=unit.id,
            project_id=project_id,
            task_id=task_id,
            source_document_id=source_doc_id,
            source_id=doc_source_id,
            stable_id=unit.stable_id,
            unit_index=unit.unit_index,
            unit_type="source_span",
            source_type=source_type or "document",
            method=unit.method,
            phase=unit.phase,
            source_text=unit.source_text,
            source_location=unit.source_location,
            start_offset=unit.start_offset,
            end_offset=unit.end_offset,
            metadata_json=json.dumps(unit_metadata),
        )
        db.add(evidence_unit)
        edge_metadata = graph_edge_metadata(
            retrieval_mode="hybrid",
            review_status="pending",
            reliability_status="uncoded",
        )
        edge_metadata.update(
            {
                "source_type": source_type,
                "document_version": int(version or 1),
                "spine_policy": "document_contains_raw_source_evidence_unit",
            }
        )
        db.add(
            ResearchEvidenceEdge(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_type="document",
                source_id=document_id,
                relation="contains",
                target_type="evidence_unit",
                target_id=unit.id,
                evidence_unit_id=unit.id,
                task_id=task_id,
                reliability_status="uncoded",
                metadata_json=json.dumps(edge_metadata),
            )
        )
        persisted.append(evidence_unit)
    return persisted


async def record_source_evidence_unit_telemetry(
    *,
    project_id: str,
    units: list[EvidenceUnit],
    task_id: str | None = None,
    retrieval_mode: str = "hybrid",
    status: str = "success",
) -> None:
    """Record content-free evidence extraction events after caller commit."""
    for unit in units:
        await telemetry_recorder.record_research_validity_event(
            operation="evidence_unit.extract",
            project_id=project_id,
            task_id=task_id,
            evidence_unit_id=unit.id,
            retrieval_mode=retrieval_mode,
            status=status,
        )


async def document_source_unit_count_map(
    db: AsyncSession, *, project_id: str, document_ids: list[str]
) -> dict[str, int]:
    """Return source evidence-unit counts keyed by document id."""
    ids = [doc_id for doc_id in document_ids if doc_id]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(EvidenceUnit.source_document_id, func.count(EvidenceUnit.id))
            .where(
                EvidenceUnit.project_id == project_id,
                EvidenceUnit.source_document_id.in_(ids),
                EvidenceUnit.unit_type == "source_span",
            )
            .group_by(EvidenceUnit.source_document_id)
        )
    ).all()
    return {str(doc_id): int(count or 0) for doc_id, count in rows if doc_id}


def document_research_spine_summary(
    *,
    source_evidence_units: int,
    status: str,
    source: str,
    text_available: bool,
) -> dict[str, Any]:
    """Content-free document spine state for APIs and UI."""
    if source_evidence_units:
        state = "source_evidence_ready"
    elif status in {"pending", "processing"}:
        state = "awaiting_processing"
    elif status == "quarantined":
        state = "blocked_security_review"
    elif text_available:
        state = "missing_source_evidence_units"
    else:
        state = "non_text_or_no_source_units"
    return {
        "artifact_state": "raw_source",
        "source_evidence_state": state,
        "source_evidence_units": source_evidence_units,
        "source": source,
        "report_allowed": False,
        "spine_policy": (
            "Documents are raw sources; reportable research requires evidence units, "
            "independent extraction/coding, reliability or reconciliation, and Done-task approval."
        ),
    }


def _chat_model_names(names: list[Any]) -> list[str]:
    normalized: list[str] = []
    for name in names:
        text = str(name or "").strip()
        if not text or "embed" in text.lower() or text in normalized:
            continue
        normalized.append(text)
    return normalized


def _node_model_names(node: Any) -> list[str]:
    capabilities = getattr(node, "model_capabilities", {}) or {}
    loaded_alias_caps = [
        str(name).strip()
        for name, caps in capabilities.items()
        if (
            str(name).strip()
            and isinstance(caps, dict)
            and caps.get("is_loaded")
            and caps.get("loaded_instance_alias")
        )
    ]
    if loaded_alias_caps:
        return _chat_model_names(loaded_alias_caps)
    loaded_caps = [
        str(name).strip()
        for name, caps in capabilities.items()
        if str(name).strip() and isinstance(caps, dict) and caps.get("is_loaded")
    ]
    if loaded_caps:
        return _chat_model_names(loaded_caps)
    loaded = [str(name).strip() for name in getattr(node, "loaded_models", []) if str(name).strip()]
    if loaded:
        return _chat_model_names(loaded)
    capability_names = [str(name).strip() for name in capabilities if str(name).strip()]
    if capability_names:
        return _chat_model_names(capability_names)
    default_model = getattr(node, "default_model", None) or getattr(node, "model", None)
    return _chat_model_names([default_model]) if default_model else []


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


def _extract_json_payload(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if isinstance(parsed, list):
        return {"applications": parsed}
    if not isinstance(parsed, dict):
        raise ValueError("Coding response must be a JSON object or list.")
    return parsed


def _application_items(parsed: dict) -> list[dict]:
    """Accept common JSON variants without treating prose as coded evidence."""
    candidate_keys = (
        "applications",
        "code_applications",
        "coding_applications",
        "evidence_units",
        "items",
        "results",
    )
    for key in candidate_keys:
        value = parsed.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if any(
        key in parsed
        for key in (
            "evidence_unit_id",
            "unit_id",
            "id",
            "evidence_unit_stable_id",
            "stable_id",
            "unit_index",
        )
    ):
        return [parsed]
    return []


def _code_list(raw: dict) -> list[str]:
    codes = raw.get("codes")
    if codes is None:
        codes = [raw.get("code_id") or raw.get("primary_code")]
    if not isinstance(codes, list):
        codes = [codes]
    normalized: list[str] = []
    for code in codes:
        if isinstance(code, dict):
            value = code.get("code_id") or code.get("label") or code.get("name")
        else:
            value = code
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


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


def _confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.5
    return max(0.0, min(1.0, score))


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


async def _use_pi_coding_plane(db: AsyncSession, project_id: str) -> bool:
    """Research coding always uses the Pi model-management authority.

    The project's agentic-engine choice controls loop semantics, not provider
    discovery or independent-coder identity.  Keeping this compatibility seam
    makes the invariant explicit while older tests/extensions still patch it.
    """
    del db, project_id
    return True


async def _select_pi_coders(
    max_coders: int, *, project_id: str | None = None, manager: Any | None = None
) -> list[CoderSpec]:
    """Select independent coders backed by distinct Pi-managed models.

    Exact endpoint identities remain pinned as route evidence, while
    ``resolve_distinct`` fails closed when the catalog has fewer distinct model
    identities than requested. Endpoint replicas never fabricate diversity.
    """
    from types import SimpleNamespace

    if manager is None:
        from app.core.pi_runtime.model_manager import PiModelManager

        manager = PiModelManager()
    # Read-only DB projection of persisted LLMServer endpoint identities;
    # it never connects to a server or loads a model.
    await manager.ensure_db_projection()
    endpoints = manager.resolve_distinct(max(1, max_coders), project_id=project_id)
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
            pi_endpoint_identity=_pi_endpoint_identity(endpoint),
        )
        for endpoint in endpoints
    ]


def _pi_endpoint_identity(endpoint: Any) -> tuple[str, ...]:
    """Return non-secret fields that define one selected Pi endpoint."""
    return (
        str(getattr(endpoint, "endpoint_id", "") or ""),
        str(getattr(endpoint, "provider_kind", "") or ""),
        str(getattr(endpoint, "base_url", "") or ""),
        str(getattr(endpoint, "model", "") or ""),
        str(getattr(endpoint, "provider_account_handle", "") or ""),
        str(getattr(endpoint, "kind", "") or ""),
    )


async def _pi_coder_runner(
    coder: CoderSpec,
    messages: list[dict],
    model_name: str | None,
    project_id: str,
) -> dict:
    """W7 coder runner: structured dispatch pinned to the coder's exact endpoint."""
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    selected_endpoint_id = str(getattr(coder.node, "endpoint_id", "") or "").strip()
    if coder.pi_manager is not None and selected_endpoint_id:
        # Refresh dynamic projections and resolve against the same manager
        # used for selection. Any removal or identity mutation is rejected
        # before the provider call can create a rater or route record.
        await coder.pi_manager.ensure_db_projection()
        current_endpoint = coder.pi_manager.resolve(
            endpoint_id=selected_endpoint_id,
            model=model_name,
            project_id=project_id,
        )
        if coder.pi_endpoint_identity != _pi_endpoint_identity(current_endpoint):
            raise ValueError(
                "Pi coder catalog drift: selected endpoint identity changed "
                f"for {selected_endpoint_id!r}"
            )

    outcome = await agentic.structured(
        purpose="validity.coder",
        project_id=project_id,
        system=None,
        messages=messages,
        schema=CODING_RESPONSE_SCHEMA,
        params=TurnParams(
            temperature=0.2,
            model=model_name,
            endpoint_id=getattr(coder.node, "endpoint_id", None),
        ),
        engine="pi",
        spine_phase="execution",
    )
    served_endpoint_id = str(getattr(outcome, "endpoint_id", "") or "").strip()
    if selected_endpoint_id and served_endpoint_id and served_endpoint_id != selected_endpoint_id:
        # The endpoint is part of the source-of-truth route evidence.  A
        # provider or adapter that reports a different endpoint than the one
        # pinned in TurnParams must not be allowed to masquerade as the
        # selected independent coder; fail closed before any coding rows are
        # persisted or reliability is evaluated.
        raise ValueError(
            "Pi coder endpoint mismatch: selected "
            f"{selected_endpoint_id!r}, served {served_endpoint_id!r}"
        )
    return {
        "message": {"content": json.dumps(outcome.value)},
        "_istara_route": {
            "node_id": getattr(coder.node, "node_id", ""),
            "node_source": "pi",
            "provider_type": getattr(coder.node, "provider_type", ""),
            "model": model_name or "",
            "endpoint_id": served_endpoint_id or selected_endpoint_id,
            "provider_account_handle": getattr(coder.node, "provider_account_handle", ""),
            "decoding_profile": {"temperature": 0.2},
            "protocol_version": QUALITATIVE_CODING_PROTOCOL["version"],
            "conversation_scope": "fresh_session_per_coder_call",
            "cache_scope": "provider_prefix_cache_no_response_reuse",
            "route_kind": "coding_run",
            "outcome": "served",
        },
    }


async def _load_units(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str | None,
    evidence_unit_ids: list[str] | None,
    limit: int,
) -> list[EvidenceUnit]:
    query = select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)
    if task_id:
        query = query.where(EvidenceUnit.task_id == task_id)
    if evidence_unit_ids:
        query = query.where(EvidenceUnit.id.in_(evidence_unit_ids))
    query = query.order_by(EvidenceUnit.source_id, EvidenceUnit.unit_index).limit(
        max(1, min(limit, 200))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


def _is_qa_provisional_unit(unit: Any) -> bool:
    """True when an evidence unit is stamped as synthetic-QA provisional.

    The QA seeder stamps ``is_qa_provisional``/``promotion_blocked`` on
    evidence-unit metadata at ingestion (documents API). Any coding run that
    would promote such a unit is fail-closed blocked below.
    """
    try:
        metadata = json.loads(unit.metadata_json or "{}")
    except (json.JSONDecodeError, TypeError):
        metadata = {}
    if not isinstance(metadata, dict):
        return False
    return bool(metadata.get("is_qa_provisional"))


async def _load_codebook(
    db: AsyncSession,
    *,
    project_id: str,
    codebook_version_id: str | None,
) -> CodebookVersion | None:
    query = select(CodebookVersion).where(CodebookVersion.project_id == project_id)
    if codebook_version_id:
        query = query.where(CodebookVersion.id == codebook_version_id)
    else:
        query = query.order_by(CodebookVersion.created_at.desc()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


def _compact_source_text_for_coding(
    text: str, limit: int = MAX_CODING_SOURCE_TEXT_CHARS
) -> tuple[str, bool]:
    source = str(text or "").strip()
    if len(source) <= limit:
        return source, False
    half = max(1, limit // 2)
    omitted = len(source) - (half * 2)
    compact = (
        f"{source[:half].rstrip()}\n"
        f"[...source span compacted for model context; omitted_chars={omitted}...]\n"
        f"{source[-half:].lstrip()}"
    )
    return compact, True


def _coding_unit_payload(unit: EvidenceUnit) -> dict:
    payload = unit.to_dict()
    source_text = str(payload.get("source_text") or "")
    compact_text, truncated = _compact_source_text_for_coding(source_text)
    payload["source_text"] = compact_text
    payload["source_text_original_chars"] = len(source_text)
    payload["source_text_truncated_for_coding"] = truncated
    if truncated:
        payload["source_text_excerpt_policy"] = "head_tail_context_bound"
    return payload


def _coding_messages(
    units: list[EvidenceUnit], codebook: CodebookVersion | None, threshold: float
) -> list[dict]:
    codebook_payload = codebook.to_dict() if codebook else {"status": "draft", "codes": []}
    prompt = build_qualitative_coding_prompt(
        evidence_units=[_coding_unit_payload(unit) for unit in units],
        codebook=codebook_payload,
        project_policy={"default_threshold": threshold},
    )
    schema = {
        "applications": [
            {
                "evidence_unit_id": "unit id from the prompt",
                "stable_id": "stable evidence unit id from the prompt",
                "unit_index": 1,
                "codes": ["one or more governed or proposed qualitative codes"],
                "primary_code": "single best nominal code",
                "quote": "exact source quote/span",
                "confidence": 0.0,
                "rationale": "brief qualitative memo",
                "ambiguity": "",
                "needs_codebook_revision": False,
            }
        ]
    }
    return [
        {
            "role": "system",
            "content": (
                "You are an independent qualitative researcher. Code each evidence unit "
                "using the protected protocol and active codebook. Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{prompt}\n\nReturn JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            ),
        },
    ]


def _coding_repair_messages(
    units: list[EvidenceUnit], codebook: CodebookVersion | None, threshold: float
) -> list[dict]:
    messages = _coding_messages(units, codebook, threshold)
    messages[-1]["content"] += (
        "\n\nYour previous coding response was not usable for the reliability "
        "matrix. Return JSON only with an `applications` array. Include at "
        "least one application for every evidence unit, copy each "
        "`evidence_unit_id`, `stable_id`, and `unit_index` exactly from the "
        "prompt, and provide at least one qualitative code plus a quote, "
        "confidence, and rationale. If evidence is ambiguous, use a precise "
        "ambiguity code and low confidence rather than omitting the unit."
    )
    return messages


async def persist_task_nugget_evidence_units(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str | None,
    nugget_id: str,
    source_text: str,
    source_location: str = "",
    source_document_id: str | None = None,
    method: str = "",
    phase: str = "",
    source_type: str = "source_span",
    candidate_only: bool = False,
) -> list[EvidenceUnit]:
    """Persist evidence units and graph edges for one candidate/accepted nugget."""
    from app.core.research_validity import segment_evidence_units

    task_prefix = f"task:{task_id}:" if task_id else ""
    evidence_source_id = f"{task_prefix}nugget:{nugget_id}"
    units = segment_evidence_units(
        project_id=project_id,
        source_text=source_text[:2000],
        source_id=evidence_source_id,
        source_location=source_location,
        method=method,
        phase=phase,
    )
    persisted: list[EvidenceUnit] = []
    for unit in units:
        evidence_unit = EvidenceUnit(
            id=unit.id,
            project_id=project_id,
            task_id=task_id,
            source_document_id=source_document_id,
            source_id=evidence_source_id,
            stable_id=unit.stable_id,
            unit_index=unit.unit_index,
            unit_type="candidate_atom" if candidate_only else "source_span",
            source_type=source_type,
            method=unit.method,
            phase=unit.phase,
            source_text=unit.source_text,
            source_location=unit.source_location,
            start_offset=unit.start_offset,
            end_offset=unit.end_offset,
            metadata_json=json.dumps(
                {
                    **unit.metadata,
                    "candidate_only": candidate_only,
                    "source_type": source_type,
                    "spine_policy": (
                        "candidate_nugget_text_requires_exact_source_span_before_governed_coding"
                        if candidate_only
                        else "exact_source_span_available_for_governed_coding"
                    ),
                }
            ),
        )
        db.add(evidence_unit)
        edge_metadata = graph_edge_metadata(
            retrieval_mode="hybrid",
            review_status="pending",
            reliability_status="uncoded",
        )
        edge_metadata.update(
            {
                "candidate_only": candidate_only,
                "source_type": source_type,
            }
        )
        db.add(
            ResearchEvidenceEdge(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_type="nugget",
                source_id=nugget_id,
                relation="grounded_in",
                target_type="evidence_unit",
                target_id=unit.id,
                evidence_unit_id=unit.id,
                task_id=task_id,
                metadata_json=json.dumps(edge_metadata),
            )
        )
        persisted.append(evidence_unit)
        await telemetry_recorder.record_research_validity_event(
            operation="evidence_unit.extract",
            project_id=project_id,
            task_id=task_id,
            evidence_unit_id=unit.id,
            retrieval_mode="hybrid",
            status="success",
        )
    return persisted


async def _task_finding_support_diagnostics(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    code_rows: list[CodeApplication],
) -> dict:
    """Check item-level finding support instead of accepting a whole task in bulk."""
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    accepted_evidence_unit_ids = {
        row.evidence_unit_id
        for row in code_rows
        if _is_reconciled_code_application(row) and row.evidence_unit_id
    }
    nuggets = (
        (
            await db.execute(
                select(Nugget).where(Nugget.project_id == project_id, Nugget.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    facts = (
        (
            await db.execute(
                select(Fact).where(Fact.project_id == project_id, Fact.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    insights = (
        (
            await db.execute(
                select(Insight).where(Insight.project_id == project_id, Insight.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    recommendations = (
        (
            await db.execute(
                select(Recommendation).where(
                    Recommendation.project_id == project_id,
                    Recommendation.task_id == task_id,
                )
            )
        )
        .scalars()
        .all()
    )

    accepted_nugget_ids: set[str] = set()
    if accepted_evidence_unit_ids:
        edge_rows = (
            (
                await db.execute(
                    select(ResearchEvidenceEdge.source_id).where(
                        ResearchEvidenceEdge.project_id == project_id,
                        ResearchEvidenceEdge.task_id == task_id,
                        ResearchEvidenceEdge.source_type == "nugget",
                        ResearchEvidenceEdge.relation == "grounded_in",
                        ResearchEvidenceEdge.evidence_unit_id.in_(accepted_evidence_unit_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        accepted_nugget_ids = set(edge_rows)

    accepted_fact_ids: set[str] = set()
    accepted_insight_ids: set[str] = set()
    accepted_recommendation_ids: set[str] = set()
    unsupported: list[dict[str, str]] = []

    for row in nuggets:
        if row.id not in accepted_nugget_ids:
            unsupported.append(
                {
                    "type": "nugget",
                    "id": row.id,
                    "reason": "no accepted coded evidence unit is linked to this source nugget",
                }
            )

    for row in facts:
        nugget_ids = _json_list_value(row.nugget_ids)
        if not nugget_ids:
            unsupported.append(
                {"type": "fact", "id": row.id, "reason": "fact has no linked nuggets"}
            )
            continue
        missing = [nid for nid in nugget_ids if nid not in accepted_nugget_ids]
        if missing:
            unsupported.append(
                {
                    "type": "fact",
                    "id": row.id,
                    "reason": "fact depends on unaccepted nugget(s): " + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_fact_ids.add(row.id)

    for row in insights:
        fact_ids = _json_list_value(row.fact_ids)
        if not fact_ids:
            unsupported.append(
                {
                    "type": "insight",
                    "id": row.id,
                    "reason": "insight has no linked facts",
                }
            )
            continue
        missing = [fid for fid in fact_ids if fid not in accepted_fact_ids]
        if missing:
            unsupported.append(
                {
                    "type": "insight",
                    "id": row.id,
                    "reason": "insight depends on unaccepted fact(s): " + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_insight_ids.add(row.id)

    for row in recommendations:
        insight_ids = _json_list_value(row.insight_ids)
        if not insight_ids:
            unsupported.append(
                {
                    "type": "recommendation",
                    "id": row.id,
                    "reason": "recommendation has no linked insights",
                }
            )
            continue
        missing = [iid for iid in insight_ids if iid not in accepted_insight_ids]
        if missing:
            unsupported.append(
                {
                    "type": "recommendation",
                    "id": row.id,
                    "reason": "recommendation depends on unaccepted insight(s): "
                    + ", ".join(missing[:5]),
                }
            )
        else:
            accepted_recommendation_ids.add(row.id)

    return {
        "accepted_evidence_unit_ids": sorted(accepted_evidence_unit_ids),
        "accepted_nugget_ids": sorted(accepted_nugget_ids),
        "accepted_fact_ids": sorted(accepted_fact_ids),
        "accepted_insight_ids": sorted(accepted_insight_ids),
        "accepted_recommendation_ids": sorted(accepted_recommendation_ids),
        "unsupported_findings": unsupported,
        "unsupported_finding_count": len(unsupported),
    }


def task_validation_payload_with_coding_run(
    existing_validation_result: str | None,
    coding_run: dict,
) -> str:
    """Merge coding-run status into task validation metadata."""
    try:
        payload = json.loads(existing_validation_result or "{}")
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    payload["research_validity"] = {
        "coding_run_id": coding_run.get("id"),
        "promotion_status": coding_run.get("promotion_status"),
        "reliability_method": coding_run.get("reliability_method"),
        "kappa": coding_run.get("kappa"),
        "alpha": coding_run.get("alpha"),
        "rater_count": coding_run.get("rater_count"),
        "distinct_model_count": coding_run.get("distinct_model_count"),
        "fallback_reason": coding_run.get("fallback_reason"),
    }
    return json.dumps(payload)


def mark_task_provisional_skill_artifacts(task: Any) -> None:
    """Block skill-created artifacts that have not entered accepted Spine gates."""
    task.review_state = (
        task.review_state
        if task.review_state and task.review_state != "none"
        else "awaiting_review"
    )
    task.what_to_review = task.what_to_review or (
        "Skill-generated research artifacts are provisional: exact raw-source "
        "evidence units, coding reliability, reconciliation, and Done approval "
        "are required before they can become report evidence."
    )
    try:
        validation_payload = json.loads(task.validation_result or "{}")
        if not isinstance(validation_payload, dict):
            validation_payload = {}
    except Exception:
        validation_payload = {}
    current = validation_payload.get("research_validity", {})
    validation_payload["research_validity"] = {
        **(current if isinstance(current, dict) else {}),
        "status": "provisional",
        "promotion_status": "blocked",
        "report_allowed": False,
        "reason": "skill_output_missing_exact_source_span_or_accepted_coding_run",
    }
    task.validation_result = json.dumps(validation_payload)


def add_agent_initial_code_applications(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    tags: list,
    evidence_unit_id: str | None,
    source_document_id: str | None,
    source_text: str,
    source_location: str,
    start_offset: int | None,
    end_offset: int | None,
    agent_id: str,
    confidence: float,
    reasoning: str,
) -> int:
    """Persist lower-assurance skill-provided codes before governed coding."""
    count = 0
    for tag in tags[:5]:
        if not isinstance(tag, str) or not tag.strip():
            continue
        db.add(
            CodeApplication(
                id=str(uuid.uuid4()),
                project_id=project_id,
                task_id=task_id,
                code_id=tag,
                evidence_unit_id=evidence_unit_id,
                source_document_id=source_document_id,
                source_text=source_text,
                source_location=source_location,
                start_offset=start_offset,
                end_offset=end_offset,
                coder_id=agent_id,
                coder_type="llm",
                route_evidence_json=json.dumps(
                    {
                        "route_kind": "agent_initial_code_application",
                        "agent_id": agent_id,
                        "task_id": task_id,
                    }
                ),
                confidence=confidence,
                reasoning=reasoning,
                reliability_status="needs_human_review",
                reconciliation_status="unreconciled",
                promotion_status="needs_human_review",
            )
        )
        count += 1
    return count


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

            manager_accessor = getattr(agentic, "model_manager", None)
            if callable(manager_accessor):
                coders = await _select_pi_coders(
                    max_coders=max_coders,
                    project_id=project_id,
                    manager=manager_accessor(),
                )
            else:
                coders = await _select_pi_coders(
                    max_coders=max_coders, project_id=project_id
                )
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
        try:
            response = await runner(coder, messages, coder.model_name or None, project_id)
            content = response.get("message", {}).get("content", "")
            parsed = _extract_json_payload(content)
            usable_applications = _usable_coding_applications(
                parsed,
                unit_by_id=unit_by_id,
                units=units,
            )
            if not _has_complete_unit_coverage(usable_applications, unit_by_id=unit_by_id):
                repair_response = await runner(
                    coder,
                    _coding_repair_messages(units, codebook, threshold),
                    coder.model_name or None,
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
                    response = repair_response
                    parsed = repair_parsed
                    usable_applications = repair_usable
            if not _has_complete_unit_coverage(usable_applications, unit_by_id=unit_by_id):
                raise ValueError(
                    "coder response lacked complete evidence-unit coverage "
                    f"({len({unit.id for _, unit, _ in usable_applications})}/"
                    f"{len(unit_by_id)})"
                )
        except Exception as exc:
            route_evidence.append(
                {
                    "coder_id": coder.coder_id,
                    "model": coder.model_name,
                    "outcome": "failed",
                    "error": str(exc)[:160],
                }
            )
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
                coder_id=coder.coder_id,
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
                    "coder_id": coder.coder_id,
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
                    coder_id=coder.coder_id,
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


def _code_application_state(row: CodeApplication) -> dict:
    return {
        "code_id": row.code_id,
        "review_status": row.review_status,
        "reliability_status": row.reliability_status,
        "reconciliation_status": row.reconciliation_status,
        "promotion_status": row.promotion_status,
    }


async def _refresh_coding_run_reconciliation_status(
    db: AsyncSession,
    *,
    project_id: str,
    coding_run_id: str | None,
) -> None:
    if not coding_run_id:
        return
    run = await db.get(CodingRun, coding_run_id)
    if not run or run.project_id != project_id:
        return
    code_rows = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.coding_run_id == coding_run_id,
                )
            )
        )
        .scalars()
        .all()
    )
    unresolved_count = sum(1 for row in code_rows if _is_unresolved_code_application(row))
    accepted_count = sum(1 for row in code_rows if _is_reconciled_code_application(row))
    if (
        unresolved_count == 0
        and accepted_count > 0
        and run.promotion_status not in ACCEPTED_PROMOTION_STATUSES
    ):
        run.promotion_status = "accepted_after_reconciliation"
        run.fallback_reason = "Human reconciliation accepted evidence after low agreement."
    elif unresolved_count == 0 and code_rows and accepted_count == 0:
        run.promotion_status = "rejected_after_reconciliation"
        run.fallback_reason = "Human reconciliation rejected all coded evidence."


def _is_unresolved_code_application(row: CodeApplication) -> bool:
    if (
        row.promotion_status == "rejected"
        or row.reconciliation_status == "rejected"
        or row.review_status == "rejected"
    ):
        return False
    return not _is_reconciled_code_application(row)


def _is_reconciled_code_application(row: CodeApplication) -> bool:
    """Return whether an application has both reliability and reconciliation.

    A passing Fleiss/alpha run is not a human decision. Keep report support
    fail-closed until the application carries the durable reconciliation state
    written by ``create_reconciliation_decision``.
    """
    return (
        row.promotion_status in ACCEPTED_PROMOTION_STATUSES
        and row.reconciliation_status in RECONCILED_CODE_APPLICATION_STATUSES
    )


async def create_reconciliation_decision(
    db: AsyncSession,
    *,
    project_id: str,
    code_application_id: str,
    decision_type: str,
    decided_by: str,
    rationale: str = "",
    accepted_code_id: str | None = None,
    source: str = "human_review",
) -> dict:
    """Persist a reconciliation decision and mirror it onto the code application."""
    normalized_decision = (decision_type or "").strip().lower()
    if normalized_decision not in {
        "accepted",
        "rejected",
        "revised",
        "needs_human_review",
    }:
        raise ValueError("Unsupported reconciliation decision type.")
    result = await db.execute(
        select(CodeApplication).where(
            CodeApplication.id == code_application_id,
            CodeApplication.project_id == project_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise LookupError("Code application not found.")

    previous_state = _code_application_state(row)
    if normalized_decision == "accepted":
        row.review_status = "approved"
        row.reconciliation_status = "accepted"
        row.promotion_status = "accepted"
        if row.reliability_status not in ("accepted", "reliable", "passed"):
            row.reliability_status = "human_reconciled"
    elif normalized_decision == "rejected":
        row.review_status = "rejected"
        row.reconciliation_status = "rejected"
        row.promotion_status = "rejected"
        row.reliability_status = "rejected"
    elif normalized_decision == "revised" and accepted_code_id:
        row.code_id = accepted_code_id
        row.review_status = "approved"
        row.reconciliation_status = "reconciled"
        row.promotion_status = "accepted"
        row.reliability_status = "human_reconciled"
    else:
        row.review_status = "modified"
        row.reconciliation_status = "revised"
        row.promotion_status = "needs_reconciliation"
        row.reliability_status = "needs_human_review"

    row.reviewed_by = decided_by or "local-user"
    row.reviewed_at = datetime.now(UTC)
    resolved_state = _code_application_state(row)
    try:
        route_evidence = json.loads(row.route_evidence_json or "{}")
    except json.JSONDecodeError:
        route_evidence = {}

    decision = ReconciliationDecision(
        id=str(uuid.uuid4()),
        project_id=project_id,
        task_id=row.task_id,
        coding_run_id=row.coding_run_id,
        evidence_unit_id=row.evidence_unit_id,
        code_application_id=row.id,
        decision_type=normalized_decision,
        source=source,
        accepted_code_id=(
            accepted_code_id or row.code_id if row.promotion_status == "accepted" else ""
        ),
        rationale=rationale,
        decided_by=row.reviewed_by or "",
        previous_state_json=json.dumps(previous_state),
        resolved_state_json=json.dumps(resolved_state),
        route_evidence_json=json.dumps(route_evidence),
    )
    db.add(decision)
    db.add(
        ResearchEvidenceEdge(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_type="code_application",
            source_id=row.id,
            relation="reconciled_by",
            target_type="reconciliation_decision",
            target_id=decision.id,
            evidence_unit_id=row.evidence_unit_id,
            coding_run_id=row.coding_run_id,
            task_id=row.task_id,
            codebook_version_id=row.codebook_version_id,
            reliability_status=row.reliability_status,
            metadata_json=json.dumps(
                graph_edge_metadata(
                    retrieval_mode="graph+hybrid",
                    review_status=row.review_status,
                    reliability_status=row.reliability_status,
                    route_evidence=route_evidence,
                )
            ),
        )
    )
    await _refresh_coding_run_reconciliation_status(
        db,
        project_id=project_id,
        coding_run_id=row.coding_run_id,
    )
    await db.commit()
    await db.refresh(row)
    await db.refresh(decision)
    await telemetry_recorder.record_research_validity_event(
        trace_id=uuid.uuid4().hex[:36],
        operation="reconciliation_decision.create",
        project_id=project_id,
        task_id=row.task_id,
        status="success",
        route_id=row.route_id,
        donor_id=row.donor_id,
        coding_run_id=row.coding_run_id or "",
        evidence_unit_id=row.evidence_unit_id or "",
        codebook_version_id=row.codebook_version_id or "",
    )
    payload = decision.to_dict()
    payload["code_application"] = row.to_dict()
    return payload


async def _load_traceability_findings(
    db: AsyncSession,
    *,
    project_id: str,
    finding_ids: set[str],
    task_ids: set[str],
    finding_id: str | None,
) -> tuple[list[dict], dict[str, dict]]:
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    finding_models = (
        ("nugget", Nugget),
        ("fact", Fact),
        ("insight", Insight),
        ("recommendation", Recommendation),
    )
    rows: list[dict] = []
    by_id: dict[str, dict] = {}
    for finding_type, model_cls in finding_models:
        query = select(model_cls).where(model_cls.project_id == project_id)
        if finding_ids:
            query = query.where(model_cls.id.in_(finding_ids))
        elif task_ids:
            query = query.where(model_cls.task_id.in_(task_ids))
        elif finding_id:
            query = query.where(model_cls.id == finding_id)
        else:
            continue
        result = await db.execute(query)
        for row in result.scalars().all():
            payload = {
                "id": row.id,
                "type": finding_type,
                "task_id": getattr(row, "task_id", None),
                "phase": getattr(row, "phase", ""),
                "confidence": getattr(row, "confidence", None),
            }
            rows.append(payload)
            by_id[row.id] = payload
    return rows, by_id


async def build_evidence_graph_traceability(
    db: AsyncSession,
    *,
    project_id: str,
    report_id: str | None = None,
    task_id: str | None = None,
    finding_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Build a GraphRAG-ready traceability answer from stored evidence-chain data."""
    from app.models.project_report import ProjectReport

    capped_limit = max(1, min(limit, 100))
    report_query = (
        select(ProjectReport)
        .where(ProjectReport.project_id == project_id)
        .order_by(ProjectReport.updated_at.desc())
        .limit(capped_limit)
    )
    if report_id:
        report_query = select(ProjectReport).where(
            ProjectReport.project_id == project_id,
            ProjectReport.id == report_id,
        )
    report_rows = list((await db.execute(report_query)).scalars().all())

    report_finding_ids: set[str] = set()
    report_index: list[dict] = []
    for report in report_rows:
        finding_ids = _json_list_value(report.finding_ids_json)
        if finding_id and finding_id not in finding_ids and not report_id:
            continue
        report_finding_ids.update(finding_ids)
        report_index.append(
            {
                **report.to_dict(),
                "finding_ids": finding_ids,
                "source_document_ids": _json_list_value(report.source_document_ids_json),
                "codebook_version_id": report.codebook_version_id,
            }
        )

    seed_task_ids = {task_id} if task_id else set()
    findings, finding_by_id = await _load_traceability_findings(
        db,
        project_id=project_id,
        finding_ids=report_finding_ids,
        task_ids=seed_task_ids,
        finding_id=finding_id,
    )
    task_ids = {row["task_id"] for row in findings if row.get("task_id")}
    if task_id:
        task_ids.add(task_id)

    code_query = select(CodeApplication).where(CodeApplication.project_id == project_id)
    if task_ids:
        code_query = code_query.where(CodeApplication.task_id.in_(task_ids))
    elif finding_id or report_id or task_id:
        code_query = code_query.where(CodeApplication.task_id == "__no_task_match__")
    code_rows = list((await db.execute(code_query)).scalars().all())
    code_applications = [row.to_dict() for row in code_rows[: capped_limit * 10]]
    unresolved = [row for row in code_rows if _is_unresolved_code_application(row)]

    run_ids = {row.coding_run_id for row in code_rows if row.coding_run_id}
    coding_runs: list[dict] = []
    if run_ids:
        run_rows = (
            (
                await db.execute(
                    select(CodingRun)
                    .where(CodingRun.project_id == project_id, CodingRun.id.in_(run_ids))
                    .order_by(CodingRun.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        coding_runs = [run.to_dict() for run in run_rows]

    task_gates: dict[str, dict] = {}
    for scoped_task_id in sorted(task_ids):
        task_gates[scoped_task_id] = await assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=scoped_task_id,
        )

    decision_query = select(ReconciliationDecision).where(
        ReconciliationDecision.project_id == project_id
    )
    if task_ids:
        decision_query = decision_query.where(ReconciliationDecision.task_id.in_(task_ids))
    elif run_ids:
        decision_query = decision_query.where(ReconciliationDecision.coding_run_id.in_(run_ids))
    decisions = list(
        (
            await db.execute(
                decision_query.order_by(ReconciliationDecision.created_at.desc()).limit(
                    capped_limit * 5
                )
            )
        )
        .scalars()
        .all()
    )

    edge_query = select(ResearchEvidenceEdge).where(ResearchEvidenceEdge.project_id == project_id)
    if task_ids:
        edge_query = edge_query.where(ResearchEvidenceEdge.task_id.in_(task_ids))
    elif run_ids:
        edge_query = edge_query.where(ResearchEvidenceEdge.coding_run_id.in_(run_ids))
    edges = list(
        (
            await db.execute(
                edge_query.order_by(ResearchEvidenceEdge.created_at.desc()).limit(capped_limit * 10)
            )
        )
        .scalars()
        .all()
    )

    report_dependencies: list[dict] = []
    for report in report_index:
        report_findings = [
            finding_by_id[fid] for fid in report["finding_ids"] if fid in finding_by_id
        ]
        report_task_ids = sorted({row["task_id"] for row in report_findings if row.get("task_id")})
        report_unresolved = [
            row.to_dict()
            for row in unresolved
            if row.task_id and row.task_id in set(report_task_ids)
        ]
        missing_task_gates = [
            tid
            for tid in report_task_ids
            if tid not in task_gates or "report_allowed" not in task_gates.get(tid, {})
        ]
        report_allowed = (
            bool(report_task_ids)
            and not missing_task_gates
            and all(bool(task_gates[tid].get("report_allowed")) for tid in report_task_ids)
        )
        report_dependencies.append(
            {
                "report_id": report["id"],
                "title": report["title"],
                "layer": report["layer"],
                "finding_ids": report["finding_ids"],
                "task_ids": report_task_ids,
                "finding_count": len(report_findings),
                "low_agreement_dependency_count": len(report_unresolved),
                "missing_task_gate_count": len(missing_task_gates),
                "missing_task_gate_ids": missing_task_gates,
                "report_allowed_by_research_validity": report_allowed,
                "blocked_code_applications": report_unresolved,
            }
        )

    task_dependencies = [
        {
            "task_id": scoped_task_id,
            "report_gate": task_gates.get(scoped_task_id, {}),
            "code_application_count": sum(1 for row in code_rows if row.task_id == scoped_task_id),
            "unresolved_code_application_count": sum(
                1 for row in unresolved if row.task_id == scoped_task_id
            ),
            "accepted_code_application_count": sum(
                1
                for row in code_rows
                if row.task_id == scoped_task_id
                and _is_reconciled_code_application(row)
            ),
        }
        for scoped_task_id in sorted(task_ids)
    ]

    return {
        "project_id": project_id,
        "filters": {
            "report_id": report_id,
            "task_id": task_id,
            "finding_id": finding_id,
            "limit": capped_limit,
        },
        "retrieval_mode": "graph+hybrid",
        "contract": {
            "graph_role": "synthesis_and_traceability",
            "hybrid_rag_role": "exact_evidence_backfill",
            "promotion_rule": (
                "graph_traceability_cannot_bypass_coding_reliability_reconciliation_or_done_gates"
            ),
        },
        "reports": report_index,
        "findings": findings,
        "task_dependencies": task_dependencies,
        "report_dependencies": report_dependencies,
        "coding_runs": coding_runs,
        "code_applications": code_applications,
        "reconciliation_decisions": [decision.to_dict() for decision in decisions],
        "evidence_graph_edges": [edge.to_dict() for edge in edges],
        "low_agreement_dependencies": [row.to_dict() for row in unresolved],
        "summary": {
            "report_count": len(report_index),
            "finding_count": len(findings),
            "task_count": len(task_dependencies),
            "coding_run_count": len(coding_runs),
            "code_application_count": len(code_applications),
            "reconciliation_decision_count": len(decisions),
            "evidence_graph_edge_count": len(edges),
            "low_agreement_dependency_count": len(unresolved),
            "blocked_report_count": sum(
                1
                for report in report_dependencies
                if report["low_agreement_dependency_count"] > 0
                or not report["report_allowed_by_research_validity"]
            ),
        },
    }


async def assess_task_research_validity(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
) -> dict:
    """Return whether task-bound findings may flow into reports."""
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    latest_run_result = await db.execute(
        select(CodingRun)
        .where(CodingRun.project_id == project_id, CodingRun.task_id == task_id)
        .order_by(CodingRun.created_at.desc())
        .limit(1)
    )
    latest_run = latest_run_result.scalar_one_or_none()
    code_rows = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.task_id == task_id,
                )
            )
        )
        .scalars()
        .all()
    )
    task_finding_count = 0
    for model_cls in (Nugget, Fact, Insight, Recommendation):
        rows = (
            (
                await db.execute(
                    select(model_cls.id).where(
                        model_cls.project_id == project_id,
                        model_cls.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        task_finding_count += len(rows)
    accepted_count = sum(1 for row in code_rows if _is_reconciled_code_application(row))
    unresolved_count = sum(1 for row in code_rows if _is_unresolved_code_application(row))
    base = {
        "latest_coding_run": latest_run.to_dict() if latest_run else None,
        "code_application_count": len(code_rows),
        "task_finding_count": task_finding_count,
        "accepted_code_application_count": accepted_count,
        "unresolved_code_application_count": unresolved_count,
    }

    if task_finding_count == 0 and not code_rows:
        return {
            **base,
            "report_allowed": False,
            "reason": (
                "Task has no accepted/reconciled evidence or Research Spine artifacts to report."
            ),
        }
    if unresolved_count:
        return {
            **base,
            "report_allowed": False,
            "reason": f"Task has {unresolved_count} unreconciled code application(s).",
        }
    if (
        latest_run
        and code_rows
        and latest_run.promotion_status not in ACCEPTED_PROMOTION_STATUSES
    ):
        return {
            **base,
            "report_allowed": False,
            "reason": (
                "Latest task coding run is not accepted "
                f"({latest_run.promotion_status or latest_run.status})."
            ),
        }
    accepted_document_rows = [
        row
        for row in code_rows
        if _is_reconciled_code_application(row) and row.source_document_id
    ]
    if accepted_document_rows:
        from app.models.document import Document

        source_document_ids = {str(row.source_document_id) for row in accepted_document_rows}
        current_documents = (
            (
                await db.execute(
                    select(Document).where(
                        Document.project_id == project_id,
                        Document.id.in_(source_document_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        current_by_id = {document.id: document for document in current_documents}
        evidence_unit_ids = {
            str(row.evidence_unit_id)
            for row in accepted_document_rows
            if row.evidence_unit_id
        }
        units = (
            (
                await db.execute(
                    select(EvidenceUnit).where(
                        EvidenceUnit.project_id == project_id,
                        EvidenceUnit.id.in_(evidence_unit_ids),
                    )
                )
            )
            .scalars()
            .all()
            if evidence_unit_ids
            else []
        )
        unit_by_id = {unit.id: unit for unit in units}
        stale_source_rows = []
        for row in accepted_document_rows:
            document = current_by_id.get(str(row.source_document_id))
            unit = unit_by_id.get(str(row.evidence_unit_id or ""))
            try:
                unit_metadata = json.loads(unit.metadata_json or "{}") if unit else {}
            except (json.JSONDecodeError, TypeError):
                unit_metadata = {}
            unit_version = unit_metadata.get("document_version")
            version_is_current = False
            if document is not None:
                try:
                    version_is_current = unit_version is None or int(unit_version) == int(
                        document.version or 1
                    )
                except (TypeError, ValueError):
                    version_is_current = False
            if document is None or not version_is_current:
                stale_source_rows.append(row)
        if stale_source_rows:
            return {
                **base,
                "report_allowed": False,
                "stale_source_code_application_count": len(stale_source_rows),
                "reason": (
                    f"Task has {len(stale_source_rows)} accepted code application(s) "
                    "grounded in a deleted or superseded source document."
                ),
            }
    support = await _task_finding_support_diagnostics(
        db,
        project_id=project_id,
        task_id=task_id,
        code_rows=list(code_rows),
    )
    base_with_support = {**base, **support}
    if task_finding_count and not code_rows:
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": "Task has reportable findings but no coded evidence applications.",
        }
    if code_rows and accepted_count == 0:
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": "Task has code applications but no accepted/reconciled coded evidence.",
        }
    if task_finding_count and support["unsupported_finding_count"]:
        unsupported_ids = [
            f"{row['type']}:{row['id']}" for row in support["unsupported_findings"][:5]
        ]
        return {
            **base_with_support,
            "report_allowed": False,
            "reason": (
                f"Task has {support['unsupported_finding_count']} finding(s) without "
                "accepted/reconciled source evidence: " + ", ".join(unsupported_ids)
            ),
        }
    return {
        **base_with_support,
        "report_allowed": True,
        "reason": "Task has no pending research-validity blocker.",
    }
