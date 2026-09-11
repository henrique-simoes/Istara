"""Project-scoped, candidate-only links for downstream research findings."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.research_validity import graph_edge_metadata
from app.models.research_validity import ResearchEvidenceEdge
from app.models.task import Task


async def persist_scoped_derivation_links(
    db: AsyncSession,
    model: Any,
    raw_ids: object,
    fallback_ids: list[str],
    project_id: str,
    task: Task,
    source_type: str,
    source_id: str,
    target_type: str,
) -> list[str]:
    """Persist only active-project links and their provisional graph edges."""
    if isinstance(raw_ids, str):
        try:
            raw_ids = json.loads(raw_ids)
        except (json.JSONDecodeError, TypeError):
            raw_ids = [raw_ids]
    if isinstance(raw_ids, (list, tuple, set)):
        values = raw_ids
    else:
        values = [raw_ids] if raw_ids else []
    candidate_ids = list(dict.fromkeys(str(value) for value in values if value))
    if not candidate_ids:
        candidate_ids = list(dict.fromkeys(str(value) for value in fallback_ids if value))
    if not candidate_ids:
        return []

    # Flush generated upstream rows so same-run links are queryable, then admit
    # only records belonging to the active project.
    await db.flush()
    result = await db.execute(
        select(model.id).where(
            model.project_id == project_id,
            model.id.in_(candidate_ids),
        )
    )
    valid_ids = {str(value) for value in result.scalars().all()}
    rejected_ids = [value for value in candidate_ids if value not in valid_ids]
    if rejected_ids:
        warning = (
            "Generated downstream links outside the active project were discarded; "
            "human review is required."
        )
        existing_review_note = task.what_to_review or ""
        if warning not in existing_review_note:
            task.what_to_review = f"{existing_review_note} {warning}".strip()

    edge_metadata = graph_edge_metadata(
        retrieval_mode="hybrid",
        review_status="pending",
        reliability_status="uncoded",
    )
    edge_metadata.update(
        {
            "candidate_only": True,
            "promotion_rule": "requires_accepted_evidence_and_human_review",
        }
    )
    scoped_ids = [value for value in candidate_ids if value in valid_ids]
    for target_id in scoped_ids:
        db.add(
            ResearchEvidenceEdge(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_type=source_type,
                source_id=source_id,
                relation="derived_from",
                target_type=target_type,
                target_id=target_id,
                task_id=task.id,
                reliability_status="uncoded",
                metadata_json=json.dumps(edge_metadata),
            )
        )
    return scoped_ids
