"""Design evidence helpers for the Interfaces research-to-design pipeline."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_screen import DesignBrief, DesignScreen
from app.models.finding import Insight, Recommendation
from app.services.laws_of_ux_service import laws_service


@dataclass(frozen=True)
class DesignSeedFinding:
    """Resolved finding allowed to seed design generation."""

    id: str
    type: str
    text: str
    phase: str
    confidence: float | None = None
    impact: str | None = None
    priority: str | None = None
    effort: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "phase": self.phase,
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.impact:
            data["impact"] = self.impact
        if self.priority:
            data["priority"] = self.priority
        if self.effort:
            data["effort"] = self.effort
        return data


def parse_json_list(raw: Any) -> list[Any]:
    """Parse a JSON-encoded list without letting corrupt DB rows break views."""
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return value if isinstance(value, list) else []


def normalize_id_list(raw_ids: list[str] | tuple[str, ...] | None, *, max_items: int = 10) -> list[str]:
    """Return unique, trimmed IDs in caller order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_ids or []:
        if not isinstance(raw, str):
            continue
        item = raw.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
        if len(normalized) >= max_items:
            break
    return normalized


async def resolve_seed_findings(
    db: AsyncSession,
    project_id: str,
    seed_ids: list[str] | tuple[str, ...] | None,
    *,
    max_items: int = 10,
) -> tuple[list[DesignSeedFinding], list[str]]:
    """Resolve seed finding IDs to project-local insights/recommendations."""
    normalized = normalize_id_list(seed_ids, max_items=max_items)
    if not normalized:
        return [], []

    by_id: dict[str, DesignSeedFinding] = {}

    insight_rows = await db.execute(
        select(Insight).where(Insight.project_id == project_id, Insight.id.in_(normalized))
    )
    for insight in insight_rows.scalars().all():
        by_id[insight.id] = DesignSeedFinding(
            id=insight.id,
            type="insight",
            text=insight.text,
            phase=insight.phase,
            confidence=insight.confidence,
            impact=insight.impact,
        )

    rec_rows = await db.execute(
        select(Recommendation).where(
            Recommendation.project_id == project_id,
            Recommendation.id.in_(normalized),
        )
    )
    for rec in rec_rows.scalars().all():
        by_id[rec.id] = DesignSeedFinding(
            id=rec.id,
            type="recommendation",
            text=rec.text,
            phase=rec.phase,
            priority=rec.priority,
            effort=rec.effort,
        )

    resolved = [by_id[item] for item in normalized if item in by_id]
    missing = [item for item in normalized if item not in by_id]
    return resolved, missing


def build_seeded_prompt(prompt: str, findings: list[DesignSeedFinding]) -> str:
    """Prepend research evidence to a screen-generation prompt."""
    if not findings:
        return prompt
    lines = [
        f"- [{finding.type}:{finding.id}] {finding.text}"
        for finding in findings
    ]
    return "Based on these project-local research findings:\n" + "\n".join(lines) + f"\n\nDesign: {prompt}"


def _first_law_match(text: str) -> dict[str, Any] | None:
    matches = laws_service.match_text(text, top_k=1)
    if not matches:
        return None
    law_id, score = matches[0]
    if score < 0.08:
        return None
    law = laws_service.get_by_id(law_id) or {}
    return {
        "id": law_id,
        "name": law.get("name", law_id),
        "score": round(score, 3),
    }


async def hydrate_design_brief(db: AsyncSession, brief: DesignBrief) -> dict[str, Any]:
    """Serialize a brief with UI-ready source evidence and recommendations."""
    data = brief.to_dict()
    insight_ids = normalize_id_list(parse_json_list(brief.source_insight_ids), max_items=50)
    rec_ids = normalize_id_list(parse_json_list(brief.source_recommendation_ids), max_items=50)

    source_findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    ux_laws: dict[str, str] = {}

    if insight_ids:
        rows = await db.execute(
            select(Insight).where(Insight.project_id == brief.project_id, Insight.id.in_(insight_ids))
        )
        insight_by_id = {item.id: item for item in rows.scalars().all()}
        for iid in insight_ids:
            insight = insight_by_id.get(iid)
            if insight:
                source_findings.append(
                    {
                        "id": insight.id,
                        "type": "insight",
                        "text": insight.text,
                        "phase": insight.phase,
                        "confidence": insight.confidence,
                        "impact": insight.impact,
                    }
                )

    if rec_ids:
        rows = await db.execute(
            select(Recommendation).where(
                Recommendation.project_id == brief.project_id,
                Recommendation.id.in_(rec_ids),
            )
        )
        rec_by_id = {item.id: item for item in rows.scalars().all()}
        for rid in rec_ids:
            rec = rec_by_id.get(rid)
            if not rec:
                continue
            law = _first_law_match(rec.text)
            if law:
                ux_laws[law["id"]] = law["name"]
            rec_payload: dict[str, Any] = {
                "id": rec.id,
                "type": "recommendation",
                "text": rec.text,
                "phase": rec.phase,
                "priority": rec.priority,
                "effort": rec.effort,
            }
            if law:
                rec_payload["law"] = law["name"]
                rec_payload["law_id"] = law["id"]
            recommendations.append(rec_payload)
            source_findings.append(rec_payload)

    data["source_findings"] = source_findings
    data["recommendations"] = recommendations
    data["ux_laws"] = list(ux_laws.values())
    return data


