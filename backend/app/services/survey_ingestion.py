"""Survey response ingestion for the Research Spine.

Each question-answer pair creates a provisional visible nugget plus a raw source
evidence unit. The nugget is not reportable until governed coding,
reliability/reconciliation, and Done-task gates accept it.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Nugget
from app.models.survey_integration import SurveyLink
from app.services.research_validity_service import persist_task_nugget_evidence_units

logger = logging.getLogger(__name__)


async def ingest_responses(
    db: AsyncSession,
    link: SurveyLink,
    responses: list[dict],
    project_id: str,
) -> dict:
    """Convert survey responses into provisional nuggets and evidence units.

    Each question-answer pair becomes a Nugget with:
    - source: survey name from the link
    - text: "Q: {question}\\nA: {answer}"
    - tags: ["survey", survey_name]
    - phase: "discover"

    Args:
        db: Async database session.
        link: The SurveyLink that ties the external survey to a Istara project.
        responses: Normalised responses from a survey adapter, each with an
            ``"answers"`` key containing ``[{"question": str, "answer": str}, ...]``.
        project_id: The Istara project to attach nuggets to.

    Returns:
        A summary dict with nugget and evidence-unit counts.
    """
    created = 0
    evidence_units_created = 0
    skipped = 0

    for response in responses:
        response_id = str(response.get("id", "") or "")
        for qa in response.get("answers", []):
            question = qa.get("question", "").strip()
            answer = qa.get("answer", "").strip()

            # Skip empty answers — no evidence to record
            if not answer:
                skipped += 1
                continue

            source_location = f"response_{response_id}"
            source_text = f"Q: {question}\nA: {answer}"
            nugget = Nugget(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text=source_text,
                source=link.external_survey_name or f"survey-{link.external_survey_id}",
                source_location=source_location,
                tags=json.dumps(["survey", link.external_survey_name or "unknown"]),
                phase="discover",
            )
            db.add(nugget)
            units = await persist_task_nugget_evidence_units(
                db,
                project_id=project_id,
                task_id=None,
                nugget_id=nugget.id,
                source_text=source_text,
                source_location=source_location,
                method="survey",
                phase="discover",
                source_type="survey_response",
                candidate_only=False,
            )
            evidence_units_created += len(units)
            created += 1

    # Update link metadata
    link.response_count = (link.response_count or 0) + len(responses)
    link.last_response_at = datetime.now(UTC)

    await db.commit()

    logger.info(
        "Ingested %d provisional nuggets and %d evidence units from %d responses (skipped %d empty answers) for link %s",
        created,
        evidence_units_created,
        len(responses),
        skipped,
        link.id,
    )

    return {
        "nuggets_created": created,
        "evidence_units_created": evidence_units_created,
        "responses_processed": len(responses),
        "empty_answers_skipped": skipped,
    }
