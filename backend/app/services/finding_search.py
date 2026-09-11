"""Project-scoped search across document context and manual findings."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag import RetrievalResult
from app.models.finding import Fact, Insight, Nugget, Recommendation


async def search_project_findings(
    db: AsyncSession,
    project_id: str,
    query: str,
    top_k: int,
    retrieved: Sequence[RetrievalResult],
) -> list[dict[str, object]]:
    """Merge document-RAG results with exact manual-finding matches.

    Manual findings are deliberately returned as search results only. Their
    research-validity state is unchanged and no result is promoted by search.
    """
    results = [
        {
            "text": item.text,
            "source": item.source,
            "page": item.page,
            "score": round(item.score, 3),
        }
        for item in retrieved
    ]
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
        results.extend(
            {
                "text": item.text,
                "source": f"finding:{finding_type}",
                "page": None,
                "score": 1.0,
            }
            for item in rows.scalars().all()
        )

    unique_results = list({(item["text"], item["source"]): item for item in results}.values())
    unique_results.sort(key=lambda item: item["score"], reverse=True)
    return unique_results[:top_k]
