"""Graph quality measurements (plan `docs/build-stream/2026-09-26-graph-quality-measurement.md`).

G1 · Evidence-graph traceability. For one project, walk every recommendation, insight and fact down
to the nuggets it rests on, and every nugget to the raw source text it claims to quote:

* **span fidelity** — a nugget's text (whitespace-normalised) appears verbatim in a project
  document; a code application's quote appears verbatim in its evidence unit;
* **grounding** — a nugget has a ``grounded_in`` edge to an existing evidence unit whose text is
  itself verbatim in a project document;
* **link validity** — every id an artifact names (``fact.nugget_ids`` and so on) and every edge
  endpoint exists in the same project;
* **chain completeness** — a fact, insight or recommendation reaches at least one faithful nugget;
* **cycles** in the edge graph.

Pure reads: nothing is written. Seeded faults are built by the tests
(``tests/test_graph_eval_trace.py``) through the same row shapes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from app.evals.stats import bootstrap_ci

_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Case-folded text with every whitespace run collapsed, for verbatim containment."""
    return _WS.sub(" ", str(text or "")).strip().casefold()


def _ids(raw: object) -> list[str]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else []
        except (json.JSONDecodeError, TypeError):
            raw = [raw]
    if isinstance(raw, (list, tuple, set)):
        return [str(v) for v in raw if v]
    return [str(raw)] if raw else []


def _share(flags: Sequence[bool]) -> dict[str, Any] | None:
    if not flags:
        return None
    values = [1.0 if f else 0.0 for f in flags]
    low, high = bootstrap_ci(values)
    return {
        "share": round(sum(values) / len(values), 4),
        "ci95_low": round(low, 4),
        "ci95_high": round(high, 4),
        "n": len(values),
    }


def find_cycles(edges: Iterable[tuple[str, str]]) -> int:
    """Number of back edges met in a depth-first walk (0 means the graph is acyclic)."""
    graph: dict[str, list[str]] = defaultdict(list)
    for source, target in edges:
        graph[source].append(target)
    state: dict[str, int] = {}
    back = 0
    for root in list(graph):
        if root in state:
            continue
        stack = [(root, iter(graph[root]))]
        state[root] = 1
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
            elif state.get(child) == 1:
                back += 1
            elif child not in state:
                state[child] = 1
                stack.append((child, iter(graph.get(child, []))))
    return back


class GraphSnapshot:
    """The rows G1 reads for one project, indexed by id."""

    def __init__(self, rows: dict[str, list[Any]]) -> None:
        self.documents = rows["documents"]
        self.units = {u.id: u for u in rows["units"]}
        self.nuggets = {n.id: n for n in rows["nuggets"]}
        self.facts = {f.id: f for f in rows["facts"]}
        self.insights = {i.id: i for i in rows["insights"]}
        self.recommendations = {r.id: r for r in rows["recommendations"]}
        self.code_applications = rows["code_applications"]
        self.edges = rows["edges"]
        self.corpus = [normalise(d.content_text) for d in self.documents if d.content_text]

    def in_corpus(self, text: str) -> bool:
        needle = normalise(text)
        return bool(needle) and any(needle in doc for doc in self.corpus)

    def known(self, kind: str, ident: str) -> bool:
        table = {
            "evidence_unit": self.units,
            "nugget": self.nuggets,
            "fact": self.facts,
            "insight": self.insights,
            "recommendation": self.recommendations,
        }.get(kind)
        if kind == "document":
            return any(d.id == ident for d in self.documents)
        return table is None or ident in table


def _grounded_nuggets(snap: GraphSnapshot) -> dict[str, bool]:
    grounded: dict[str, bool] = {nid: False for nid in snap.nuggets}
    for edge in snap.edges:
        if edge.relation != "grounded_in" or edge.source_id not in grounded:
            continue
        unit = snap.units.get(edge.target_id)
        if unit is not None and snap.in_corpus(unit.source_text):
            grounded[edge.source_id] = True
    return grounded


def _reaches(ids: list[str], ok: dict[str, bool]) -> bool:
    return any(ok.get(i, False) for i in ids)


def _level(parents: dict[str, Any], field: str, children_ok: dict[str, bool], children: dict):
    """Per-parent: (reaches a faithful child, share of named ids that exist)."""
    reach, links = {}, []
    for pid, parent in parents.items():
        named = _ids(getattr(parent, field, ""))
        links.extend(i in children for i in named)
        reach[pid] = _reaches(named, children_ok)
    return reach, links


