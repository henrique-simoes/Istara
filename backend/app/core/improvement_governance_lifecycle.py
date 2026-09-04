"""Improvement governance proposal lifecycle operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.improvement_governance_contracts import (
    POLICY,
    STATUS,
)
from app.core.improvement_governance_contracts import (
    clean_payload as _clean_payload,
)
from app.core.improvement_governance_contracts import (
    clean_string as _clean_string,
)
from app.core.improvement_governance_contracts import (
    normalize_surface as _normalize_surface,
)
from app.core.improvement_governance_contracts import (
    utcnow as _utcnow,
)
from app.core.sandbox_evaluation import sandbox_evaluation
from app.models.database import async_session
from app.models.improvement_governance import ImprovementProposal

logger_name = "app.core.improvement_governance"


class ImprovementGovernanceLifecycleMixin:
    async def _register_archive_variant(
        self, proposal: ImprovementProposal, session: AsyncSession
    ) -> None:
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
            safe_project_id = _clean_string(project_id, max_chars=36)
            if safe_source_id:
                existing = await session.execute(
                    select(ImprovementProposal).where(
                        ImprovementProposal.source_system == safe_source,
                        ImprovementProposal.source_id == safe_source_id,
                        ImprovementProposal.project_id == safe_project_id,
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
                initial_status = (
                    STATUS["applied"] if policy == POLICY["auto"] else STATUS["proposed"]
                )

            now = _utcnow()
            proposal = ImprovementProposal(
                source_system=safe_source,
                source_id=safe_source_id,
                project_id=safe_project_id,
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

    async def get_proposal(
        self, proposal_id: str, db: AsyncSession | None = None
    ) -> ImprovementProposal | None:
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
        project_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> ImprovementProposal | None:
        async def _get(session: AsyncSession) -> ImprovementProposal | None:
            stmt = select(ImprovementProposal).where(
                ImprovementProposal.source_system == source_system,
                ImprovementProposal.source_id == source_id,
            )
            if project_id is not None:
                stmt = stmt.where(ImprovementProposal.project_id == project_id)
            result = await session.execute(stmt)
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
                    proposal
                    for proposal in proposals
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
            evidence.append(
                {
                    "event": "approved",
                    "at": now.isoformat(),
                    "reviewer_id": reviewer_id,
                    "note": note,
                }
            )
            proposal.set_evidence(evidence)
            await session.flush()
            await self._sync_archive_status(
                proposal, session, evidence={"reviewer_id": reviewer_id, "note": note}
            )
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
                return {
                    "error": f"Proposal status is '{proposal.status}', approval required before apply"
                }
            if not proposal.get_rollback_plan():
                return {"error": "Rollback plan required before apply"}
            now = _utcnow()
            events = proposal.get_evidence()
            sandbox_result = sandbox_evaluation.evaluate_proposal(
                proposal, apply_evidence=evidence or {}
            )
            events.append(sandbox_result)
            if not sandbox_result["passed"]:
                proposal.set_evidence(events)
                await session.flush()
                return {
                    "error": "Sandbox evaluation failed before apply",
                    "sandbox_evaluation": sandbox_result,
                    "proposal": proposal.to_dict(),
                }
            proposal.status = STATUS["applied"]
            proposal.applied_by = _clean_string(actor_id, max_chars=100)
            proposal.applied_at = now
            events.append(
                {
                    "event": "applied",
                    "at": now.isoformat(),
                    "actor_id": actor_id,
                    **(evidence or {}),
                }
            )
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(
                proposal, session, evidence={"actor_id": actor_id, **(evidence or {})}
            )
            return {"proposal": proposal.to_dict()}

        if db is not None:
            return await _apply(db)
        async with async_session() as session:
            result = await _apply(session)
            await session.commit()
            return result

    async def record_sandbox_evaluation(
        self,
        proposal_id: str,
        *,
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        async def _record(session: AsyncSession) -> dict:
            proposal = await self.get_proposal(proposal_id, db=session)
            if proposal is None:
                return {"error": "Proposal not found"}
            result = sandbox_evaluation.evaluate_proposal(proposal, apply_evidence=evidence or {})
            events = proposal.get_evidence()
            events.append(result)
            proposal.set_evidence(events)
            await session.flush()
            return {"proposal": proposal.to_dict(), "sandbox_evaluation": result}

        if db is not None:
            return await _record(db)
        async with async_session() as session:
            result = await _record(session)
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
            events.append(
                {
                    "event": "rejected",
                    "at": now.isoformat(),
                    "reviewer_id": reviewer_id,
                    "reason": reason,
                }
            )
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(
                proposal, session, evidence={"reviewer_id": reviewer_id, "reason": reason}
            )
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
            events.append(
                {"event": "reverted", "at": now.isoformat(), "actor_id": actor_id, "reason": reason}
            )
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(
                proposal, session, evidence={"actor_id": actor_id, "reason": reason}
            )
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
            events.append(
                {
                    "event": "quarantined",
                    "at": now.isoformat(),
                    "actor_id": actor_id,
                    "reason": reason,
                }
            )
            proposal.set_evidence(events)
            await session.flush()
            await self._sync_archive_status(
                proposal, session, evidence={"actor_id": actor_id, "reason": reason}
            )
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
            runs.append(
                {
                    "at": now.isoformat(),
                    "passed": passed,
                    "metrics_before": _clean_payload(metrics_before or {}),
                    "metrics_after": _clean_payload(metrics_after or {}),
                    "evidence": _clean_payload(evidence or {}),
                }
            )
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
