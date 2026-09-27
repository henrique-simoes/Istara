"""SK2/SK3: does a skill read the whole study and find what is in it?

Professional-readiness review (2026-09-26), DEC-8. Runs a skill through the product route
(``POST /api/skills/{name}/execute``) on the Harbor Ledger interviews already uploaded to a project,
with the serving model pinned through ``POST /api/settings/pi-default``, then grades the nuggets the
run stored against the corpus generator's planted theme quotes (``harbor-ledger-qrels-thematic``):

  theme recall  themes (of 10) with at least one nugget sharing >= 40 contiguous characters
                (case and whitespace aside) with one of that theme's planted quotes
  grounded      share of the run's nuggets stored as exact source spans (D-12)
  coverage      the skill's own ``input_coverage.json`` when it reports one

Run inside the backend container, which owns the database:

    python -m app.evals.skill_theme_eval --project <id> --skill user-interviews \\
        --endpoint pi-deepseek-flash --label after --qrels /app/data/eval/thematic.json
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import re
import time
from datetime import UTC, datetime

MIN_OVERLAP = 40
BASE = "http://127.0.0.1:8000"


def normalise(text: str) -> str:
    text = str(text or "").casefold().replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def longest_shared(a: str, b: str) -> int:
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return matcher.find_longest_match(0, len(a), 0, len(b)).size


def theme_quotes(qrels_path: str) -> dict[str, list[str]]:
    data = json.load(open(qrels_path, encoding="utf-8"))
    themes: dict[str, set[str]] = {}
    for question in data["questions"]:
        themes.setdefault(question["theme"], set()).update(question["targets"])
    return {theme: sorted(quotes) for theme, quotes in themes.items()}


def theme_recall(nugget_texts: list[str], themes: dict[str, list[str]]) -> dict:
    normalised = [normalise(t) for t in nugget_texts if t]
    hit_themes = {}
    for theme, quotes in themes.items():
        for quote in (normalise(q) for q in quotes):
            best = next((n for n in normalised if longest_shared(n, quote) >= MIN_OVERLAP), None)
            if best is not None:
                hit_themes[theme] = best[:120]
                break
    return {
        "themes": len(themes),
        "themes_found": len(hit_themes),
        "recall": round(len(hit_themes) / len(themes), 4) if themes else None,
        "per_theme": {t: (t in hit_themes) for t in sorted(themes)},
    }


async def _documents(project_id: str, prefix: str) -> list[tuple[str, str]]:
    from sqlalchemy import select

    from app.models.database import async_session
    from app.models.document import Document

    async with async_session() as db:
        rows = (
            await db.execute(
                select(Document.file_name, Document.file_path).where(
                    Document.project_id == project_id
                )
            )
        ).all()
    return sorted((n, p) for n, p in rows if n and n.startswith(prefix) and p)


async def _run_findings(project_id: str, since: datetime) -> dict:
    from sqlalchemy import func, select

    from app.models.agentic_usage import AgenticUsage
    from app.models.database import async_session
    from app.models.finding import Fact, Insight, Nugget, Recommendation
    from app.models.research_validity import EvidenceUnit

    async with async_session() as db:
        nuggets = (
            (
                await db.execute(
                    select(Nugget).where(
                        Nugget.project_id == project_id, Nugget.created_at >= since
                    )
                )
            )
            .scalars()
            .all()
        )
        counts = {}
        for model, name in (
            (Fact, "facts"),
            (Insight, "insights"),
            (Recommendation, "recommendations"),
        ):
            counts[name] = await db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.project_id == project_id, model.created_at >= since)
            )
        grounded = 0
        for nugget in nuggets:
            unit = await db.scalar(
                select(EvidenceUnit.id).where(
                    EvidenceUnit.project_id == project_id,
                    EvidenceUnit.source_id.like(f"%nugget:{nugget.id}"),
                    EvidenceUnit.unit_type == "source_span",
                    EvidenceUnit.source_document_id.is_not(None),
                )
            )
            grounded += 1 if unit else 0
        cost = await db.scalar(
            select(func.coalesce(func.sum(AgenticUsage.cost_usd), 0.0)).where(
                AgenticUsage.project_id == project_id, AgenticUsage.created_at >= since
            )
        )
        calls = await db.scalar(
            select(func.count())
            .select_from(AgenticUsage)
            .where(AgenticUsage.project_id == project_id, AgenticUsage.created_at >= since)
        )
    return {
        "nugget_texts": [n.text or "" for n in nuggets],
        "nuggets": len(nuggets),
        "grounded": grounded,
        "cost_usd": round(float(cost or 0.0), 4),
        "model_calls": int(calls or 0),
        **counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--qrels", required=True)
    parser.add_argument("--prefix", default="HB-IV")
    parser.add_argument("--timeout", type=float, default=7200)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    import httpx

    import app.core.agentic  # noqa: F401  (import-order guard)
    from app.models.database import register_models

    register_models()
    docs = asyncio.run(_documents(args.project, args.prefix))
    themes = theme_quotes(args.qrels)
    with httpx.Client(base_url=BASE, timeout=args.timeout + 60) as client:
        pinned = client.post("/api/settings/pi-default", json={"endpoint_id": args.endpoint})
        since = datetime.now(UTC)
        started = time.monotonic()
        response = client.post(
            f"/api/skills/{args.skill}/execute",
            json={
                "project_id": args.project,
                "files": [p for _, p in docs],
                "timeout_seconds": args.timeout,
            },
        )
        elapsed = round(time.monotonic() - started, 1)
    body = (
        response.json()
        if response.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    found = asyncio.run(_run_findings(args.project, since))
    report = {
        "measure": "SK2/SK3 skill theme recall (professional-readiness review, DEC-8)",
        "label": args.label,
        "skill": args.skill,
        "endpoint": args.endpoint,
        "endpoint_pinned": pinned.status_code,
        "files": len(docs),
        "status": response.status_code,
        "success": body.get("success"),
        "summary": body.get("summary"),
        "errors": body.get("errors", [])[:5],
        "elapsed_s": elapsed,
        "theme_recall": theme_recall(found.pop("nugget_texts"), themes),
        **found,
    }
    text = json.dumps(report, indent=2)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