def _quote_in_unit(snap: GraphSnapshot, application: Any) -> bool:
    """A code application's quoted span is a verbatim part of its evidence unit."""
    unit = snap.units.get(application.evidence_unit_id)
    quote = normalise(application.source_text)
    return bool(quote) and unit is not None and quote in normalise(unit.source_text)


def _edge_validity(snap: GraphSnapshot, project_id: str) -> list[bool]:
    return [
        e.project_id == project_id
        and snap.known(e.source_type, e.source_id)
        and snap.known(e.target_type, e.target_id)
        for e in snap.edges
    ]


def trace_metrics(snap: GraphSnapshot, project_id: str) -> dict[str, Any]:
    """G1 over one project's snapshot."""
    fidelity = {nid: snap.in_corpus(n.text) for nid, n in snap.nuggets.items()}
    grounded = _grounded_nuggets(snap)
    faithful = {nid: fidelity[nid] or grounded[nid] for nid in snap.nuggets}
    fact_ok, fact_links = _level(snap.facts, "nugget_ids", faithful, snap.nuggets)
    insight_ok, insight_links = _level(snap.insights, "fact_ids", fact_ok, snap.facts)
    rec_ok, rec_links = _level(snap.recommendations, "insight_ids", insight_ok, snap.insights)
    quotes = [_quote_in_unit(snap, ca) for ca in snap.code_applications]
    return {
        "counts": {
            "documents": len(snap.documents),
            "evidence_units": len(snap.units),
            "nuggets": len(snap.nuggets),
            "facts": len(snap.facts),
            "insights": len(snap.insights),
            "recommendations": len(snap.recommendations),
            "code_applications": len(snap.code_applications),
            "edges": len(snap.edges),
        },
        "nugget_span_fidelity": _share(list(fidelity.values())),
        "nugget_grounded": _share(list(grounded.values())),
        "code_application_quote_fidelity": _share(quotes),
        "link_validity": _share(fact_links + insight_links + rec_links),
        "edge_validity": _share(_edge_validity(snap, project_id)),
        "chain_completeness": {
            "facts": _share(list(fact_ok.values())),
            "insights": _share(list(insight_ok.values())),
            "recommendations": _share(list(rec_ok.values())),
        },
        "cycles": find_cycles((e.source_id, e.target_id) for e in snap.edges),
    }


async def load_snapshot(db, project_id: str) -> GraphSnapshot:
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.document import Document
    from app.models.finding import Fact, Insight, Nugget, Recommendation
    from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge

    async def rows(model, *, scoped: bool = True):
        query = select(model)
        if scoped:
            query = query.where(model.project_id == project_id)
        return list((await db.execute(query)).scalars().all())

    snapshot = {
        "documents": await rows(Document),
        "units": await rows(EvidenceUnit),
        "nuggets": await rows(Nugget),
        "facts": await rows(Fact),
        "insights": await rows(Insight),
        "recommendations": await rows(Recommendation),
        "code_applications": await rows(CodeApplication),
        # All edges that touch the project's ids, not only those stamped with its id: an edge
        # written under another project is exactly what edge validity must see.
        "edges": await rows(ResearchEvidenceEdge, scoped=False),
    }
    own = {
        o.id
        for key in ("documents", "units", "nuggets", "facts", "insights", "recommendations")
        for o in snapshot[key]
    }
    snapshot["edges"] = [
        e
        for e in snapshot["edges"]
        if e.project_id == project_id or e.source_id in own or e.target_id in own
    ]
    return GraphSnapshot(snapshot)


async def run_trace(project_id: str) -> dict[str, Any]:
    from app.models.database import async_session

    async with async_session() as db:
        snap = await load_snapshot(db, project_id)
    return {
        "measurement": "G1 evidence-graph traceability",
        "project_id": project_id,
        **trace_metrics(snap, project_id),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    trace = sub.add_parser("trace", help="G1: evidence-graph traceability for one project")
    trace.add_argument("--project-id", required=True)
    trace.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    from app.models.database import register_models

    register_models()
    report = asyncio.run(run_trace(args.project_id))
    text = json.dumps(report, indent=1, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text if not args.out else f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
