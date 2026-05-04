"""System-wide improvement governance for Istara's self-evolving loops."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.improvement_governance import ImprovementProposal

STATUS = {
    "draft": "draft",
    "proposed": "proposed",
    "approved": "approved",
    "applied": "applied",
    "rejected": "rejected",
    "reverted": "reverted",
    "quarantined": "quarantined",
}
POLICY = {
    "auto": "auto_apply",
    "approval": "approval_required",
    "admin": "admin_required",
}
RISK = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}
SURFACES = {
    "auto": {"memory", "telemetry", "evaluation", "documentation"},
    "admin": {"backend_code", "integrations", "mcp", "compute", "security", "connection_strings"},
    "behavior": {
        "prompts",
        "configs",
        "skills",
        "agents",
        "ui",
        "backend_code",
        "integrations",
        "mcp",
        "compute",
        "security",
        "orchestration",
        "connection_strings",
    },
}

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)['\"]?\b(password|passwd|api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b['\"]?\s*[:=]\s*['\"]?[^'\"\s,;}]+"
    ),
    re.compile(r"://[^:/\s]+:[^@\s]+@"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{48,}\b"),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_string(value: Any, *, max_chars: int = 4000) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\x00", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:max_chars]


def _clean_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = _clean_string(key, max_chars=120)
            if re.search(r"(?i)(password|passwd|api[_-]?key|secret|token)", safe_key):
                cleaned[safe_key] = "[REDACTED]"
            else:
                cleaned[safe_key] = _clean_payload(item, depth=depth + 1)
        return cleaned
    if isinstance(value, list):
        return [_clean_payload(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, tuple):
        return [_clean_payload(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, (str, bytes)):
        return _clean_string(value.decode("utf-8", "ignore") if isinstance(value, bytes) else value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clean_string(value)


def _normalize_surface(surface: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", surface.strip().lower()).strip("_")
    aliases = {
        "backend": "backend_code",
        "code": "backend_code",
        "integration": "integrations",
        "llm": "compute",
        "llms": "compute",
        "reasoning_bank": "reasoning",
        "transcripts": "transcription",
        "audio": "transcription",
        "whatsapp": "channels",
        "telegram": "channels",
        "aura": "integrations",
    }
    return aliases.get(normalized, normalized)


def _normalize_surfaces(surfaces: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for surface in surfaces or []:
        normalized = _normalize_surface(str(surface))
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out or ["evaluation"]


class ImprovementGovernanceService:
    """Create, evaluate, approve, apply, and revert improvement proposals."""

    async def _register_archive_variant(self, proposal: ImprovementProposal, session: AsyncSession) -> None:
        try:
            from app.core.dgmh_archive import dgmh_archive

            await dgmh_archive.register_from_governance_proposal(proposal, db=session)
        except Exception:
            pass

    async def _sync_archive_status(
        self,
        proposal: ImprovementProposal,
        session: AsyncSession,
        *,
        evidence: dict | None = None,
    ) -> None:
        try:
            from app.core.dgmh_archive import dgmh_archive

            await dgmh_archive.update_status_for_governance(
                proposal.id,
                proposal.status,
                evidence=evidence or {},
                db=session,
            )
        except Exception:
            pass

    def classify_policy(
        self,
        *,
        affected_surfaces: list[str] | None = None,
        source_system: str = "manual",
        risk_level: str | None = None,
        proposed_change: dict | None = None,
    ) -> dict:
        surfaces = set(_normalize_surfaces(affected_surfaces))
        normalized_risk = (risk_level or self.infer_risk_level(list(surfaces))).lower()
        if normalized_risk not in set(RISK.values()):
            normalized_risk = RISK["medium"]

        if surfaces <= SURFACES["auto"] and normalized_risk == RISK["low"]:
            policy = POLICY["auto"]
        elif surfaces & SURFACES["admin"] or normalized_risk in {RISK["high"], RISK["critical"]}:
            policy = POLICY["admin"]
        elif surfaces & SURFACES["behavior"]:
            policy = POLICY["approval"]
        else:
            policy = POLICY["approval"]

        return {
            "source_system": _clean_string(source_system, max_chars=60) or "manual",
            "affected_surfaces": sorted(surfaces),
            "risk_level": normalized_risk,
            "approval_policy": policy,
            "requires_human_approval": policy != POLICY["auto"],
            "auto_apply_allowed": policy == POLICY["auto"],
            "behavioral_change": bool(surfaces & SURFACES["behavior"]),
            "proposed_change": _clean_payload(proposed_change or {}),
        }

    def infer_risk_level(self, affected_surfaces: list[str]) -> str:
        surfaces = set(_normalize_surfaces(affected_surfaces))
        if surfaces & {"backend_code", "security", "connection_strings"}:
            return RISK["critical"]
        if surfaces & {"integrations", "mcp", "compute"}:
            return RISK["high"]
        if surfaces & {"prompts", "configs", "skills", "agents", "ui", "orchestration"}:
            return RISK["medium"]
        return RISK["low"]

    async def create_proposal(
        self,
        *,
        source_system: str = "manual",
        source_id: str = "",
        project_id: str = "",
        agent_id: str = "",
        title: str,
        summary: str = "",
        rationale: str = "",
        affected_surfaces: list[str] | None = None,
        risk_level: str | None = None,
        approval_policy: str | None = None,
        before_state: dict | None = None,
        proposed_change: dict | None = None,
        rollback_plan: dict | None = None,
        evidence: list | None = None,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        reasoning_memory_ids: list[str] | None = None,
        improvement_score: float | None = None,
        confidence: float = 0.5,
        created_by: str = "",
        status: str | None = None,
        db: AsyncSession | None = None,
    ) -> ImprovementProposal:
        async def _create(session: AsyncSession) -> ImprovementProposal:
            safe_source = _clean_string(source_system, max_chars=60) or "manual"
            safe_source_id = _clean_string(source_id, max_chars=120)
            if safe_source_id:
                existing = await session.execute(
                    select(ImprovementProposal).where(
                        ImprovementProposal.source_system == safe_source,
                        ImprovementProposal.source_id == safe_source_id,
                    )
                )
                existing_proposal = existing.scalar_one_or_none()
                if existing_proposal is not None:
                    await self._register_archive_variant(existing_proposal, session)
                    return existing_proposal

            classification = self.classify_policy(
                affected_surfaces=affected_surfaces,
                source_system=safe_source,
                risk_level=risk_level,
                proposed_change=proposed_change,
            )
            policy = approval_policy or classification["approval_policy"]
            initial_status = status
            if initial_status is None:
                initial_status = STATUS["applied"] if policy == POLICY["auto"] else STATUS["proposed"]

            now = _utcnow()
            proposal = ImprovementProposal(
                source_system=safe_source,
                source_id=safe_source_id,
                project_id=_clean_string(project_id, max_chars=36),
                agent_id=_clean_string(agent_id, max_chars=100),
                title=_clean_string(title, max_chars=255),
                summary=_clean_string(summary, max_chars=4000),
                rationale=_clean_string(rationale, max_chars=4000),
                risk_level=classification["risk_level"],
                approval_policy=policy,
                status=initial_status,
                improvement_score=improvement_score,
                confidence=max(0.0, min(1.0, float(confidence))),
                requires_human_approval=policy != POLICY["auto"],
                auto_apply_allowed=policy == POLICY["auto"],
                created_by=_clean_string(created_by, max_chars=100),
                applied_at=now if initial_status == STATUS["applied"] else None,
            )
            proposal.set_affected_surfaces(classification["affected_surfaces"])
            proposal.set_before_state(_clean_payload(before_state or {}))
            proposal.set_proposed_change(_clean_payload(proposed_change or {}))
            proposal.set_rollback_plan(_clean_payload(rollback_plan or {}))
            proposal.set_evidence(_clean_payload(evidence or []))
            proposal.set_metrics_before(_clean_payload(metrics_before or {}))
            proposal.set_metrics_after(_clean_payload(metrics_after or {}))
            proposal.set_reasoning_memory_ids(reasoning_memory_ids or [])
            session.add(proposal)
            await session.flush()
            await self._register_archive_variant(proposal, session)
            return proposal

        if db is not None:
            return await _create(db)
        async with async_session() as session:
            proposal = await _create(session)
            await session.commit()
            await session.refresh(proposal)
            return proposal

    async def get_proposal(self, proposal_id: str, db: AsyncSession | None = None) -> ImprovementProposal | None:
        async def _get(session: AsyncSession) -> ImprovementProposal | None:
            result = await session.execute(
                select(ImprovementProposal).where(ImprovementProposal.id == proposal_id)
            )
            return result.scalar_one_or_none()

        if db is not None:
            return await _get(db)
        async with async_session() as session:
            return await _get(session)

    async def get_proposal_by_source(
        self,
        *,
        source_system: str,
        source_id: str,
        db: AsyncSession | None = None,
    ) -> ImprovementProposal | None:
        async def _get(session: AsyncSession) -> ImprovementProposal | None:
            result = await session.execute(
                select(ImprovementProposal).where(
                    ImprovementProposal.source_system == source_system,
                    ImprovementProposal.source_id == source_id,
                )
            )
            return result.scalar_one_or_none()

        if db is not None:
            return await _get(db)
        async with async_session() as session:
            return await _get(session)

    async def list_proposals(
        self,
        *,
        project_id: str | None = None,
        source_system: str | None = None,
        status: str | None = None,
        affected_surface: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async def _list(session: AsyncSession) -> list[dict]:
            stmt = select(ImprovementProposal).order_by(ImprovementProposal.updated_at.desc())
            if project_id is not None:
                stmt = stmt.where(ImprovementProposal.project_id == project_id)
            if source_system:
                stmt = stmt.where(ImprovementProposal.source_system == source_system)
            if status:
                stmt = stmt.where(ImprovementProposal.status == status)
            stmt = stmt.offset(max(0, offset)).limit(max(1, min(200, limit)))
            result = await session.execute(stmt)
            proposals = [item.to_dict() for item in result.scalars().all()]
            if affected_surface:
                normalized = _normalize_surface(affected_surface)
                proposals = [
                    proposal for proposal in proposals
                    if normalized in proposal.get("affected_surfaces", [])
                ]
            return proposals

        if db is not None:
            return await _list(db)
        async with async_session() as session:
            return await _list(session)

    async def approve_proposal(
        self,
        proposal_id: str,
        *,
        reviewer_id: str = "",
        note: str = "",
        db: AsyncSession | None = None,
    ) -> dict:
        async def _approve(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            if proposal.status not in {STATUS["draft"], STATUS["proposed"]}:
                return {"error": f"Proposal status is '{proposal.status}', expected proposed"}
            now = _utcnow()
            proposal.status = STATUS["approved"]
            proposal.approved_by = _clean_string(reviewer_id, max_chars=100)
            proposal.approved_at = now
            evidence = proposal.get_evidence()
            evidence.append({"event": "approved", "at": now.isoformat(), "reviewer_id": reviewer_id, "note": note})
            proposal.set_evidence(evidence)
            await session.flush()
            await self._sync_archive_status(proposal, session, evidence={"reviewer_id": reviewer_id, "note": note})
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _approve(db)
        async with async_session() as session:
            result = await _approve(session)
            await session.commit()
            return result

    async def apply_proposal(
        self,
        proposal_id: str,
        *,
        actor_id: str = "",
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        async def _apply(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            if proposal.requires_human_approval and proposal.status != STATUS["approved"]:
                return {"error": f"Proposal status is '{proposal.status}', approval required before apply"}
            if not proposal.get_rollback_plan():
                return {"error": "Rollback plan required before apply"}
            now = _utcnow()
            proposal.status = STATUS["applied"]
            proposal.applied_by = _clean_string(actor_id, max_chars=100)
            proposal.applied_at = now
            events = proposal.get_evidence()
            events.append({"event": "applied", "at": now.isoformat(), "actor_id": actor_id, **(evidence or {})})
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(proposal, session, evidence={"actor_id": actor_id, **(evidence or {})})
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _apply(db)
        async with async_session() as session:
            result = await _apply(session)
            await session.commit()
            return result

    async def reject_proposal(
        self,
        proposal_id: str,
        *,
        reviewer_id: str = "",
        reason: str = "",
        db: AsyncSession | None = None,
    ) -> dict:
        async def _reject(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            if proposal.status in {STATUS["applied"], STATUS["reverted"]}:
                return {"error": f"Proposal status is '{proposal.status}', cannot reject"}
            now = _utcnow()
            proposal.status = STATUS["rejected"]
            proposal.approved_by = _clean_string(reviewer_id, max_chars=100)
            proposal.approved_at = now
            events = proposal.get_evidence()
            events.append({"event": "rejected", "at": now.isoformat(), "reviewer_id": reviewer_id, "reason": reason})
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(proposal, session, evidence={"reviewer_id": reviewer_id, "reason": reason})
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _reject(db)
        async with async_session() as session:
            result = await _reject(session)
            await session.commit()
            return result

    async def revert_proposal(
        self,
        proposal_id: str,
        *,
        actor_id: str = "",
        reason: str = "",
        db: AsyncSession | None = None,
    ) -> dict:
        async def _revert(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            if proposal.status != STATUS["applied"]:
                return {"error": f"Proposal status is '{proposal.status}', expected applied"}
            now = _utcnow()
            proposal.status = STATUS["reverted"]
            proposal.reverted_by = _clean_string(actor_id, max_chars=100)
            proposal.reverted_at = now
            events = proposal.get_evidence()
            events.append({"event": "reverted", "at": now.isoformat(), "actor_id": actor_id, "reason": reason})
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(proposal, session, evidence={"actor_id": actor_id, "reason": reason})
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _revert(db)
        async with async_session() as session:
            result = await _revert(session)
            await session.commit()
            return result

    async def quarantine_proposal(
        self,
        proposal_id: str,
        *,
        actor_id: str = "",
        reason: str = "",
        db: AsyncSession | None = None,
    ) -> dict:
        async def _quarantine(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            now = _utcnow()
            proposal.status = STATUS["quarantined"]
            events = proposal.get_evidence()
            events.append({"event": "quarantined", "at": now.isoformat(), "actor_id": actor_id, "reason": reason})
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(proposal, session, evidence={"actor_id": actor_id, "reason": reason})
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _quarantine(db)
        async with async_session() as session:
            result = await _quarantine(session)
            await session.commit()
            return result

    async def record_evaluation(
        self,
        proposal_id: str,
        *,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        passed: bool | None = None,
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        async def _record(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            now = _utcnow()
            if metrics_before is not None:
                proposal.set_metrics_before(_clean_payload(metrics_before))
            if metrics_after is not None:
                proposal.set_metrics_after(_clean_payload(metrics_after))
            runs = proposal.get_evaluation_runs()
            runs.append({
                "at": now.isoformat(),
                "passed": passed,
                "metrics_before": _clean_payload(metrics_before or {}),
                "metrics_after": _clean_payload(metrics_after or {}),
                "evidence": _clean_payload(evidence or {}),
            })
            proposal.set_evaluation_runs(runs)
            await session.flush()
            try:
                from app.core.dgmh_archive import dgmh_archive

                await dgmh_archive.record_evaluation_for_governance(
                    proposal.id,
                    metrics_before=metrics_before,
                    metrics_after=metrics_after,
                    passed=passed,
                    evidence=evidence,
                    db=session,
                )
            except Exception:
                pass
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _record(db)
        async with async_session() as session:
            result = await _record(session)
            await session.commit()
            return result

    async def record_feature_evidence(
        self,
        *,
        feature: str,
        source_system: str,
        source_id: str = "",
        project_id: str = "",
        agent_id: str = "",
        title: str | None = None,
        summary: str = "",
        affected_surfaces: list[str] | None = None,
        evidence: dict | None = None,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        confidence: float = 0.5,
        db: AsyncSession | None = None,
    ) -> dict:
        """Record producer evidence without treating it as an applied behavior mutation."""
        feature_key = _clean_string(feature, max_chars=120) or "unknown_feature"
        event_id = _clean_string(source_id or f"{feature_key}:{_utcnow().timestamp()}", max_chars=90)
        proposal_source_id = _clean_string(f"{feature_key}:{event_id}", max_chars=120)

        async def _record(session: AsyncSession) -> dict:
            existing = await self.get_proposal_by_source(
                source_system=source_system,
                source_id=proposal_source_id,
                db=session,
            )
            event = {
                "event": "producer_evidence",
                "at": _utcnow().isoformat(),
                "feature": feature_key,
                "source_system": source_system,
                "source_id": event_id,
                "evidence": _clean_payload(evidence or {}),
            }
            if existing is not None:
                events = existing.get_evidence()
                events.append(event)
                existing.set_evidence(events)
                if metrics_before is not None:
                    existing.set_metrics_before(_clean_payload(metrics_before))
                if metrics_after is not None:
                    existing.set_metrics_after(_clean_payload(metrics_after))
                await session.flush()
                await self._register_archive_variant(existing, session)
                try:
                    from app.core.dgmh_archive import dgmh_archive

                    await dgmh_archive.record_evaluation_for_governance(
                        existing.id,
                        metrics_before=metrics_before,
                        metrics_after=metrics_after,
                        passed=(evidence or {}).get("passed"),
                        evidence=event,
                        db=session,
                    )
                except Exception:
                    pass
                return {"proposal_id": existing.id, "status": existing.status, "appended": True}

            matrix = next(
                (
                    item for item in self.feature_contract_matrix()
                    if item.get("feature") == feature_key
                ),
                {},
            )
            surfaces = affected_surfaces or matrix.get("surfaces") or ["telemetry", "evaluation"]
            proposal = await self.create_proposal(
                source_system=source_system,
                source_id=proposal_source_id,
                project_id=project_id,
                agent_id=agent_id,
                title=title or f"Producer evidence for {feature_key}",
                summary=summary,
                rationale="Producer evidence captured by the system-wide improvement contract.",
                affected_surfaces=surfaces,
                risk_level=RISK["low"],
                approval_policy=POLICY["auto"],
                status=STATUS["applied"],
                proposed_change={
                    "feature": feature_key,
                    "producer": source_system,
                    "evidence_only": True,
                    "event_id": event_id,
                },
                rollback_plan={
                    "strategy": "remove or quarantine this evidence trace; no behavior mutation was applied",
                },
                evidence=[event],
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                confidence=confidence,
                created_by=source_system,
                db=session,
            )
            return {"proposal_id": proposal.id, "status": proposal.status, "appended": False}

        if db is not None:
            return await _record(db)
        async with async_session() as session:
            result = await _record(session)
            await session.commit()
            return result

    async def summary(self, *, project_id: str | None = None) -> dict:
        async with async_session() as session:
            stmt = select(ImprovementProposal)
            if project_id is not None:
                stmt = stmt.where(ImprovementProposal.project_id == project_id)
            result = await session.execute(stmt)
            proposals = result.scalars().all()
            status_counts = Counter(item.status for item in proposals)
            source_counts = Counter(item.source_system for item in proposals)
            surface_counts: Counter[str] = Counter()
            for proposal in proposals:
                surface_counts.update(proposal.get_affected_surfaces())
            return {
                "total": len(proposals),
                "by_status": dict(status_counts),
                "by_source_system": dict(source_counts),
                "by_surface": dict(surface_counts),
                "pending_human_approval": sum(
                    1 for item in proposals
                    if item.requires_human_approval and item.status in {STATUS["draft"], STATUS["proposed"]}
                ),
                "applied": status_counts.get(STATUS["applied"], 0),
                "reverted": status_counts.get(STATUS["reverted"], 0),
                "quarantined": status_counts.get(STATUS["quarantined"], 0),
            }

    def infer_autoresearch_surfaces(self, loop_type: str) -> list[str]:
        mapping = {
            "skill_prompt": ["skills", "prompts"],
            "model_temp": ["configs", "compute"],
            "rag_params": ["configs", "memory"],
            "persona": ["agents", "prompts"],
            "question_bank": ["interviews", "documents"],
            "ui_sim": ["ui"],
        }
        return mapping.get(loop_type, ["configs"])

    async def register_autoresearch_experiment(
        self,
        experiment: dict,
        *,
        project_id: str = "",
        reasoning_memory_ids: list[str] | None = None,
    ) -> list[str]:
        if not experiment.get("kept"):
            return []
        loop_type = str(experiment.get("loop_type", ""))
        surfaces = self.infer_autoresearch_surfaces(loop_type)
        proposal = await self.create_proposal(
            source_system="autoresearch",
            source_id=str(experiment.get("id", "")),
            project_id=project_id,
            agent_id="autoresearch",
            title=f"Promote autoresearch improvement for {loop_type or 'unknown loop'}",
            summary=str(experiment.get("hypothesis", "")),
            rationale=str(experiment.get("decision_reason", "")),
            affected_surfaces=surfaces,
            before_state={
                "baseline_score": experiment.get("baseline_score"),
                "target_name": experiment.get("target_name"),
            },
            proposed_change={
                "loop_type": loop_type,
                "target_name": experiment.get("target_name"),
                "hypothesis": experiment.get("hypothesis"),
                "mutation_description": experiment.get("mutation_description"),
            },
            rollback_plan={
                "strategy": "restore previous runner snapshot or revert the kept mutation through its owning runner",
                "requires_verification": True,
                "reason": "Autoresearch kept the candidate after measurement; permanent promotion remains governed.",
            },
            evidence=[{
                "kind": "autoresearch_experiment",
                "experiment_id": experiment.get("id"),
                "delta": experiment.get("delta"),
                "score_samples": experiment.get("score_samples"),
                "score_stddev": experiment.get("score_stddev"),
                "confidence_interval_95": experiment.get("confidence_interval_95"),
                "decision_reason": experiment.get("decision_reason"),
            }],
            metrics_before={"score": experiment.get("baseline_score")},
            metrics_after={"score": experiment.get("experiment_score"), "delta": experiment.get("delta")},
            reasoning_memory_ids=reasoning_memory_ids or [],
            improvement_score=experiment.get("delta"),
            confidence=0.7 if experiment.get("score_samples") else 0.6,
            created_by="autoresearch",
        )
        return [proposal.id]

    def infer_meta_surfaces(self, parameter_path: str) -> list[str]:
        if parameter_path.startswith("self_evolution."):
            return ["skills", "agents", "configs"]
        if parameter_path.startswith("task_router."):
            return ["orchestration", "configs"]
        if parameter_path.startswith("agent_factory."):
            return ["agents", "configs"]
        if parameter_path.startswith("agent."):
            return ["skills", "orchestration", "configs"]
        return ["configs"]

    async def register_meta_proposal(self, proposal: dict) -> str | None:
        parameter_path = str(proposal.get("parameter_path", ""))
        created = await self.create_proposal(
            source_system="hyperagent",
            source_id=str(proposal.get("id", "")),
            agent_id="meta-hyperagent",
            title=f"Review HyperAgent tuning for {parameter_path or 'parameter'}",
            summary=str(proposal.get("reason", "")),
            rationale=str(proposal.get("expected_impact", "")),
            affected_surfaces=self.infer_meta_surfaces(parameter_path),
            before_state={
                "parameter_path": parameter_path,
                "current_value": proposal.get("current_value"),
            },
            proposed_change={
                "parameter_path": parameter_path,
                "proposed_value": proposal.get("proposed_value"),
                "target_system": proposal.get("target_system"),
            },
            rollback_plan={
                "strategy": "revert the active MetaVariant or restore the previous parameter value",
                "old_value": proposal.get("current_value"),
                "parameter_path": parameter_path,
            },
            evidence=proposal.get("evidence", []),
            confidence=max(0.0, min(1.0, float(proposal.get("confidence", 50)) / 100)),
            created_by="meta-hyperagent",
        )
        return created.id

    async def register_agent_creation_proposal(self, proposal: dict) -> str | None:
        created = await self.create_proposal(
            source_system="memento_agent_factory",
            source_id=str(proposal.get("id", "")),
            agent_id="agent-factory",
            title=f"Review agent creation for {proposal.get('proposed_name', 'new agent')}",
            summary=str(proposal.get("reason", "")),
            rationale="Memento-Skills agent creation proposed a new specialized agent from a capability gap.",
            affected_surfaces=["agents", "skills", "prompts", "orchestration"],
            before_state={
                "source_task_id": proposal.get("source_task_id"),
                "capability_gap": proposal.get("reason"),
            },
            proposed_change={
                "agent_name": proposal.get("proposed_name"),
                "role": proposal.get("proposed_role"),
                "specialties": proposal.get("proposed_specialties"),
                "system_prompt": proposal.get("proposed_system_prompt"),
            },
            rollback_plan={
                "strategy": "disable or delete the generated custom agent and remove its persona overlay",
                "source_task_id": proposal.get("source_task_id"),
            },
            evidence=[{
                "kind": "memento_agent_creation",
                "confidence": proposal.get("confidence"),
                "created_at": proposal.get("created_at"),
            }],
            confidence=max(0.0, min(1.0, float(proposal.get("confidence", 50)) / 100)),
            created_by="agent-factory",
        )
        return created.id

    async def register_skill_update_proposal(self, proposal: dict) -> str | None:
        created = await self.create_proposal(
            source_system="skill_evolution",
            source_id=str(proposal.get("id", "")),
            agent_id="skill-manager",
            title=f"Review skill update for {proposal.get('skill_name', 'skill')}",
            summary=str(proposal.get("reason", "")),
            rationale="Skill evolution proposed a prompt/config mutation from observed quality telemetry.",
            affected_surfaces=["skills", "prompts", "telemetry"],
            before_state={
                "skill_name": proposal.get("skill_name"),
                "field": proposal.get("field"),
                "current_value": proposal.get("current_value"),
            },
            proposed_change={
                "skill_name": proposal.get("skill_name"),
                "field": proposal.get("field"),
                "proposed_value": proposal.get("proposed_value"),
            },
            rollback_plan={
                "strategy": "restore previous skill definition field",
                "skill_name": proposal.get("skill_name"),
                "field": proposal.get("field"),
                "old_value": proposal.get("current_value"),
            },
            evidence=[{
                "kind": "skill_update_proposal",
                "confidence": proposal.get("confidence"),
                "created_at": proposal.get("created_at"),
            }],
            confidence=max(0.0, min(1.0, float(proposal.get("confidence", 0.5)))),
            created_by="skill-manager",
        )
        return created.id

    async def register_skill_creation_proposal(self, proposal: dict) -> str | None:
        definition = proposal.get("proposed_definition") or {}
        created = await self.create_proposal(
            source_system="memento_skill_factory",
            source_id=str(proposal.get("id", "")),
            agent_id=str(proposal.get("source_agent_id", "skill-manager")),
            title=f"Review skill creation for {definition.get('name', 'new skill')}",
            summary=str(proposal.get("reason", "")),
            rationale="Memento-Skills skill creation proposed a reusable skill from a high-quality trace.",
            affected_surfaces=["skills", "prompts", "agents"],
            before_state={"source_task_id": proposal.get("source_task_id")},
            proposed_change={"definition": definition},
            rollback_plan={
                "strategy": "delete or disable the generated runtime skill definition",
                "skill_name": definition.get("name"),
            },
            evidence=[{
                "kind": "memento_skill_creation",
                "confidence": proposal.get("confidence"),
                "test_result": proposal.get("test_result"),
            }],
            confidence=max(0.0, min(1.0, float(proposal.get("confidence", 50)) / 100)),
            created_by="skill-manager",
        )
        return created.id

    async def register_self_evolution_promotion(self, promotion: dict, *, applied: bool = False) -> str | None:
        created = await self.create_proposal(
            source_system="self_evolution",
            source_id=f"{promotion.get('agent_id', '')}:{promotion.get('learning_id', '')}",
            agent_id=str(promotion.get("agent_id", "")),
            title=f"Track self-evolution promotion for {promotion.get('agent_id', 'agent')}",
            summary=str(promotion.get("learning", "")) or str(promotion.get("promotion_text", "")),
            rationale="Self-evolution promoted a mature learning into persona memory.",
            affected_surfaces=["agents", "prompts", "memory"],
            before_state={
                "learning_id": promotion.get("learning_id"),
                "target_file": promotion.get("target_file"),
            },
            proposed_change={
                "target_file": promotion.get("target_file"),
                "target_section": promotion.get("target_section"),
                "promotion_text": promotion.get("promotion_text"),
            },
            rollback_plan={
                "strategy": "remove the appended promotion entry from the target persona file",
                "target_file": promotion.get("target_file"),
            },
            evidence=[{"kind": "self_evolution_promotion", **_clean_payload(promotion)}],
            confidence=max(0.0, min(1.0, float(promotion.get("confidence", 70)) / 100)),
            created_by="self-evolution",
            status=STATUS["applied"] if applied else None,
        )
        return created.id

    def feature_contract_matrix(self) -> list[dict]:
        return [
            {
                "feature": "interviews_audio_upload_transcription_tagging_documents",
                "surfaces": ["interviews", "transcription", "documents", "skills"],
                "required_evidence": [
                    "audio dependency health",
                    "language detection result",
                    "transcription confidence or provider error",
                    "tagging and document creation trace",
                    "rollback for generated document/tag changes",
                ],
            },
            {
                "feature": "memento_skills_and_agent_creation",
                "surfaces": ["skills", "agents", "prompts", "reasoning"],
                "required_evidence": [
                    "capability gap",
                    "source memories",
                    "approval decision",
                    "promotion metrics",
                    "rollback path",
                ],
            },
            {
                "feature": "hyperagent_meta_tuning",
                "surfaces": ["configs", "orchestration", "skills", "agents"],
                "required_evidence": [
                    "observation snapshot",
                    "parameter bounds",
                    "approval decision",
                    "variant metrics before and after",
                    "revert or confirm action",
                ],
            },
            {
                "feature": "dgmh_archive_evolution",
                "surfaces": ["orchestration", "configs", "skills", "agents", "telemetry"],
                "required_evidence": [
                    "archive parent selection score",
                    "lineage and generation",
                    "proposal and approval link",
                    "evaluation runs with uncertainty",
                    "ReasoningBank success or failure trace",
                    "rollback or quarantine action",
                ],
            },
            {
                "feature": "karpathy_autoresearch",
                "surfaces": ["configs", "skills", "prompts", "ui", "compute"],
                "required_evidence": [
                    "baseline score",
                    "candidate mutation",
                    "sampled measurements",
                    "uncertainty guard",
                    "keep/revert decision",
                    "governance promotion proposal",
                ],
            },
            {
                "feature": "reasoning_bank",
                "surfaces": ["memory", "reasoning", "telemetry"],
                "required_evidence": [
                    "source trace",
                    "redacted memory",
                    "retrieval usage",
                    "quarantine/edit history",
                    "impact on future task outcomes",
                ],
            },
            {
                "feature": "mcp_integrations_and_aura_research",
                "surfaces": ["mcp", "integrations", "security", "telemetry"],
                "required_evidence": [
                    "access policy",
                    "secret redaction",
                    "audit entry",
                    "tool health",
                    "rollback or disable path",
                ],
            },
            {
                "feature": "whatsapp_telegram_channel_integrations",
                "surfaces": ["channels", "integrations", "security"],
                "required_evidence": [
                    "webhook validation",
                    "credential storage policy",
                    "message processing trace",
                    "rate/error telemetry",
                    "disable path",
                ],
            },
            {
                "feature": "ensemble_model_and_llm_orchestration",
                "surfaces": ["compute", "orchestration", "telemetry"],
                "required_evidence": [
                    "model eligibility",
                    "statistical comparison",
                    "fallback route",
                    "latency and error percentiles",
                    "hardware utilization signal",
                ],
            },
            {
                "feature": "pooled_compute_connection_strings",
                "surfaces": ["connection_strings", "compute", "security"],
                "required_evidence": [
                    "hashed token storage",
                    "redemption audit",
                    "network guard result",
                    "pool health",
                    "revocation path",
                ],
            },
            {
                "feature": "desktop_tray_installation",
                "surfaces": ["ui", "integrations", "compute"],
                "required_evidence": [
                    "dependency install check",
                    "server lifecycle trace",
                    "tray action result",
                    "error recovery state",
                    "platform-specific rollback",
                ],
            },
            {
                "feature": "all_menus_and_submenus",
                "surfaces": ["ui", "backend_code", "telemetry"],
                "required_evidence": [
                    "frontend route coverage",
                    "API contract coverage",
                    "empty/loading/error states",
                    "accessibility and mobile checks",
                    "visual change telemetry",
                ],
            },
        ]


improvement_governance = ImprovementGovernanceService()
