"""Export a research report with the evidence behind every claim (D-9, R1).

A report could only be read inside Istara; researchers share reports as documents. Every exported
finding carries its evidence trail down to the source: a nugget cites the evidence units it is
grounded in (the quote, its document and location, and the coding state of that unit); a fact
cites its nuggets' evidence, an insight its facts', a recommendation its insights'. The same trail
measures R1: the share of a report's claims that reach an exact source span.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

KIND_ORDER = ("recommendation", "insight", "fact", "nugget")
KIND_TITLES = {
    "recommendation": "Recommendations",
    "insight": "Insights",
    "fact": "Facts",
    "nugget": "Evidence nuggets",
}


@dataclass
class Citation:
    quote: str
    document: str
    location: str
    evidence_unit_id: str
    coding: str

    @property
    def exact_span(self) -> bool:
        return bool(self.document)


@dataclass
class TracedFinding:
    kind: str
    id: str
    text: str
    citations: list[Citation] = field(default_factory=list)

    @property
    def traced(self) -> bool:
        return any(c.exact_span for c in self.citations)


def _ids(value) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (json.JSONDecodeError, TypeError):
        return []
    return [str(v) for v in parsed if v] if isinstance(parsed, list) else []


async def _nugget_citations(db: AsyncSession, project_id: str, nugget_ids: list[str]) -> dict:
    from app.models.code_application import CodeApplication
    from app.models.document import Document
    from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge
    from app.services.research_validity_reconciliation import (
        _is_reconciled_code_application,
        _is_unresolved_code_application,
    )

    if not nugget_ids:
        return {}
    edges = (
        (
            await db.execute(
                select(ResearchEvidenceEdge).where(
                    ResearchEvidenceEdge.project_id == project_id,
                    ResearchEvidenceEdge.source_type == "nugget",
                    ResearchEvidenceEdge.relation == "grounded_in",
                    ResearchEvidenceEdge.source_id.in_(nugget_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    unit_ids = {e.evidence_unit_id for e in edges if e.evidence_unit_id}
    units = {
        u.id: u
        for u in (
            await db.execute(
                select(EvidenceUnit).where(
                    EvidenceUnit.project_id == project_id, EvidenceUnit.id.in_(unit_ids)
                )
            )
        )
        .scalars()
        .all()
    }
    doc_ids = {u.source_document_id for u in units.values() if u.source_document_id}
    docs = {
        d.id: d
        for d in (await db.execute(select(Document).where(Document.id.in_(doc_ids))))
        .scalars()
        .all()
    }
    codes = (
        (
            await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.evidence_unit_id.in_(unit_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    coding: dict[str, str] = {}
    for row in codes:
        state = (
            "accepted"
            if _is_reconciled_code_application(row)
            else "needs review"
            if _is_unresolved_code_application(row)
            else "rejected"
        )
        if coding.get(row.evidence_unit_id) != "accepted":
            coding[row.evidence_unit_id] = state
    by_nugget: dict[str, list[Citation]] = {}
    for edge in edges:
        unit = units.get(edge.evidence_unit_id or "")
        if unit is None:
            continue
        document = docs.get(unit.source_document_id or "")
        by_nugget.setdefault(edge.source_id, []).append(
            Citation(
                quote=unit.source_text or "",
                document=(document.file_name or document.title) if document else "",
                location=unit.source_location or "",
                evidence_unit_id=unit.id,
                coding=coding.get(unit.id, "not coded"),
            )
        )
    return by_nugget


async def trace_report(db: AsyncSession, report) -> list[TracedFinding]:
    """Every finding the report cites, with its evidence trail to the source."""
    from app.models.finding import Fact, Insight, Nugget, Recommendation

    wanted = set(_ids(report.finding_ids_json))
    project_id = report.project_id
    rows = {}
    for model, kind in (
        (Nugget, "nugget"),
        (Fact, "fact"),
        (Insight, "insight"),
        (Recommendation, "recommendation"),
    ):
        for row in (
            await db.execute(select(model).where(model.project_id == project_id))
        ).scalars():
            rows[row.id] = (kind, row)

    def parents(kind: str, row) -> list[str]:
        field_name = {
            "fact": "nugget_ids",
            "insight": "fact_ids",
            "recommendation": "insight_ids",
        }.get(kind)
        return _ids(getattr(row, field_name, "[]")) if field_name else []

    def nuggets_under(finding_id: str, seen: set[str]) -> set[str]:
        if finding_id in seen or finding_id not in rows:
            return set()
        seen.add(finding_id)
        kind, row = rows[finding_id]
        if kind == "nugget":
            return {finding_id}
        found: set[str] = set()
        for parent in parents(kind, row):
            found |= nuggets_under(parent, seen)
        return found

    per_finding = {fid: nuggets_under(fid, set()) for fid in wanted if fid in rows}
    all_nuggets = sorted({n for ns in per_finding.values() for n in ns})
    citations = await _nugget_citations(db, project_id, all_nuggets)
    traced = []
    for fid, nugget_ids in per_finding.items():
        kind, row = rows[fid]
        cited = [c for n in sorted(nugget_ids) for c in citations.get(n, [])]
        traced.append(TracedFinding(kind=kind, id=fid, text=row.text or "", citations=cited))
    traced.sort(key=lambda f: (KIND_ORDER.index(f.kind), f.text))
    return traced


def traceability(findings: list[TracedFinding]) -> dict:
    """R1: claims that reach an exact source span."""
    total = len(findings)
    traced = sum(1 for f in findings if f.traced)
    return {
        "claims": total,
        "traced_to_source_span": traced,
        "share": round(traced / total, 4) if total else None,
    }


def _citation_line(c: Citation) -> str:
    where = f"{c.document}" + (f", {c.location.split('#', 1)[-1]}" if "#" in c.location else "")
    return f"“{' '.join(c.quote.split())}” — {where or 'no source document'} (coding: {c.coding})"


def render_markdown(report, findings: list[TracedFinding]) -> str:
    stats = traceability(findings)
    lines = [f"# {report.title}", ""]
    lines.append(
        f"Status: {report.status} · version {report.version} · "
        f"{stats['traced_to_source_span']} of {stats['claims']} findings traced to a source span"
    )
    if report.executive_summary:
        lines += ["", "## Executive summary", "", report.executive_summary.strip()]
    content = json.loads(report.content_json or "{}") if report.content_json else {}
    full_document = content.get("full_document") if isinstance(content, dict) else ""
    if full_document:
        lines += ["", str(full_document).strip()]
    for kind in KIND_ORDER:
        group = [f for f in findings if f.kind == kind]
        if not group:
            continue
        lines += ["", f"## {KIND_TITLES[kind]}", ""]
        for index, finding in enumerate(group, start=1):
            lines.append(f"{index}. {' '.join(finding.text.split())}")
            for citation in finding.citations[:6]:
                lines.append(f"   - {_citation_line(citation)}")
            if not finding.citations:
                lines.append("   - No evidence trail: this finding is not traced to a source.")
    return "\n".join(lines) + "\n"


def render_csv(findings: list[TracedFinding]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "finding_type",
            "finding_id",
            "finding",
            "quote",
            "document",
            "location",
            "evidence_unit_id",
            "coding",
        ]
    )
    for finding in findings:
        if not finding.citations:
            writer.writerow([finding.kind, finding.id, finding.text, "", "", "", "", ""])
        for c in finding.citations:
            writer.writerow(
                [
                    finding.kind,
                    finding.id,
                    finding.text,
                    c.quote,
                    c.document,
                    c.location,
                    c.evidence_unit_id,
                    c.coding,
                ]
            )
    return buffer.getvalue()


def render_docx(report, findings: list[TracedFinding]) -> bytes:
    from docx import Document as DocxDocument

    stats = traceability(findings)
    doc = DocxDocument()
    doc.add_heading(report.title, level=0)
    doc.add_paragraph(
        f"Status: {report.status} · version {report.version} · "
        f"{stats['traced_to_source_span']} of {stats['claims']} findings traced to a source span"
    )
    if report.executive_summary:
        doc.add_heading("Executive summary", level=1)
        doc.add_paragraph(report.executive_summary.strip())
    for kind in KIND_ORDER:
        group = [f for f in findings if f.kind == kind]
        if not group:
            continue
        doc.add_heading(KIND_TITLES[kind], level=1)
        for finding in group:
            doc.add_paragraph(" ".join(finding.text.split()), style="List Number")
            for citation in finding.citations[:6]:
                doc.add_paragraph(_citation_line(citation), style="List Bullet 2")
            if not finding.citations:
                doc.add_paragraph(
                    "No evidence trail: not traced to a source.", style="List Bullet 2"
                )
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
