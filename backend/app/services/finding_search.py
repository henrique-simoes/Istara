"""Project-scoped search across document context and manual findings."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag import RetrievalResult, retrieval_result_key
from app.models.finding import Fact, Insight, Nugget, Recommendation


async def search_project_findings(
    db: AsyncSession,
    project_id: str,
    query: str,
    top_k: int,
    retrieved: Sequence[RetrievalResult],
) -> list[dict[str, object]]:
    """Source evidence first, in retrieval order, then matching findings, each on its own terms.

    Retrieved chunks are raw source evidence, ranked by hybrid retrieval. Findings matched by
    substring are candidate/provisional research artifacts (model-written until the spine
    accepts them). The old merge scored every finding ``1.0`` beside fused RRF values of about
    ``0.01``, so a provisional finding always outranked the source it should be checked against.
    It also deduped by ``(text, source)``, collapsing two evidence units that share a sentence
    (F12). Now the two kinds never share a score: evidence carries its ``rank`` (and the fused
    value, labelled), findings carry ``review_status: provisional`` and no score. Search never
    promotes anything.
    """
    evidence: list[dict[str, object]] = []
    seen_evidence: set[str] = set()
    for result in retrieved:
        key = retrieval_result_key(result)
        if key in seen_evidence:
            continue
        seen_evidence.add(key)
        evidence.append(
            {
                "kind": "source_evidence",
                "rank": len(evidence) + 1,
                "text": result.text,
                "source": result.source,
                "page": result.page,
                "evidence_unit_id": result.evidence_unit_id or None,
                "fusion_score": round(result.score, 4),
            }
        )
        if len(evidence) >= top_k:
            break

    findings: list[dict[str, object]] = []
    seen_findings: set[str] = set()
    query_pattern = f"%{query}%"
    for model, finding_type in (
        (Nugget, "nugget"),
        (Fact, "fact"),
        (Insight, "insight"),
        (Recommendation, "recommendation"),
    ):
        rows = await db.execute(
            select(model)
            .where(model.project_id == project_id, model.text.ilike(query_pattern))
            .limit(top_k)
        )
        for item in rows.scalars().all():
            if item.id in seen_findings:
                continue
            seen_findings.add(item.id)
            findings.append(
                {
                    "kind": "finding",
                    "rank": None,
                    "text": item.text,
                    "source": f"finding:{finding_type}",
                    "finding_id": item.id,
                    "page": None,
                    "review_status": "provisional",
                    "score": None,
                }
            )
    return evidence + findings[:top_k]
