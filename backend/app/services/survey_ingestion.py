"""Survey response ingestion — converts survey responses into Istara Nuggets.

Each question-answer pair from a survey response becomes a Nugget (raw evidence)
in the Atomic Research evidence chain.  The nuggets are tagged with the survey
platform and survey name so they can be traced back to their source.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Nugget
from app.models.survey_integration import SurveyLink

logger = logging.getLogger(__name__)


async def ingest_responses(
    db: AsyncSession,
    link: SurveyLink,
    responses: list[dict],
    project_id: str,
) -> dict:
    """Convert survey responses into Nuggets (raw evidence).

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
        A summary dict: ``{"nuggets_created": int, "responses_processed": int}``.
    """
    created = 0
    skipped = 0

    for response in responses:
        for qa in response.get("answers", []):
            question = qa.get("question", "").strip()
            answer = qa.get("answer", "").strip()

            # Skip empty answers — no evidence to record
            if not answer:
                skipped += 1
                continue

            nugget = Nugget(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text=f"Q: {question}\nA: {answer}",
                source=link.external_survey_name or f"survey-{link.external_survey_id}",
                source_location=f"response_{response.get('id', '')}",
                tags=json.dumps(["survey", link.external_survey_name or "unknown"]),
                phase="discover",
            )
            db.add(nugget)
            created += 1

    # Update link metadata
    link.response_count = (link.response_count or 0) + len(responses)
    link.last_response_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(
        "Ingested %d nuggets from %d responses (skipped %d empty answers) for link %s",
        created,
        len(responses),
        skipped,
        link.id,
    )

    return {
        "nuggets_created": created,
        "responses_processed": len(responses),
        "empty_answers_skipped": skipped,
    }
