"""DGM-H archive evolution for Istara's governed improvement loops."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dgmh_archive_utils import (
    ARCHIVE_STATUS,
    SELECTABLE_STATUSES,
    artifact_kind,
    clean_payload,
    clean_string,
    mutation_kind,
    normalize_token,
    score_from_metrics,
    status_from_governance,
    ucb_score,
    utcnow,
)
from app.models.database import async_session
from app.models.dgmh_archive import DGMHArchiveVariant
from app.models.improvement_governance import ImprovementProposal


class DGMHArchiveService:
    """Register, select, evaluate, apply, and roll back DGM-H archive variants."""

    async def _get_variant(self, session: AsyncSession, variant_id: str) -> DGMHArchiveVariant | None:
        result = await session.execute(select(DGMHArchiveVariant).where(DGMHArchiveVariant.id == variant_id))
        return result.scalar_one_or_none()

    async def _select_parent_model(
        self,
        session: AsyncSession,
        *,
        target_system: str = "",
        artifact_kind: str = "",
        mutation_surface: str = "",
        project_id: str = "",
    ) -> DGMHArchiveVariant | None:
        stmt = select(DGMHArchiveVariant).where(DGMHArchiveVariant.status.in_(SELECTABLE_STATUSES))
        if target_system:
            stmt = stmt.where(DGMHArchiveVariant.target_system == target_system)
        if artifact_kind:
            stmt = stmt.where(DGMHArchiveVariant.artifact_kind == artifact_kind)
        if mutation_surface:
            stmt = stmt.where(DGMHArchiveVariant.mutation_surface == mutation_surface)
        if project_id:
            stmt = stmt.where(DGMHArchiveVariant.project_id.in_([project_id, ""]))
        result = await session.execute(stmt)
        candidates = result.scalars().all()
        if not candidates:
            return None
        total = len(candidates) + 1
        return max(
            candidates,
            key=lambda item: ucb_score(
                score=item.score,
                confidence=item.confidence,
                evaluation_count=len(item.get_evaluation()) + 1,
                total_variants=total,
            ),
        )

    async def register_variant(
        self,
        *,
        source_system: str = "manual",
        source_id: str = "",
        project_id: str = "",
        agent_id: str = "",
        governance_proposal_id: str = "",
        parent_id: str = "",
        target_system: str = "",
        mutation_kind: str = "proposal",
        mutation_surface: str = "evaluation",
        artifact_kind: str = "proposal_variant",
        artifact_ref: str = "",
        title: str = "",
        summary: str = "",
        mutation: dict | None = None,
        rollback_plan: dict | None = None,
        evidence: list | None = None,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        reasoning_memory_ids: list[str] | None = None,
        score: float | None = None,
        confidence: float = 0.5,
        status: str = ARCHIVE_STATUS["candidate"],
        db: AsyncSession | None = None,
    ) -> DGMHArchiveVariant:
        async def _register(session: AsyncSession) -> DGMHArchiveVariant:
            safe_source = clean_string(source_system, max_chars=60) or "manual"
            safe_source_id = clean_string(source_id, max_chars=120)
            safe_governance_id = clean_string(governance_proposal_id, max_chars=36)
            if safe_governance_id:
                existing = await session.execute(
                    select(DGMHArchiveVariant).where(
                        DGMHArchiveVariant.governance_proposal_id == safe_governance_id
                    )
                )
                existing_variant = existing.scalar_one_or_none()
                if existing_variant is not None:
                    return existing_variant
            elif safe_source_id:
                existing = await session.execute(
                    select(DGMHArchiveVariant).where(
                        DGMHArchiveVariant.source_system == safe_source,
                        DGMHArchiveVariant.source_id == safe_source_id,
                        DGMHArchiveVariant.mutation_kind == normalize_token(mutation_kind, "proposal"),
                    )
                )
                existing_variant = existing.scalar_one_or_none()
                if existing_variant is not None:
                    return existing_variant

            clean_target = clean_string(target_system, max_chars=120)
            clean_artifact = normalize_token(artifact_kind, "proposal_variant")
            clean_surface = normalize_token(mutation_surface, "evaluation")
            parent = None
            clean_parent_id = clean_string(parent_id, max_chars=36)
            if clean_parent_id:
                parent = await self._get_variant(session, clean_parent_id)
            elif clean_target or clean_surface:
                parent = await self._select_parent_model(
                    session,
                    target_system=clean_target,
                    artifact_kind=clean_artifact,
                    mutation_surface=clean_surface,
                    project_id=project_id,
                )

            lineage: list[str] = []
            generation = 0
            root_id = ""
            if parent is not None:
                clean_parent_id = parent.id
                generation = int(parent.generation or 0) + 1
                root_id = parent.root_id or parent.id
                lineage = [*parent.get_lineage(), parent.id]

            variant_score = score_from_metrics(
                score=score,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
            )
            variant = DGMHArchiveVariant(
                parent_id=clean_parent_id,
                root_id=root_id,
                generation=generation,
                source_system=safe_source,
                source_id=safe_source_id,
                project_id=clean_string(project_id, max_chars=36),
                agent_id=clean_string(agent_id, max_chars=100),
                governance_proposal_id=safe_governance_id,
                target_system=clean_target,
                mutation_kind=normalize_token(mutation_kind, "proposal"),
                mutation_surface=clean_surface,
                artifact_kind=clean_artifact,
                artifact_ref=clean_string(artifact_ref, max_chars=255),
                title=clean_string(title, max_chars=255),
                summary=clean_string(summary, max_chars=4000),
                status=status if status in set(ARCHIVE_STATUS.values()) else ARCHIVE_STATUS["candidate"],
                score=variant_score,
                confidence=max(0.0, min(1.0, float(confidence))),
            )
            variant.set_lineage(lineage)
            variant.set_mutation(clean_payload(mutation or {}))
            variant.set_rollback_plan(clean_payload(rollback_plan or {}))
            variant.set_evidence(clean_payload(evidence or []))
            variant.set_metrics_before(clean_payload(metrics_before or {}))
            variant.set_metrics_after(clean_payload(metrics_after or {}))
            variant.set_reasoning_memory_ids(reasoning_memory_ids or [])
            variant.ucb_score = ucb_score(
                score=variant.score,
                confidence=variant.confidence,
                evaluation_count=1,
                total_variants=2,
            )
            session.add(variant)
            await session.flush()
            if not variant.root_id:
                variant.root_id = variant.id
                await session.flush()
            return variant

        if db is not None:
            return await _register(db)
        async with async_session() as session:
            variant = await _register(session)
            await session.commit()
            await session.refresh(variant)
            return variant

    async def register_from_governance_proposal(
        self,
        proposal: ImprovementProposal,
        *,
        db: AsyncSession | None = None,
    ) -> DGMHArchiveVariant:
        surfaces = proposal.get_affected_surfaces()
        proposed_change = proposal.get_proposed_change()
        target_system = (
            str(proposed_change.get("target_system", ""))
            or str(proposed_change.get("loop_type", ""))
            or (surfaces[0] if surfaces else "evaluation")
        )
        mutation_surface = surfaces[0] if surfaces else "evaluation"
        return await self.register_variant(
            source_system=proposal.source_system,
            source_id=proposal.source_id,
            project_id=proposal.project_id,
            agent_id=proposal.agent_id,
            governance_proposal_id=proposal.id,
            target_system=target_system,
            mutation_kind=mutation_kind(proposal.source_system, proposed_change),
            mutation_surface=mutation_surface,
            artifact_kind=artifact_kind(surfaces, proposal.source_system, proposed_change),
            artifact_ref=str(proposed_change.get("parameter_path", "")) or proposal.source_id,
            title=proposal.title,
            summary=proposal.summary,
            mutation=proposed_change,
            rollback_plan=proposal.get_rollback_plan(),
            evidence=proposal.get_evidence(),
            metrics_before=proposal.get_metrics_before(),
            metrics_after=proposal.get_metrics_after(),
            reasoning_memory_ids=proposal.get_reasoning_memory_ids(),
            score=proposal.improvement_score,
            confidence=proposal.confidence,
            status=status_from_governance(proposal.status),
            db=db,
        )

    async def list_variants(
        self,
        *,
        project_id: str | None = None,
        source_system: str | None = None,
        status: str | None = None,
        target_system: str | None = None,
        mutation_surface: str | None = None,
        artifact_kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async def _list(session: AsyncSession) -> list[dict]:
            stmt = select(DGMHArchiveVariant).order_by(DGMHArchiveVariant.updated_at.desc())
            if project_id is not None:
                stmt = stmt.where(DGMHArchiveVariant.project_id == project_id)
            if source_system:
                stmt = stmt.where(DGMHArchiveVariant.source_system == source_system)
            if status:
                stmt = stmt.where(DGMHArchiveVariant.status == status)
            if target_system:
                stmt = stmt.where(DGMHArchiveVariant.target_system == target_system)
            if mutation_surface:
                stmt = stmt.where(DGMHArchiveVariant.mutation_surface == mutation_surface)
            if artifact_kind:
                stmt = stmt.where(DGMHArchiveVariant.artifact_kind == artifact_kind)
            stmt = stmt.offset(max(0, offset)).limit(max(1, min(200, limit)))
            result = await session.execute(stmt)
            return [item.to_dict() for item in result.scalars().all()]

        if db is not None:
            return await _list(db)
        async with async_session() as session:
            return await _list(session)

    async def get_variant(
        self,
        variant_id: str,
        *,
        db: AsyncSession | None = None,
    ) -> DGMHArchiveVariant | None:
        if db is not None:
            return await self._get_variant(db, variant_id)
        async with async_session() as session:
            return await self._get_variant(session, variant_id)

    async def select_parent(
        self,
        *,
        target_system: str = "",
        artifact_kind: str = "",
        mutation_surface: str = "",
        project_id: str = "",
        db: AsyncSession | None = None,
    ) -> dict | None:
        async def _select(session: AsyncSession) -> dict | None:
            variant = await self._select_parent_model(
                session,
                target_system=target_system,
                artifact_kind=artifact_kind,
                mutation_surface=mutation_surface,
                project_id=project_id,
            )
            if variant is None:
                return None
            return variant.to_dict()

        if db is not None:
            return await _select(db)
        async with async_session() as session:
            return await _select(session)

    async def record_evaluation(
        self,
        variant_id: str,
        *,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        passed: bool | None = None,
        evidence: dict | None = None,
        score: float | None = None,
        confidence: float | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        async def _record(session: AsyncSession) -> dict:
            variant = await self._get_variant(session, variant_id)
            if variant is None:
                return {"error": "DGM-H archive variant not found"}
            now = utcnow()
            if metrics_before is not None:
                variant.set_metrics_before(clean_payload(metrics_before))
            if metrics_after is not None:
                variant.set_metrics_after(clean_payload(metrics_after))
            runs = variant.get_evaluation()
            runs.append(
                {
                    "at": now.isoformat(),
                    "passed": passed,
                    "metrics_before": clean_payload(metrics_before or {}),
                    "metrics_after": clean_payload(metrics_after or {}),
                    "evidence": clean_payload(evidence or {}),
                }
            )
            variant.set_evaluation(runs)
            variant.evaluated_at = now
            computed_score = score_from_metrics(
                score=score,
                metrics_before=metrics_before or variant.get_metrics_before(),
                metrics_after=metrics_after or variant.get_metrics_after(),
            )
            if computed_score is not None:
                variant.score = computed_score
            if confidence is not None:
                variant.confidence = max(0.0, min(1.0, float(confidence)))
            if passed is False and variant.status not in {ARCHIVE_STATUS["active"], ARCHIVE_STATUS["confirmed"]}:
                variant.status = ARCHIVE_STATUS["failed"]
            variant.ucb_score = ucb_score(
                score=variant.score,
                confidence=variant.confidence,
                evaluation_count=len(runs) + 1,
                total_variants=len(runs) + 2,
            )
            await session.flush()
            await self._record_reasoning_trace(
                variant,
                outcome="success" if passed else "failure" if passed is False else "unknown",
            )
            return {"variant": variant.to_dict()}

        if db is not None:
            return await _record(db)
        async with async_session() as session:
            result = await _record(session)
            await session.commit()
            return result

    async def update_status_for_governance(
        self,
        governance_proposal_id: str,
        status: str,
        *,
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async def _update(session: AsyncSession) -> list[dict]:
            result = await session.execute(
                select(DGMHArchiveVariant).where(
                    DGMHArchiveVariant.governance_proposal_id == governance_proposal_id
                )
            )
            variants = result.scalars().all()
            now = utcnow()
            archive_status = status_from_governance(status)
            updated: list[dict] = []
            for variant in variants:
                variant.status = archive_status
                events = variant.get_evidence()
                events.append(
                    {
                        "event": f"governance_{status}",
                        "at": now.isoformat(),
                        **clean_payload(evidence or {}),
                    }
                )
                variant.set_evidence(events)
                if archive_status == ARCHIVE_STATUS["active"]:
                    variant.applied_at = now
                elif archive_status == ARCHIVE_STATUS["reverted"]:
                    variant.reverted_at = now
                elif archive_status == ARCHIVE_STATUS["confirmed"]:
                    variant.confirmed_at = now
                updated.append(variant.to_dict())
            if variants:
                await session.flush()
            return updated

        if db is not None:
            return await _update(db)
        async with async_session() as session:
            updated = await _update(session)
            await session.commit()
            return updated

    async def record_evaluation_for_governance(
        self,
        governance_proposal_id: str,
        *,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        passed: bool | None = None,
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async def _record_all(session: AsyncSession) -> list[dict]:
            result = await session.execute(
                select(DGMHArchiveVariant).where(
                    DGMHArchiveVariant.governance_proposal_id == governance_proposal_id
                )
            )
            variants = result.scalars().all()
            updated: list[dict] = []
            for variant in variants:
                recorded = await self.record_evaluation(
                    variant.id,
                    metrics_before=metrics_before,
                    metrics_after=metrics_after,
                    passed=passed,
                    evidence=evidence,
                    db=session,
                )
                if "variant" in recorded:
                    updated.append(recorded["variant"])
            return updated

        if db is not None:
            return await _record_all(db)
        async with async_session() as session:
            updated = await _record_all(session)
            await session.commit()
            return updated

    async def apply_variant(
        self,
        variant_id: str,
        *,
        actor_id: str = "",
        evidence: dict | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        async def _apply(session: AsyncSession) -> dict:
            variant = await self._get_variant(session, variant_id)
            if variant is None:
                return {"error": "DGM-H archive variant not found"}
            if variant.status not in {ARCHIVE_STATUS["approved"], ARCHIVE_STATUS["active"]}:
                return {"error": f"Variant status is '{variant.status}', expected approved"}
            now = utcnow()
            variant.status = ARCHIVE_STATUS["active"]
            variant.applied_at = now
            events = variant.get_evidence()
            events.append({"event": "variant_applied", "at": now.isoformat(), "actor_id": actor_id, **(evidence or {})})
            variant.set_evidence(events)
            await session.flush()
            return {"variant": variant.to_dict()}

        if db is not None:
            return await _apply(db)
        async with async_session() as session:
            result = await _apply(session)
            await session.commit()
            return result

    async def set_variant_status(
        self,
        variant_id: str,
        *,
        status: str,
        actor_id: str = "",
        reason: str = "",
        db: AsyncSession | None = None,
    ) -> dict:
        async def _set(session: AsyncSession) -> dict:
            variant = await self._get_variant(session, variant_id)
            if variant is None:
                return {"error": "DGM-H archive variant not found"}
            if status not in set(ARCHIVE_STATUS.values()):
                return {"error": f"Unsupported DGM-H archive status: {status}"}
            now = utcnow()
            variant.status = status
            if status == ARCHIVE_STATUS["reverted"]:
                variant.reverted_at = now
            elif status == ARCHIVE_STATUS["confirmed"]:
                variant.confirmed_at = now
            elif status == ARCHIVE_STATUS["active"]:
                variant.applied_at = now
            events = variant.get_evidence()
            events.append({"event": f"variant_{status}", "at": now.isoformat(), "actor_id": actor_id, "reason": reason})
            variant.set_evidence(events)
            await session.flush()
            if status in {ARCHIVE_STATUS["confirmed"], ARCHIVE_STATUS["reverted"], ARCHIVE_STATUS["failed"]}:
                await self._record_reasoning_trace(
                    variant,
                    outcome="success" if status == ARCHIVE_STATUS["confirmed"] else "failure",
                )
            return {"variant": variant.to_dict()}

        if db is not None:
            return await _set(db)
        async with async_session() as session:
            result = await _set(session)
            await session.commit()
            return result

    async def lineage(self, variant_id: str) -> dict:
        async with async_session() as session:
            variant = await self._get_variant(session, variant_id)
            if variant is None:
                return {"error": "DGM-H archive variant not found"}
            ids = [*variant.get_lineage(), variant.id]
            if not ids:
                return {"variants": [variant.to_dict()]}
            result = await session.execute(
                select(DGMHArchiveVariant).where(DGMHArchiveVariant.id.in_(ids))
            )
            variants_by_id = {item.id: item.to_dict() for item in result.scalars().all()}
            return {
                "root_id": variant.root_id,
                "variant_id": variant.id,
                "variants": [variants_by_id[item_id] for item_id in ids if item_id in variants_by_id],
            }

    async def summary(self, *, project_id: str | None = None) -> dict:
        async with async_session() as session:
            stmt = select(DGMHArchiveVariant)
            if project_id is not None:
                stmt = stmt.where(DGMHArchiveVariant.project_id == project_id)
            result = await session.execute(stmt)
            variants = result.scalars().all()
            return {
                "total": len(variants),
                "by_status": dict(Counter(item.status for item in variants)),
                "by_source_system": dict(Counter(item.source_system for item in variants)),
                "by_surface": dict(Counter(item.mutation_surface for item in variants)),
                "by_artifact_kind": dict(Counter(item.artifact_kind for item in variants)),
                "candidate": sum(1 for item in variants if item.status == ARCHIVE_STATUS["candidate"]),
                "active": sum(1 for item in variants if item.status == ARCHIVE_STATUS["active"]),
                "confirmed": sum(1 for item in variants if item.status == ARCHIVE_STATUS["confirmed"]),
                "reverted": sum(1 for item in variants if item.status == ARCHIVE_STATUS["reverted"]),
                "quarantined": sum(1 for item in variants if item.status == ARCHIVE_STATUS["quarantined"]),
            }

    async def _record_reasoning_trace(self, variant: DGMHArchiveVariant, *, outcome: str) -> None:
        try:
            from app.core.reasoning_bank import reasoning_bank

            memories = await reasoning_bank.record_trace(
                project_id=variant.project_id,
                agent_id=variant.agent_id or "dgmh-archive",
                query=f"{variant.target_system} {variant.mutation_kind} {variant.title}",
                trajectory={
                    "variant_id": variant.id,
                    "parent_id": variant.parent_id,
                    "generation": variant.generation,
                    "source_system": variant.source_system,
                    "source_id": variant.source_id,
                    "mutation": variant.get_mutation(),
                    "score": variant.score,
                    "confidence": variant.confidence,
                    "status": variant.status,
                },
                outcome=outcome,
                source_kind="dgmh_archive",
                source_id=variant.id,
                tags=[variant.source_system, variant.mutation_kind, variant.mutation_surface],
                domain=variant.target_system or variant.mutation_surface,
                judge_score=variant.score if isinstance(variant.score, (int, float)) else None,
            )
            memory_ids = [memory["id"] for memory in memories if memory.get("id")]
            if memory_ids:
                existing = variant.get_reasoning_memory_ids()
                variant.set_reasoning_memory_ids([*existing, *memory_ids])
        except Exception:
            pass


dgmh_archive = DGMHArchiveService()
