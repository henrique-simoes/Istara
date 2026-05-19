"""Improvement governance evidence and producer registration operations."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.improvement_governance_contracts import (
    POLICY,
    RISK,
    STATUS,
    clean_payload as _clean_payload,
    clean_string as _clean_string,
    normalize_surface as _normalize_surface,
    utcnow as _utcnow,
)
from app.core.improvement_governance_policy import ImprovementPolicyMixin
from app.core.sandbox_evaluation import sandbox_evaluation
from app.models.database import async_session
from app.models.improvement_governance import ImprovementProposal

class ImprovementGovernanceEvidenceMixin:
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
                project_id=project_id,
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