async def resolve_screen_source_findings(
    db: AsyncSession,
    screen: DesignScreen,
    *,
    max_items: int = 20,
) -> list[dict[str, Any]]:
    """Resolve a screen's source_findings JSON to UI/API payloads."""
    ids = normalize_id_list(parse_json_list(screen.source_findings), max_items=max_items)
    if not ids:
        return []
    resolved, _missing = await resolve_seed_findings(
        db,
        screen.project_id,
        ids,
        max_items=max_items,
    )
    return [finding.to_dict() for finding in resolved]


def build_dev_spec_content(screen: DesignScreen, source_findings: list[dict[str, Any]]) -> str:
    """Build deterministic markdown for developer handoff."""
    lines = [
        f"# Developer Spec: {screen.title}",
        "",
        f"- Screen ID: {screen.id}",
        f"- Device: {screen.device_type}",
        f"- Status: {screen.status}",
    ]
    if screen.parent_screen_id:
        lines.append(f"- Parent screen: {screen.parent_screen_id}")
    if screen.variant_type:
        lines.append(f"- Variant type: {screen.variant_type}")
    if screen.figma_file_key:
        lines.append(f"- Figma file key: {screen.figma_file_key}")
    if screen.figma_node_id:
        lines.append(f"- Figma node ID: {screen.figma_node_id}")

    if screen.description:
        lines.extend(["", "## Description", screen.description])
    if screen.prompt:
        lines.extend(["", "## Prompt", screen.prompt])
    if source_findings:
        lines.extend(["", "## Source Findings"])
        for finding in source_findings:
            label = finding.get("type", "finding")
            fid = finding.get("id", "")
            text = finding.get("text", "")
            lines.append(f"- [{label}:{fid}] {text}")
    if screen.html_content:
        lines.extend(["", "## HTML", "```html", screen.html_content, "```"])
    return "\n".join(lines)


def build_figma_import_html(
    *,
    file_name: str,
    file_key: str,
    node_id: str | None,
    components: list[dict[str, Any]],
    styles: list[dict[str, Any]],
) -> str:
    """Create a static, sandbox-safe HTML summary for imported Figma context."""
    safe_name = html.escape(file_name or "Untitled Figma file")
    safe_key = html.escape(file_key)
    safe_node = html.escape(node_id or "root")
    component_items = "\n".join(
        f"<li><strong>{html.escape(str(c.get('name', 'Unnamed')))}</strong>"
        f"<span>{html.escape(str(c.get('description', '')))}</span></li>"
        for c in components[:20]
    )
    style_items = "\n".join(
        f"<li><strong>{html.escape(str(s.get('name', 'Unnamed')))}</strong>"
        f"<span>{html.escape(str(s.get('style_type', '')))}</span></li>"
        for s in styles[:20]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{safe_name}</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; padding: 32px; color: #111827; background: #f8fafc; }}
    main {{ max-width: 960px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    section {{ margin-top: 24px; }}
    ul {{ display: grid; gap: 8px; padding: 0; list-style: none; }}
    li {{ display: flex; justify-content: space-between; gap: 16px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 6px; }}
    span {{ color: #64748b; }}
  </style>
</head>
<body>
  <main>
    <h1>{safe_name}</h1>
    <p>Imported from Figma file <strong>{safe_key}</strong>, node <strong>{safe_node}</strong>.</p>
    <section>
      <h2>Components</h2>
      <ul>{component_items or "<li><span>No components returned.</span></li>"}</ul>
    </section>
    <section>
      <h2>Styles</h2>
      <ul>{style_items or "<li><span>No styles returned.</span></li>"}</ul>
    </section>
  </main>
</body>
</html>"""
