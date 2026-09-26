"""ReasoningBank-style memory for agentic orchestration.

This module distills successful and failed traces into small reusable memories.
It intentionally starts with deterministic extraction and lexical retrieval so
it is safe during installation, tests, and offline production startup.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_guard import ContentGuard, neutralize_boundary_markup
from app.models.database import async_session
from app.models.reasoning_memory import ReasoningMemoryItem

logger = logging.getLogger(__name__)

ACTIVE_STATUS = "active"
MERGED_STATUS = "merged"
SUCCESS_OUTCOMES = {"success", "kept", "completed", "verified"}
FAILURE_OUTCOMES = {"failure", "failed", "reverted", "timeout", "rejected"}
PROCESS_ONLY_SOURCE_KINDS = {
    "autoresearch",
    "candidate_atom",
    "codebook_revision",
    "coding_run",
    "donor_model_performance",
    "evidence_unit_extraction",
    "graph_synthesis",
    "manual",
    "qualitative_protocol",
    "reasoning_bank",
    "reconciliation",
    "report_grounding",
    "retrieval_quality",
    "skill",
    "source_ingestion",
}
REASONING_BANK_SPINE_NOTICE = (
    "ReasoningBank memories are process guidance only. They are never report "
    "evidence, never accepted Atomic Research artifacts, and must not bypass "
    "source evidence units, independent coding, reliability, reconciliation, "
    "human-approved Done tasks, or report gates."
)

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)['\"]?\b(password|passwd|api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b['\"]?\s*[:=]\s*['\"]?[^'\"\s,;}]+"
    ),
    re.compile(r"://[^:/\s]+:[^@\s]+@"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{48,}\b"),
]
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
_guard = ContentGuard()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: Any, *, max_chars: int = 4000, mark_prompt_risk: bool = True) -> str:
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
    if mark_prompt_risk:
        scan = _guard.scan_text(text)
        text = scan.cleaned_text
        if scan.threat_level in ("medium", "high"):
            threats = ", ".join(scan.threats[:3])
            text = f"[UNTRUSTED_MEMORY_CONTENT threat_level={scan.threat_level}: {threats}] {text}"
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


async def _record_reasoning_bank_telemetry(
    item: ReasoningMemoryItem,
    *,
    session: AsyncSession | None = None,
) -> None:
    if not item.project_id:
        return
    try:
        from app.core.telemetry import telemetry_recorder

        await telemetry_recorder.record_research_validity_event(
            operation="reasoning_bank.lesson",
            project_id=item.project_id,
            agent_id=item.agent_id or "",
            skill_name=item.source_kind or "",
            status="success",
            quality_score=item.confidence,
            session=session,
        )
    except Exception as exc:
        logger.debug("ReasoningBank telemetry skipped: %s", exc)


_MIN_MEMORY_BODY_CHARS = 80
_MAX_PREFILTER_TERMS = 8
_MAX_CANDIDATES = 2000


def format_memory_context(memories: list[dict], *, max_chars: int = 1500) -> str:
    """Render retrieved memories for a prompt within ``max_chars``, one closed wrapper each.

    Each memory's title and content sit INSIDE its untrusted wrapper (both come from stored traces),
    and the block is assembled line by line against the budget. It is never sliced after wrapping,
    because a slice could drop a closing tag and leave memory text outside the delimiter.
    """
    if not memories:
        return ""
    header = "\n".join(["## Relevant Reasoning Memory", REASONING_BANK_SPINE_NOTICE])
    if len(header) > max_chars:
        return ""
    lines = [header]
    used = len(header)
    for memory in memories:
        memory_id = str(memory.get("id", ""))
        prefix = (
            f"- [{_clean_text(memory.get('outcome'), max_chars=30)}/"
            f"{_clean_text(memory.get('source_kind'), max_chars=50)}] "
            f"(confidence {float(memory.get('confidence') or 0):.2f}): "
        )
        # Neutralise before measuring: escaping markup lengthens the text, and the wrapper would
        # otherwise do it after the budget check.
        body = neutralize_boundary_markup(
            _guard.sanitize_for_prompt(
                f"{_clean_text(memory.get('title'), max_chars=255)}\n"
                f"{_clean_text(memory.get('content', ''), max_chars=500)}"
            )
        )
        source = f"reasoning_memory:{memory_id}"
        overhead = len(prefix) + len(_guard.wrap_untrusted("", source=source)) + 1
        room = max_chars - used - overhead
        if room < _MIN_MEMORY_BODY_CHARS:
            break
        if len(body) > room:
            body = body[: room - 3].rstrip() + "..."
        line = prefix + _guard.wrap_untrusted(body, source=source)
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


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
        if item.source_kind in PROCESS_ONLY_SOURCE_KINDS:
            item.set_tags(_dedupe_tags([*item.get_tags(), "process-memory-only"]))
        item.set_evidence_refs(evidence_refs or [])

        if db is not None:
            db.add(item)
            await db.flush()
            await _record_reasoning_bank_telemetry(item, session=db)
            return item

        async with async_session() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
            await _record_reasoning_bank_telemetry(item)
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
            description = (
                "A failed or reverted trace captured so future agents can avoid repeating it."
            )
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
            if is_success or is_failure:
                confidence = max(confidence, min(1.0, max(0.0, judge_score)))
            else:
                # A neutral/provisional trace (self-verified output, an autoresearch candidate)
                # has no independent judgement behind its score. It stays a weak prior whatever
                # score it reports (governance contract; F3's pseudo-score fed straight in here).
                confidence = min(max(confidence, min(1.0, max(0.0, judge_score))), 0.6)

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
        db: AsyncSession | None = None,
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
                db=db,
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
        self_verified: bool | None = None,
    ) -> list[dict]:
        """``verified`` is INDEPENDENT verification (human-approved review). ``self_verified`` is
        the agent's own check. A passing self-check is recorded as a provisional trace, never as
        a success, and its score cannot raise the memory's confidence (measurement 6)."""
        if not success:
            outcome = "failure"
        elif verified:
            outcome = "success"
        elif self_verified is False:
            outcome = "failure"
        elif self_verified:
            outcome = "provisional"
            quality_score = None
        else:
            outcome = "failure"
        trajectory = {
            "task_title": task_title,
            "task_description": task_description,
            "skill_name": skill_name,
            "output_summary": output_summary,
            "verified": verified,
            "self_verified": self_verified,
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
        outcome = "candidate_proposal" if experiment.get("kept") else "failure"
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
            "research_spine_policy": experiment.get("research_spine_policy"),
            "governance_required": experiment.get("governance_required"),
            "mutation_live_after_measurement": experiment.get("mutation_live_after_measurement"),
        }
        return await self.record_trace(
            project_id=project_id,
            agent_id="autoresearch",
            query=(
                f"{experiment.get('loop_type', '')} "
                f"{experiment.get('target_name', '')} "
                f"{experiment.get('hypothesis', '')}"
            ),
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
        include_global: bool = False,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        async def _retrieve(session: AsyncSession) -> list[dict]:
            stmt = select(ReasoningMemoryItem).where(ReasoningMemoryItem.status == ACTIVE_STATUS)
            if project_id:
                if include_global:
                    stmt = stmt.where(
                        or_(
                            ReasoningMemoryItem.project_id == project_id,
                            ReasoningMemoryItem.project_id == "",
                        )
                    )
                else:
                    stmt = stmt.where(ReasoningMemoryItem.project_id == project_id)
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
            # Relevance BEFORE recency: pre-filter in SQL to rows that share a query term, then
            # cap. Taking the 200 newest rows first made any older relevant lesson unreachable
            # once 200 newer ones existed (F16).
            match_terms = sorted(query_tokens, key=len, reverse=True)[:_MAX_PREFILTER_TERMS]
            stmt = stmt.where(
                or_(
                    *[
                        column.ilike(f"%{term}%")
                        for term in match_terms
                        for column in (
                            ReasoningMemoryItem.title,
                            ReasoningMemoryItem.description,
                            ReasoningMemoryItem.content,
                            ReasoningMemoryItem.domain,
                            ReasoningMemoryItem.tags_json,
                        )
                    ]
                )
            )
            stmt = stmt.order_by(ReasoningMemoryItem.updated_at.desc()).limit(_MAX_CANDIDATES)
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
            # A query: no usage_count increment, no commit (F16: every read, including admin
            # inspection and routing, counted as a "use" and committed the caller's session).
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

    async def record_usage(self, memory_ids: list[str]) -> None:
        """Command: count one use of each memory that was actually put into a prompt."""
        ids = [memory_id for memory_id in dict.fromkeys(memory_ids) if memory_id]
        if not ids:
            return
        async with async_session() as session:
            rows = await session.execute(
                select(ReasoningMemoryItem).where(ReasoningMemoryItem.id.in_(ids))
            )
            for item in rows.scalars().all():
                item.usage_count = (item.usage_count or 0) + 1
            await session.commit()

    async def context_for_query(
        self,
        *,
        project_id: str = "",
        query: str,
        agent_id: str | None = None,
        source_kinds: list[str] | None = None,
        limit: int = 5,
        max_chars: int = 1500,
        include_global: bool = False,
        record_usage: bool = True,
    ) -> str:
        """Prompt-ready memory context. Counts one use per memory that made it into the text,
        unless ``record_usage`` is false (inspection)."""
        memories = await self.retrieve(
            project_id=project_id,
            query=query,
            agent_id=agent_id,
            source_kinds=source_kinds,
            limit=limit,
            include_global=include_global,
        )
        context = format_memory_context(memories, max_chars=max_chars)
        if record_usage and context:
            try:
                await self.record_usage(
                    [
                        str(m.get("id"))
                        for m in memories
                        if f'source="reasoning_memory:{m.get("id")}"' in context
                    ]
                )
            except Exception as exc:
                # Usage accounting is bookkeeping: it must never cost the prompt its context.
                logger.debug("ReasoningBank usage count skipped: %s", exc)
        return context

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
                    created_at = created_at.replace(tzinfo=UTC)
                if created_at and created_at >= day_ago:
                    recent.append(item)

            return {
                "total": len(items),
                "source_kinds": dict(source_counts),
                "outcomes": dict(outcome_counts),
                "recent_24h": len(recent),
                "recent_failures_24h": sum(
                    1 for item in recent if item.outcome in FAILURE_OUTCOMES
                ),
                "recent_successes_24h": sum(
                    1 for item in recent if item.outcome in SUCCESS_OUTCOMES
                ),
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
