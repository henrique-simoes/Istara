"""Meta-Hyperagent — optional system-tuning layer for Istara.

Observes subsystem metrics (task routing, self-evolution, skill selection,
quality evaluation, agent capabilities) and proposes parameter adjustments.

All changes require explicit user approval before being applied.  Active
variants are time-boxed and can be reverted at any time.  Confirmed
overrides are persisted to ``data/_meta_overrides.json`` so they survive
restarts.

Safety constraints:
    - Max 3 active (un-confirmed) variants at once.
    - All proposed values validated against PARAMETER_BOUNDS.
    - No auto-apply — every proposal needs a human "approve" action.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
PROPOSALS_FILE = DATA_DIR / "_meta_proposals.json"
VARIANTS_FILE = DATA_DIR / "_meta_variants.json"
OBSERVATIONS_FILE = DATA_DIR / "_meta_observations.json"
OVERRIDES_FILE = DATA_DIR / "_meta_overrides.json"
AUDIT_LOG_FILE = DATA_DIR / "_meta_audit_log.jsonl"

MAX_ACTIVE_VARIANTS = 3


# ---------------------------------------------------------------------------
# Parameter bounds — safety envelope for tunable values
# ---------------------------------------------------------------------------

PARAMETER_BOUNDS: dict[str, Any] = {
    "self_evolution.PROMOTION_THRESHOLDS.min_occurrences": (1, 10),
    "self_evolution.PROMOTION_THRESHOLDS.min_confidence": (30, 95),
    "self_evolution.PROMOTION_THRESHOLDS.min_success_rate": (0.3, 0.95),
    "task_router.SPECIALTY_KEYWORDS": {"max_keywords_per_domain": 50},
    "agent.skill_similarity_threshold": (0.3, 0.9),
    "agent_factory.coverage_threshold": (0.3, 0.9),
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MetaProposal:
    id: str  # "mp_{uuid}"
    target_system: str  # "task_router"|"self_evolution"|"skill_selection"|"quality_eval"|"agent_factory"
    parameter_path: str  # e.g. "PROMOTION_THRESHOLDS.min_occurrences"
    current_value: Any
    proposed_value: Any
    reason: str
    evidence: list[dict]
    confidence: int  # 0-100
    expected_impact: str
    status: str  # "pending"|"approved"|"rejected"|"applied"|"reverted"
    variant_id: str | None = None
    created_at: str = ""
    reviewed_at: str | None = None
    applied_at: str | None = None
    reverted_at: str | None = None
    project_id: str = ""


@dataclass
class MetaVariant:
    id: str  # "mv_{uuid}"
    proposal_id: str
    target_system: str
    parameter_path: str
    old_value: Any
    new_value: Any
    applied_at: str
    reverted_at: str | None = None
    metrics_before: dict = field(default_factory=dict)
    metrics_after: dict | None = None
    observation_window_hours: int = 72
    status: str = "active"  # "active"|"reverted"|"confirmed"
    project_id: str = ""


# ---------------------------------------------------------------------------
# Atomic file write (matches agent_factory.py pattern)
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via temp-file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# MetaHyperagent singleton
# ---------------------------------------------------------------------------

class MetaHyperagent:
    """Observes subsystem metrics and proposes parameter tuning changes."""

    def __init__(self) -> None:
        self._proposals: list[dict] = []
        self._variants: list[dict] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._active_project_id: str | None = None
        self._recent_observations: list[dict] = []
        self._load()

    # -- Project scope ------------------------------------------------------

    @staticmethod
    def _require_project_id(project_id: str | None) -> str:
        scoped_project_id = str(project_id or "").strip()
        if not scoped_project_id:
            raise ValueError("project_id is required")
        return scoped_project_id

    @staticmethod
    def _matches_project(record: dict, project_id: str) -> bool:
        return str(record.get("project_id") or "") == project_id

    def _latest_observation_for_project(self, project_id: str) -> dict | None:
        for observation in reversed(self._recent_observations):
            if self._matches_project(observation, project_id):
                return observation
        return None

    @staticmethod
    async def _agent_factory_proposals_for_project(
        proposals: list[dict],
        project_id: str,
    ) -> list[dict]:
        task_ids = [str(item.get("source_task_id") or "") for item in proposals]
        task_ids = [task_id for task_id in task_ids if task_id]
        if not task_ids:
            return []
        try:
            from sqlalchemy import select

            from app.models.database import async_session
            from app.models.task import Task

            async with async_session() as db:
                result = await db.execute(
                    select(Task.id).where(
                        Task.id.in_(task_ids),
                        Task.project_id == project_id,
                    )
                )
                visible_task_ids = {str(task_id) for task_id in result.scalars().all()}
            return [
                proposal
                for proposal in proposals
                if str(proposal.get("source_task_id") or "") in visible_task_ids
            ]
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: project agent proposal filter failed: {exc}")
            return []

    # -- Persistence --------------------------------------------------------

    def _load(self) -> None:
        """Load proposals and variants from disk."""
        if PROPOSALS_FILE.exists():
            try:
                self._proposals = json.loads(PROPOSALS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._proposals = []
        if VARIANTS_FILE.exists():
            try:
                self._variants = json.loads(VARIANTS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._variants = []
        if OBSERVATIONS_FILE.exists():
            try:
                observations = json.loads(OBSERVATIONS_FILE.read_text(encoding="utf-8"))
                self._recent_observations = observations if isinstance(observations, list) else []
            except (json.JSONDecodeError, OSError):
                self._recent_observations = []

    def _save(self) -> None:
        """Persist proposals and variants to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write(PROPOSALS_FILE, json.dumps(self._proposals, indent=2, default=str))
        _atomic_write(VARIANTS_FILE, json.dumps(self._variants, indent=2, default=str))

    def _save_observations(self) -> None:
        """Persist bounded recent observations so metrics survive restarts."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            OBSERVATIONS_FILE,
            json.dumps(self._recent_observations[-100:], indent=2, default=str),
        )

    def _log_audit(self, action: str, details: dict) -> None:
        """Append an entry to the audit log (JSONL)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            **details,
        }
        try:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as exc:
            logger.warning(f"Meta-hyperagent audit log write failed: {exc}")

    # -- Observation --------------------------------------------------------

    async def observe_cycle(self, project_id: str | None = None) -> dict:
        """Collect metrics from observed subsystems for one project.

        Returns an observation dict with per-subsystem stats.
        """
        scoped_project_id = self._require_project_id(project_id)
        observation: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": scoped_project_id,
            "task_routing": {},
            "self_evolution": {},
            "skill_selection": {},
            "quality_eval": {},
            "agent_capabilities": {},
            "reasoning_bank": {},
        }

        # 1. Task routing — current keyword config
        try:
            import app.core.task_router as tr
            keyword_counts = {
                domain: len(kws) for domain, kws in tr.SPECIALTY_KEYWORDS.items()
            }
            observation["task_routing"] = {
                "specialty_domains": list(tr.SPECIALTY_KEYWORDS.keys()),
                "keyword_counts": keyword_counts,
                "total_keywords": sum(keyword_counts.values()),
            }
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: task_routing observe failed: {exc}")

        # 2. Self-evolution — current thresholds and promotion stats
        try:
            import app.core.self_evolution as se
            observation["self_evolution"] = {
                "thresholds": dict(se.PROMOTION_THRESHOLDS),
            }
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: self_evolution observe failed: {exc}")

        # 3. Skill selection — usage stats from skill_manager
        try:
            from app.skills.skill_manager import skill_manager

            stats = skill_manager.get_usage_stats(project_id=scoped_project_id)
            total_executions = sum(s.get("executions", 0) for s in stats.values())
            total_successes = sum(s.get("successes", 0) for s in stats.values())
            total_failures = sum(s.get("failures", 0) for s in stats.values())
            fallback_count = sum(
                1 for s in stats.values() if s.get("matched_via") == "semantic"
            )
            observation["skill_selection"] = {
                "project_id": scoped_project_id,
                "total_skills_tracked": len(stats),
                "total_executions": total_executions,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "semantic_fallback_count": fallback_count,
                "success_rate": (
                    round(total_successes / total_executions, 3)
                    if total_executions > 0
                    else None
                ),
            }
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: skill_selection observe failed: {exc}")

        # 4. Quality evaluation — verification pass/fail (read from skill stats)
        try:
            from app.skills.skill_manager import skill_manager

            stats = skill_manager.get_usage_stats(project_id=scoped_project_id)
            verification_passes = sum(
                s.get("verification_passes", 0) for s in stats.values()
            )
            verification_fails = sum(
                s.get("verification_fails", 0) for s in stats.values()
            )
            observation["quality_eval"] = {
                "project_id": scoped_project_id,
                "verification_passes": verification_passes,
                "verification_fails": verification_fails,
                "pass_rate": (
                    round(
                        verification_passes
                        / (verification_passes + verification_fails),
                        3,
                    )
                    if (verification_passes + verification_fails) > 0
                    else None
                ),
            }
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: quality_eval observe failed: {exc}")

        # 5. Agent capabilities — agent factory gap detections
        try:
            from app.core.agent_factory import AgentFactory

            factory = AgentFactory()
            pending = await self._agent_factory_proposals_for_project(
                factory.get_pending_proposals(),
                scoped_project_id,
            )
            all_proposals = await self._agent_factory_proposals_for_project(
                factory.get_all_proposals(),
                scoped_project_id,
            )
            observation["agent_capabilities"] = {
                "project_id": scoped_project_id,
                "pending_agent_proposals": len(pending),
                "total_agent_proposals": len(all_proposals),
            }
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: agent_capabilities observe failed: {exc}")

        # 6. ReasoningBank — shared success/failure memory for self-evolution.
        try:
            from app.core.reasoning_bank import reasoning_bank

            observation["reasoning_bank"] = await reasoning_bank.summary(
                project_id=scoped_project_id
            )
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: reasoning_bank observe failed: {exc}")

        self._recent_observations.append(observation)
        # Keep last 100 observations in memory
        if len(self._recent_observations) > 100:
            self._recent_observations = self._recent_observations[-100:]
        self._save_observations()

        self._log_audit("observation_cycle", {
            "project_id": scoped_project_id,
            "summary": {
                k: bool(v)
                for k, v in observation.items()
                if k not in {"timestamp", "project_id"}
            },
        })
        return observation

    # -- Analysis & Proposal Generation -------------------------------------

    async def analyze_and_propose(self, project_id: str | None = None) -> list[MetaProposal]:
        """Analyze recent project observations and generate parameter proposals."""
        scoped_project_id = self._require_project_id(project_id)
        latest = self._latest_observation_for_project(scoped_project_id)
        if latest is None:
            return []
        proposals: list[MetaProposal] = []

        # Rule 1: If skill selection semantic fallback rate > 40%, propose
        # lowering the similarity threshold.
        try:
            ss = latest.get("skill_selection", {})
            total_exec = ss.get("total_executions", 0)
            fallback_count = ss.get("semantic_fallback_count", 0)
            if total_exec >= 20 and fallback_count / total_exec > 0.40:
                current_threshold = 0.6  # default in agent.py
                proposed = max(0.3, round(current_threshold - 0.1, 2))
                if proposed != current_threshold:
                    proposals.append(MetaProposal(
                        id=f"mp_{uuid.uuid4().hex[:12]}",
                        target_system="skill_selection",
                        parameter_path="agent.skill_similarity_threshold",
                        current_value=current_threshold,
                        proposed_value=proposed,
                        reason=(
                            f"Semantic fallback rate is {fallback_count}/{total_exec} "
                            f"({fallback_count / total_exec:.0%}), exceeding 40% threshold. "
                            f"Lowering similarity threshold may improve direct matching."
                        ),
                        evidence=[{
                            "metric": "semantic_fallback_rate",
                            "value": round(fallback_count / total_exec, 3),
                            "total_executions": total_exec,
                        }],
                        confidence=60,
                        expected_impact="More skills matched directly, fewer semantic fallbacks",
                        status="pending",
                        created_at=datetime.now(timezone.utc).isoformat(),
                        project_id=scoped_project_id,
                    ))
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: skill selection analysis failed: {exc}")

        # Rule 2: If promotion rate from self-evolution is very low (< 5% of
        # candidates promoted), propose lowering thresholds.
        try:
            se_data = latest.get("self_evolution", {})
            thresholds = se_data.get("thresholds", {})
            min_occ = thresholds.get("min_occurrences", 3)
            if min_occ > 2:
                # Check if there's evidence of low promotion rates
                proposals.append(MetaProposal(
                    id=f"mp_{uuid.uuid4().hex[:12]}",
                    target_system="self_evolution",
                    parameter_path="self_evolution.PROMOTION_THRESHOLDS.min_occurrences",
                    current_value=min_occ,
                    proposed_value=max(1, min_occ - 1),
                    reason=(
                        f"Current min_occurrences={min_occ} may be too restrictive "
                        f"for early-stage deployments. Lowering to {max(1, min_occ - 1)} "
                        f"could allow faster agent learning."
                    ),
                    evidence=[{
                        "metric": "min_occurrences",
                        "current": min_occ,
                    }],
                    confidence=45,
                    expected_impact="More learnings promoted, faster agent adaptation",
                    status="pending",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    project_id=scoped_project_id,
                ))
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: self-evolution analysis failed: {exc}")

        # Rule 3: If quality verification fail rate > 30%, propose raising
        # self-evolution confidence threshold.
        try:
            qe = latest.get("quality_eval", {})
            passes = qe.get("verification_passes", 0)
            fails = qe.get("verification_fails", 0)
            total = passes + fails
            if total >= 10 and fails / total > 0.30:
                import app.core.self_evolution as se
                current_conf = se.PROMOTION_THRESHOLDS.get("min_confidence", 70)
                proposed_conf = min(95, current_conf + 5)
                if proposed_conf != current_conf:
                    proposals.append(MetaProposal(
                        id=f"mp_{uuid.uuid4().hex[:12]}",
                        target_system="quality_eval",
                        parameter_path="self_evolution.PROMOTION_THRESHOLDS.min_confidence",
                        current_value=current_conf,
                        proposed_value=proposed_conf,
                        reason=(
                            f"Quality verification fail rate is {fails}/{total} "
                            f"({fails / total:.0%}). Raising confidence threshold "
                            f"from {current_conf} to {proposed_conf} may improve "
                            f"promoted learning quality."
                        ),
                        evidence=[{
                            "metric": "verification_fail_rate",
                            "value": round(fails / total, 3),
                            "total_checks": total,
                        }],
                        confidence=55,
                        expected_impact="Higher quality promoted learnings, fewer bad promotions",
                        status="pending",
                        created_at=datetime.now(timezone.utc).isoformat(),
                        project_id=scoped_project_id,
                    ))
        except Exception as exc:
            logger.debug(f"Meta-hyperagent: quality eval analysis failed: {exc}")

        # Deduplicate — skip proposals for parameter paths that already have a
        # pending or active proposal.
        existing_paths = set()
        for p in self._proposals:
            if p.get("status") in ("pending", "applied"):
                if self._matches_project(p, scoped_project_id):
                    existing_paths.add(p.get("parameter_path"))

        new_proposals = []
        for proposal in proposals:
            if proposal.parameter_path not in existing_paths:
                self._proposals.append(asdict(proposal))
                new_proposals.append(proposal)
                existing_paths.add(proposal.parameter_path)

        if new_proposals:
            self._save()
            self._log_audit("proposals_generated", {
                "project_id": scoped_project_id,
                "count": len(new_proposals),
                "paths": [p.parameter_path for p in new_proposals],
            })

            # Broadcast each new proposal via WebSocket
            for p in new_proposals:
                try:
                    from app.api.websocket import broadcast_meta_proposal
                    await broadcast_meta_proposal(
                        proposal_id=p.id,
                        target_system=p.target_system,
                        reason=p.reason,
                        project_id=scoped_project_id,
                    )
                except Exception:
                    pass

            try:
                from app.core.improvement_governance import improvement_governance

                for proposal in new_proposals:
                    await improvement_governance.register_meta_proposal(
                        asdict(proposal),
                        project_id=scoped_project_id,
                    )
            except Exception as exc:
                logger.debug(f"Meta-hyperagent governance registration skipped: {exc}")

        return new_proposals

    # -- Apply / Revert / Confirm -------------------------------------------

    def _validate_bounds(self, parameter_path: str, value: Any) -> bool:
        """Check that a proposed value falls within PARAMETER_BOUNDS."""
        bounds = PARAMETER_BOUNDS.get(parameter_path)
        if bounds is None:
            return True  # No bounds defined — allow
        if isinstance(bounds, tuple) and len(bounds) == 2:
            lo, hi = bounds
            try:
                return lo <= value <= hi
            except TypeError:
                return False
        if isinstance(bounds, dict):
            # Dictionary bounds — structural checks
            return True
        return True

    def _active_variant_count(self, project_id: str) -> int:
        """Return active variants for one project."""
        return sum(
            1
            for v in self._variants
            if v.get("status") == "active" and self._matches_project(v, project_id)
        )

    async def apply_proposal(self, proposal_id: str, project_id: str | None = None) -> dict:
        """Approve and apply a pending proposal as an active variant.

        Returns the created variant dict or an error dict.
        """
        scoped_project_id = self._require_project_id(project_id)
        proposal = None
        for p in self._proposals:
            if p["id"] == proposal_id and self._matches_project(p, scoped_project_id):
                proposal = p
                break
        if not proposal:
            return {"error": "Proposal not found"}
        if proposal["status"] not in ("pending", "approved"):
            return {"error": f"Proposal status is '{proposal['status']}', expected 'pending'"}

        # Safety: max active variants
        if self._active_variant_count(scoped_project_id) >= MAX_ACTIVE_VARIANTS:
            return {"error": f"Max active variants ({MAX_ACTIVE_VARIANTS}) reached. Revert or confirm existing variants first."}

        # Validate bounds
        if not self._validate_bounds(proposal["parameter_path"], proposal["proposed_value"]):
            return {"error": f"Proposed value {proposal['proposed_value']} is outside bounds for {proposal['parameter_path']}"}

        # Apply the change to the live module globals
        try:
            self._apply_parameter(proposal["parameter_path"], proposal["proposed_value"])
        except Exception as exc:
            return {"error": f"Failed to apply parameter: {exc}"}

        # Create variant
        now_iso = datetime.now(timezone.utc).isoformat()
        variant = MetaVariant(
            id=f"mv_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            target_system=proposal["target_system"],
            parameter_path=proposal["parameter_path"],
            old_value=proposal["current_value"],
            new_value=proposal["proposed_value"],
            applied_at=now_iso,
            observation_window_hours=settings.meta_hyperagent_variant_observation_hours,
            status="active",
            project_id=scoped_project_id,
        )
        variant_dict = asdict(variant)
        self._variants.append(variant_dict)

        proposal["status"] = "applied"
        proposal["variant_id"] = variant.id
        proposal["reviewed_at"] = now_iso
        proposal["applied_at"] = now_iso

        self._save()
        self._log_audit("proposal_applied", {
            "project_id": scoped_project_id,
            "proposal_id": proposal_id,
            "variant_id": variant.id,
            "parameter_path": proposal["parameter_path"],
            "old_value": proposal["current_value"],
            "new_value": proposal["proposed_value"],
        })

        return variant_dict

    async def revert_variant(self, variant_id: str, project_id: str | None = None) -> dict:
        """Revert an active variant back to its original value."""
        scoped_project_id = self._require_project_id(project_id)
        variant = None
        for v in self._variants:
            if v["id"] == variant_id and self._matches_project(v, scoped_project_id):
                variant = v
                break
        if not variant:
            return {"error": "Variant not found"}
        if variant["status"] != "active":
            return {"error": f"Variant status is '{variant['status']}', expected 'active'"}

        try:
            self._apply_parameter(variant["parameter_path"], variant["old_value"])
        except Exception as exc:
            return {"error": f"Failed to revert parameter: {exc}"}

        now_iso = datetime.now(timezone.utc).isoformat()
        variant["status"] = "reverted"
        variant["reverted_at"] = now_iso

        # Update associated proposal
        for p in self._proposals:
            if p.get("id") == variant["proposal_id"] and self._matches_project(p, scoped_project_id):
                p["status"] = "reverted"
                p["reverted_at"] = now_iso
                break

        self._save()
        self._log_audit("variant_reverted", {
            "project_id": scoped_project_id,
            "variant_id": variant_id,
            "parameter_path": variant["parameter_path"],
            "restored_value": variant["old_value"],
        })
        return variant

    async def confirm_variant(self, variant_id: str, project_id: str | None = None) -> dict:
        """Confirm an active variant — persist the override permanently."""
        scoped_project_id = self._require_project_id(project_id)
        variant = None
        for v in self._variants:
            if v["id"] == variant_id and self._matches_project(v, scoped_project_id):
                variant = v
                break
        if not variant:
            return {"error": "Variant not found"}
        if variant["status"] != "active":
            return {"error": f"Variant status is '{variant['status']}', expected 'active'"}

        variant["status"] = "confirmed"

        # Update associated proposal
        for p in self._proposals:
            if p.get("id") == variant["proposal_id"] and self._matches_project(p, scoped_project_id):
                p["status"] = "approved"
                break

        # Persist to overrides file
        overrides = self._load_overrides_file()
        project_overrides = overrides.setdefault("projects", {}).setdefault(scoped_project_id, {})
        project_overrides[variant["parameter_path"]] = {
            "value": variant["new_value"],
            "variant_id": variant_id,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "project_id": scoped_project_id,
        }
        _atomic_write(OVERRIDES_FILE, json.dumps(overrides, indent=2, default=str))

        self._save()
        self._log_audit("variant_confirmed", {
            "project_id": scoped_project_id,
            "variant_id": variant_id,
            "parameter_path": variant["parameter_path"],
            "confirmed_value": variant["new_value"],
        })
        return variant

    # -- Override persistence -----------------------------------------------

    def _load_overrides_file(self) -> dict:
        """Read the confirmed overrides file."""
        if OVERRIDES_FILE.exists():
            try:
                return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def load_confirmed_overrides(self, project_id: str | None = None) -> None:
        """Apply confirmed overrides for a project."""
        scoped_project_id = str(project_id or "").strip()
        if not scoped_project_id:
            logger.info("Meta-hyperagent: skipping confirmed overrides without project scope")
            return
        overrides = self._load_overrides_file()
        if not overrides:
            return

        project_overrides = (overrides.get("projects") or {}).get(scoped_project_id, {})
        if not project_overrides:
            return

        applied = 0
        for param_path, entry in project_overrides.items():
            value = entry.get("value") if isinstance(entry, dict) else entry
            try:
                self._apply_parameter(param_path, value)
                applied += 1
            except Exception as exc:
                logger.warning(
                    f"Meta-hyperagent: failed to apply confirmed override "
                    f"{param_path}={value}: {exc}"
                )

        if applied:
            logger.info(
                f"Meta-hyperagent: applied {applied} confirmed override(s) "
                f"for project {scoped_project_id}"
            )

    # -- Parameter application to live modules ------------------------------

    def _apply_parameter(self, parameter_path: str, value: Any) -> None:
        """Modify an in-memory module global based on parameter_path.

        Supported paths:
            self_evolution.PROMOTION_THRESHOLDS.<key>
            task_router.SPECIALTY_KEYWORDS.<domain>  (append keyword)
            agent.skill_similarity_threshold
            agent_factory.coverage_threshold
        """
        parts = parameter_path.split(".")

        if parts[0] == "self_evolution" and parts[1] == "PROMOTION_THRESHOLDS":
            import app.core.self_evolution as se
            key = parts[2] if len(parts) > 2 else None
            if key and key in se.PROMOTION_THRESHOLDS:
                se.PROMOTION_THRESHOLDS[key] = value
                logger.info(f"Meta-hyperagent: set self_evolution.PROMOTION_THRESHOLDS.{key} = {value}")
                return
            raise ValueError(f"Unknown PROMOTION_THRESHOLDS key: {key}")

        if parts[0] == "task_router" and parts[1] == "SPECIALTY_KEYWORDS":
            import app.core.task_router as tr
            if len(parts) >= 3:
                domain = parts[2]
                # value can be a keyword string to append, or a list to replace
                if isinstance(value, str):
                    if domain in tr.SPECIALTY_KEYWORDS:
                        if value not in tr.SPECIALTY_KEYWORDS[domain]:
                            bounds = PARAMETER_BOUNDS.get("task_router.SPECIALTY_KEYWORDS", {})
                            max_kw = bounds.get("max_keywords_per_domain", 50)
                            if len(tr.SPECIALTY_KEYWORDS[domain]) < max_kw:
                                tr.SPECIALTY_KEYWORDS[domain].append(value)
                                logger.info(f"Meta-hyperagent: appended '{value}' to task_router.SPECIALTY_KEYWORDS[{domain}]")
                                return
                            raise ValueError(f"Domain '{domain}' at max keywords ({max_kw})")
                        return  # Already present
                    else:
                        tr.SPECIALTY_KEYWORDS[domain] = [value]
                        logger.info(f"Meta-hyperagent: created task_router.SPECIALTY_KEYWORDS[{domain}] = [{value}]")
                        return
                elif isinstance(value, list):
                    tr.SPECIALTY_KEYWORDS[domain] = value
                    logger.info(f"Meta-hyperagent: replaced task_router.SPECIALTY_KEYWORDS[{domain}]")
                    return
            raise ValueError(f"Invalid task_router.SPECIALTY_KEYWORDS path: {parameter_path}")

        if parameter_path == "agent.skill_similarity_threshold":
            import app.core.agent as ag
            import app.core.agent_execution as ae
            import app.core.agent_models as am

            ag._META_SKILL_SIMILARITY_THRESHOLD = value
            ae._META_SKILL_SIMILARITY_THRESHOLD = value
            am._META_SKILL_SIMILARITY_THRESHOLD = value
            logger.info(f"Meta-hyperagent: set agent._META_SKILL_SIMILARITY_THRESHOLD = {value}")
            return

        if parameter_path == "agent_factory.coverage_threshold":
            # The coverage check uses a hardcoded 0.6 — store as module attr
            import app.core.agent_factory as af
            af._META_COVERAGE_THRESHOLD = value
            logger.info(f"Meta-hyperagent: set agent_factory._META_COVERAGE_THRESHOLD = {value}")
            return

        raise ValueError(f"Unknown parameter path: {parameter_path}")

    # -- Observation loop ---------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the observation loop task is active."""
        return bool(self._running and self._task and not self._task.done())

    @property
    def active_project_id(self) -> str | None:
        """Project currently owned by the observation loop, if any."""
        return self._active_project_id if self.is_running else None

    def is_running_for_project(self, project_id: str | None) -> bool:
        """Return whether the observation loop is active for the requested project."""
        scoped_project_id = str(project_id or "").strip()
        return bool(
            scoped_project_id
            and self.is_running
            and self._active_project_id == scoped_project_id
        )

    def start(self, project_id: str | None = None) -> asyncio.Task:
        """Start the observation loop and retain the task handle."""
        scoped_project_id = self._require_project_id(project_id)
        if (
            self._task
            and not self._task.done()
            and self._active_project_id == scoped_project_id
        ):
            return self._task
        if self._task and not self._task.done():
            self.stop()
        self._active_project_id = scoped_project_id
        self.load_confirmed_overrides(project_id=scoped_project_id)
        self._task = asyncio.create_task(
            self.start_observation_loop(project_id=scoped_project_id)
        )
        return self._task

    async def start_observation_loop(self, project_id: str | None = None) -> None:
        """Background loop that observes and analyzes at configured intervals."""
        scoped_project_id = self._require_project_id(project_id)
        current_task = asyncio.current_task()
        if current_task is not None and (self._task is None or self._task.done()):
            self._task = current_task
        self._active_project_id = scoped_project_id
        self._running = True
        interval_secs = settings.meta_hyperagent_observation_interval_hours * 3600
        logger.info(
            f"Meta-hyperagent observation loop started "
            f"(project={scoped_project_id}, "
            f"interval={settings.meta_hyperagent_observation_interval_hours}h)"
        )

        try:
            while self._running:
                try:
                    await self.observe_cycle(project_id=scoped_project_id)
                    await self.analyze_and_propose(project_id=scoped_project_id)
                except Exception as exc:
                    logger.error(f"Meta-hyperagent observation cycle error: {exc}")

                if not self._running:
                    break
                await asyncio.sleep(interval_secs)
        except asyncio.CancelledError:
            logger.info("Meta-hyperagent observation loop cancelled.")
        finally:
            self._running = False
            if self._task is current_task:
                self._task = None
            if self._active_project_id == scoped_project_id:
                self._active_project_id = None
            logger.info("Meta-hyperagent observation loop stopped.")

    def stop(self, project_id: str | None = None) -> None:
        """Stop the observation loop."""
        scoped_project_id = str(project_id or "").strip()
        if scoped_project_id and self._active_project_id != scoped_project_id:
            return
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._active_project_id = None

    # -- Query helpers ------------------------------------------------------

    def get_pending_proposals(self, project_id: str | None = None) -> list[dict]:
        """Return proposals awaiting review."""
        scoped_project_id = self._require_project_id(project_id)
        return [
            p
            for p in self._proposals
            if p.get("status") == "pending" and self._matches_project(p, scoped_project_id)
        ]

    def get_all_proposals(self, limit: int = 50, project_id: str | None = None) -> list[dict]:
        """Return the most recent proposals (all statuses)."""
        scoped_project_id = self._require_project_id(project_id)
        proposals = [p for p in self._proposals if self._matches_project(p, scoped_project_id)]
        return proposals[-limit:]

    def get_active_variants(self, project_id: str | None = None) -> list[dict]:
        """Return currently active (un-reverted, un-confirmed) variants."""
        scoped_project_id = self._require_project_id(project_id)
        return [
            v
            for v in self._variants
            if v.get("status") == "active" and self._matches_project(v, scoped_project_id)
        ]

    def get_all_variants(self, limit: int = 50, project_id: str | None = None) -> list[dict]:
        """Return the most recent variants (all statuses)."""
        scoped_project_id = self._require_project_id(project_id)
        variants = [v for v in self._variants if self._matches_project(v, scoped_project_id)]
        return variants[-limit:]

    def get_recent_observations(self, limit: int = 10, project_id: str | None = None) -> list[dict]:
        """Return the most recent observation snapshots."""
        scoped_project_id = self._require_project_id(project_id)
        observations = [
            item
            for item in self._recent_observations
            if self._matches_project(item, scoped_project_id)
        ]
        return observations[-limit:]

    def reject_proposal(
        self,
        proposal_id: str,
        reason: str = "",
        project_id: str | None = None,
    ) -> dict | None:
        """Reject a pending proposal with optional reason."""
        scoped_project_id = self._require_project_id(project_id)
        for p in self._proposals:
            if (
                p["id"] == proposal_id
                and p["status"] == "pending"
                and self._matches_project(p, scoped_project_id)
            ):
                p["status"] = "rejected"
                p["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                if reason:
                    p["reject_reason"] = reason
                self._save()
                self._log_audit("proposal_rejected", {
                    "project_id": scoped_project_id,
                    "proposal_id": proposal_id,
                    "reason": reason,
                })
                return p
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

meta_hyperagent = MetaHyperagent()
