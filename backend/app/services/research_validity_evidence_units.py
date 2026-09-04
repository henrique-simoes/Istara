"""Evidence-unit persistence and coder prompt construction (raw-source grounded)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.research_validity import (
    build_qualitative_coding_prompt,
    graph_edge_metadata,
)
from app.core.telemetry import telemetry_recorder
from app.models.codebook_version import CodebookVersion
from app.models.research_validity import (
    EvidenceUnit,
    ResearchEvidenceEdge,
)
from app.services.research_validity_schemas import MAX_CODING_SOURCE_TEXT_CHARS

logger = logging.getLogger(__name__)


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
            session=db,
        )
    return persisted
