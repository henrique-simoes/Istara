"""ReasoningBank-style memory for agentic orchestration.

This module distills successful and failed traces into small reusable memories.
It intentionally starts with deterministic extraction and lexical retrieval so
it is safe during installation, tests, and offline production startup.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.reasoning_memory import ReasoningMemoryItem

ACTIVE_STATUS = "active"
MERGED_STATUS = "merged"
SUCCESS_OUTCOMES = {"success", "kept", "completed", "verified"}
FAILURE_OUTCOMES = {"failure", "failed", "reverted", "timeout", "rejected"}

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)['\"]?\b(password|passwd|api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b['\"]?\s*[:=]\s*['\"]?[^'\"\s,;}]+"
    ),
    re.compile(r"://[^:/\s]+:[^@\s]+@"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{48,}\b"),
]
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: Any, *, max_chars: int = 4000) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str, ensure_ascii=False)
        except TypeError:
            text = str(value)
    text = text.replace("\x00", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:max_chars]


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}


def _dedupe_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        normalized = re.sub(r"[^a-z0-9_-]+", "-", tag.lower()).strip("-")
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized[:60])
    return out


class ReasoningMemoryService:
    """Persist, retrieve, and summarize distilled reasoning memories."""

    async def record_memory(
        self,
        *,
        project_id: str = "",
        agent_id: str = "",
        source_kind: str = "manual",
        source_id: str = "",
        outcome: str = "unknown",
        title: str,
        description: str = "",
        content: str,
        tags: list[str] | None = None,
        domain: str = "",
        evidence_refs: list[dict | str] | None = None,
        judge_score: float | None = None,
        confidence: float = 0.5,
        db: AsyncSession | None = None,
    ) -> ReasoningMemoryItem:
        item = ReasoningMemoryItem(
            project_id=project_id or "",
            agent_id=agent_id or "",
            source_kind=(source_kind or "manual")[:50],
            source_id=(source_id or "")[:100],
            outcome=(outcome or "unknown")[:30],
            title=_clean_text(title, max_chars=255),
            description=_clean_text(description, max_chars=1000),
            content=_clean_text(content, max_chars=4000),
            domain=_clean_text(domain, max_chars=100),
            judge_score=judge_score,
            confidence=max(0.0, min(1.0, float(confidence))),
            status=ACTIVE_STATUS,
        )
        item.set_tags(_dedupe_tags(tags or []))
        item.set_evidence_refs(evidence_refs or [])

        if db is not None:
            db.add(item)
            await db.flush()
            return item

        async with async_session() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item

    def extract_memory_items(
        self,
        *,
        query: str,
        trajectory: Any,
        outcome: str,
        source_kind: str,
        source_id: str = "",
        tags: list[str] | None = None,
        domain: str = "",
        judge_score: float | None = None,
    ) -> list[dict[str, Any]]:
        safe_query = _clean_text(query, max_chars=500)
        safe_trace = _clean_text(trajectory, max_chars=2500)
        normalized_outcome = (outcome or "unknown").lower()
        is_success = normalized_outcome in SUCCESS_OUTCOMES
        is_failure = normalized_outcome in FAILURE_OUTCOMES

        if is_success:
            title = f"Successful {source_kind} strategy: {safe_query[:120] or source_id}"
            description = "A trace that produced a useful or accepted outcome."
            content = (
                "Reuse this strategy when the new task resembles the original context.\n\n"
                f"Original query: {safe_query}\n"
                f"Trace summary: {safe_trace}"
            )
            confidence = 0.75
        elif is_failure:
            title = f"Avoid repeated {source_kind} failure: {safe_query[:120] or source_id}"
            description = "A failed or reverted trace captured so future agents can avoid repeating it."
            content = (
                "Treat this as a cautionary memory. Check whether the same assumptions, "
                "mutation, route, or integration pattern appears again.\n\n"
                f"Original query: {safe_query}\n"
                f"Failure trace: {safe_trace}"
            )
            confidence = 0.7
        else:
            title = f"Observed {source_kind} trace: {safe_query[:120] or source_id}"
            description = "A neutral reasoning trace retained for later comparison."
            content = f"Original query: {safe_query}\nTrace summary: {safe_trace}"
            confidence = 0.55

        if judge_score is not None:
            confidence = max(confidence, min(1.0, max(0.0, judge_score)))

        return [
            {
                "source_kind": source_kind,
                "source_id": source_id,
                "outcome": normalized_outcome,
                "title": title,
                "description": description,
                "content": content,
                "tags": _dedupe_tags([source_kind, normalized_outcome, domain, *(tags or [])]),
                "domain": domain,
                "evidence_refs": [{"source_kind": source_kind, "source_id": source_id}],
                "judge_score": judge_score,
                "confidence": confidence,
            }
        ]

    async def record_trace(
        self,
        *,
        project_id: str = "",
        agent_id: str = "",
        query: str,
        trajectory: Any,
        outcome: str,
        source_kind: str,
        source_id: str = "",
        tags: list[str] | None = None,
        domain: str = "",
        judge_score: float | None = None,
    ) -> list[dict]:
        memories = self.extract_memory_items(
            query=query,
            trajectory=trajectory,
            outcome=outcome,
            source_kind=source_kind,
            source_id=source_id,
            tags=tags,
            domain=domain,
            judge_score=judge_score,
        )
        stored: list[dict] = []
        for memory in memories:
            item = await self.record_memory(
                project_id=project_id,
                agent_id=agent_id,
                **memory,
            )
            stored.append(item.to_dict())
        return stored

    async def record_task_execution(
        self,
        *,
        project_id: str,
        agent_id: str,
        task_id: str,
        task_title: str,
        task_description: str,
        skill_name: str,
        output_summary: str,
        success: bool,
        verified: bool,
        quality_score: float | None = None,
        errors: list[str] | None = None,
        validation_reason: str = "",
        trace_id: str = "",
    ) -> list[dict]:
        outcome = "success" if success and verified else "failure"
        trajectory = {
            "task_title": task_title,
            "task_description": task_description,
            "skill_name": skill_name,
            "output_summary": output_summary,
            "verified": verified,
            "quality_score": quality_score,
            "errors": errors or [],
            "validation_reason": validation_reason,
            "trace_id": trace_id,
        }
        return await self.record_trace(
            project_id=project_id,
            agent_id=agent_id,
            query=f"{task_title}\n{task_description}",
            trajectory=trajectory,
            outcome=outcome,
            source_kind="skill",
            source_id=task_id,
            tags=[skill_name, "memento"],
            domain=skill_name,
            judge_score=quality_score,
        )

    async def record_autoresearch_experiment(
        self,
        experiment: dict,
        *,
        project_id: str = "",
    ) -> list[dict]:
        status = str(experiment.get("status", "unknown")).lower()
        outcome = "success" if experiment.get("kept") else "failure"
        if status == "failed":
            outcome = "failure"
        trajectory = {
            "loop_type": experiment.get("loop_type"),
            "target_name": experiment.get("target_name"),
            "hypothesis": experiment.get("hypothesis"),
            "mutation_description": experiment.get("mutation_description"),
            "baseline_score": experiment.get("baseline_score"),
            "experiment_score": experiment.get("experiment_score"),
            "delta": experiment.get("delta"),
            "decision_reason": experiment.get("decision_reason"),
            "score_samples": experiment.get("score_samples"),
            "score_stddev": experiment.get("score_stddev"),
            "confidence_interval_95": experiment.get("confidence_interval_95"),
            "error_message": experiment.get("error_message"),
        }
        return await self.record_trace(
            project_id=project_id,
            agent_id="autoresearch",
            query=f"{experiment.get('loop_type', '')} {experiment.get('target_name', '')} {experiment.get('hypothesis', '')}",
            trajectory=trajectory,
            outcome=outcome,
            source_kind="autoresearch",
            source_id=str(experiment.get("id", "")),
            tags=[str(experiment.get("loop_type", "")), status, "karpathy-autoresearch"],
            domain=str(experiment.get("loop_type", "")),
            judge_score=experiment.get("experiment_score"),
        )

    async def retrieve(
        self,
        *,
        project_id: str = "",
        query: str,
        agent_id: str | None = None,
        source_kinds: list[str] | None = None,
        limit: int = 5,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        async def _retrieve(session: AsyncSession) -> list[dict]:
            stmt = select(ReasoningMemoryItem).where(ReasoningMemoryItem.status == ACTIVE_STATUS)
            if project_id:
                stmt = stmt.where(
                    or_(
                        ReasoningMemoryItem.project_id == project_id,
                        ReasoningMemoryItem.project_id == "",
                    )
                )
            else:
                stmt = stmt.where(ReasoningMemoryItem.project_id == "")
            if agent_id:
                stmt = stmt.where(
                    or_(
                        ReasoningMemoryItem.agent_id == agent_id,
                        ReasoningMemoryItem.agent_id == "",
                    )
                )
            if source_kinds:
                stmt = stmt.where(ReasoningMemoryItem.source_kind.in_(source_kinds))
            stmt = stmt.order_by(ReasoningMemoryItem.updated_at.desc()).limit(200)
            result = await session.execute(stmt)
            candidates = result.scalars().all()

            scored: list[tuple[float, ReasoningMemoryItem]] = []
            for item in candidates:
                haystack = " ".join(
                    [
                        item.title,
                        item.description,
                        item.content,
                        item.domain,
                        " ".join(item.get_tags()),
                    ]
                )
                candidate_tokens = _tokens(haystack)
                overlap = len(query_tokens & candidate_tokens)
                if not overlap:
                    continue
                lexical = overlap / max(1, len(query_tokens))
                outcome_boost = 0.08 if item.outcome in SUCCESS_OUTCOMES else 0.03
                score = lexical + outcome_boost + (item.confidence * 0.12)
                if item.judge_score is not None:
                    score += max(0.0, min(1.0, item.judge_score)) * 0.05
                scored.append((score, item))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            selected = scored[: max(1, min(20, limit))]
            for _, item in selected:
                item.usage_count = (item.usage_count or 0) + 1
            if selected:
                await session.commit()
            return [
                {
                    **item.to_dict(),
                    "retrieval_score": round(score, 4),
                }
                for score, item in selected
            ]

        if db is not None:
            return await _retrieve(db)
        async with async_session() as session:
            return await _retrieve(session)

    async def context_for_query(
        self,
        *,
        project_id: str = "",
        query: str,
        agent_id: str | None = None,
        source_kinds: list[str] | None = None,
        limit: int = 5,
        max_chars: int = 1500,
    ) -> str:
        memories = await self.retrieve(
            project_id=project_id,
            query=query,
            agent_id=agent_id,
            source_kinds=source_kinds,
            limit=limit,
        )
        if not memories:
            return ""
        lines = ["## Relevant Reasoning Memory"]
        for memory in memories:
            content = _clean_text(memory.get("content", ""), max_chars=500)
            lines.append(
                f"- [{memory.get('outcome')}/{memory.get('source_kind')}] "
                f"{memory.get('title')} (confidence {memory.get('confidence', 0):.2f}): {content}"
            )
        return _clean_text("\n".join(lines), max_chars=max_chars)

    async def consolidate_duplicates(self, *, project_id: str | None = None) -> dict:
        async with async_session() as session:
            stmt = select(ReasoningMemoryItem).where(ReasoningMemoryItem.status == ACTIVE_STATUS)
            if project_id is not None:
                stmt = stmt.where(ReasoningMemoryItem.project_id == project_id)
            result = await session.execute(stmt)
            items = result.scalars().all()
            grouped: dict[tuple[str, str, str], list[ReasoningMemoryItem]] = {}
            for item in items:
                key = (item.project_id, item.source_kind, item.title.strip().lower())
                grouped.setdefault(key, []).append(item)

            merged = 0
            for duplicates in grouped.values():
                if len(duplicates) < 2:
                    continue
                keeper = sorted(duplicates, key=lambda item: item.created_at)[0]
                for duplicate in duplicates[1:]:
                    keeper.confidence = max(keeper.confidence, duplicate.confidence)
                    keeper.usage_count += duplicate.usage_count
                    duplicate.status = MERGED_STATUS
                    merged += 1
            await session.commit()
            return {"merged": merged, "active": len(items) - merged}

    async def summary(self, *, project_id: str | None = None) -> dict:
        async with async_session() as session:
            stmt = select(ReasoningMemoryItem).where(ReasoningMemoryItem.status == ACTIVE_STATUS)
            if project_id is not None:
                stmt = stmt.where(ReasoningMemoryItem.project_id == project_id)
            result = await session.execute(stmt)
            items = result.scalars().all()

            source_counts = Counter(item.source_kind for item in items)
            outcome_counts = Counter(item.outcome for item in items)
            day_ago = _utcnow() - timedelta(days=1)
            recent = []
            for item in items:
                created_at = item.created_at
                if created_at and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at and created_at >= day_ago:
                    recent.append(item)

            return {
                "total": len(items),
                "source_kinds": dict(source_counts),
                "outcomes": dict(outcome_counts),
                "recent_24h": len(recent),
                "recent_failures_24h": sum(1 for item in recent if item.outcome in FAILURE_OUTCOMES),
                "recent_successes_24h": sum(1 for item in recent if item.outcome in SUCCESS_OUTCOMES),
            }

    async def list_memories(
        self,
        *,
        project_id: str | None = None,
        source_kind: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async def _list(session: AsyncSession) -> list[dict]:
            stmt = select(ReasoningMemoryItem).where(ReasoningMemoryItem.status == ACTIVE_STATUS)
            if project_id is not None:
                stmt = stmt.where(ReasoningMemoryItem.project_id == project_id)
            if source_kind:
                stmt = stmt.where(ReasoningMemoryItem.source_kind == source_kind)
            if outcome:
                stmt = stmt.where(ReasoningMemoryItem.outcome == outcome)
            stmt = stmt.order_by(ReasoningMemoryItem.updated_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [item.to_dict() for item in result.scalars().all()]

        if db is not None:
            return await _list(db)
        async with async_session() as session:
            return await _list(session)


reasoning_bank = ReasoningMemoryService()
