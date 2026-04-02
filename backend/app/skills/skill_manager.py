"""Skill Manager — self-improving skill lifecycle management.

Handles:
1. Loading skills from individual YAML/JSON definition files
2. Versioning each skill independently (git-tracked)
3. Proposing improvements based on usage patterns
4. User approval workflow for skill updates
5. Skill creation, editing, enabling/disabling
6. Skill health monitoring and quality scoring
7. Autonomous skill creation proposals
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.checkpoint import atomic_write

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent / "definitions"


class SkillDefinition:
    """A skill loaded from its definition file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        required = ["name", "display_name", "description", "phase", "skill_type",
                     "plan_prompt", "execute_prompt", "output_schema"]
        for field in required:
            if field not in self.data:
                raise ValueError(f"Skill definition missing required field: {field} in {self.path}")

    @property
    def name(self) -> str: return self.data["name"]
    @property
    def display_name(self) -> str: return self.data["display_name"]
    @property
    def phase(self) -> str: return self.data["phase"]
    @property
    def version(self) -> str: return self.data.get("version", "1.0.0")
    @property
    def enabled(self) -> bool: return self.data.get("enabled", True)
    @property
    def metadata(self) -> dict: return self.data.get("metadata", {})

    def to_dict(self) -> dict:
        return {**self.data, "file": str(self.path.name)}


class SkillUpdateProposal:
    """A proposed improvement to a skill, pending user approval."""

    def __init__(
        self,
        skill_name: str,
        field: str,
        current_value: str,
        proposed_value: str,
        reason: str,
        confidence: float = 0.5,
    ) -> None:
        self.id = f"{skill_name}_{field}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.skill_name = skill_name
        self.field = field
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.reason = reason
        self.confidence = confidence
        self.status = "pending"  # pending, approved, rejected
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.reviewed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "field": self.field,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
        }


@dataclass
class SkillCreationProposal:
    """A proposed new skill definition, pending user approval."""

    id: str
    proposed_definition: dict  # full JSON skill definition
    source_task_id: str
    source_agent_id: str
    reason: str
    confidence: int  # 0-100
    status: str = "pending"  # pending|approved|rejected
    created_at: str = ""
    reviewed_at: str | None = None
    reject_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "proposed_definition": self.proposed_definition,
            "source_task_id": self.source_task_id,
            "source_agent_id": self.source_agent_id,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reject_reason": self.reject_reason,
        }


class SkillManager:
    """Manages the skill lifecycle — loading, versioning, improving, and monitoring."""

    def __init__(self) -> None:
        self._definitions: dict[str, SkillDefinition] = {}
        self._proposals: list[SkillUpdateProposal] = []
        self._creation_proposals: list[SkillCreationProposal] = []
        self._usage_stats: dict[str, dict] = {}  # skill_name → {executions, successes, failures, avg_quality}
        self._proposals_file = SKILLS_DIR / "_proposals.json"
        self._creation_proposals_file = SKILLS_DIR / "_creation_proposals.json"
        self._stats_file = SKILLS_DIR / "_usage_stats.json"

    def ensure_definitions_dir(self) -> None:
        """Create the definitions directory if it doesn't exist."""
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> dict[str, SkillDefinition]:
        """Load all skill definitions from individual JSON files."""
        self.ensure_definitions_dir()
        self._definitions = {}

        for path in sorted(SKILLS_DIR.glob("*.json")):
            if path.name.startswith("_"):
                continue  # Skip meta files
            try:
                defn = SkillDefinition(path)
                self._definitions[defn.name] = defn
                logger.info(f"Loaded skill definition: {defn.name} v{defn.version}")
            except Exception as e:
                logger.error(f"Failed to load skill {path}: {e}")

        # Load usage stats
        if self._stats_file.exists():
            try:
                self._usage_stats = json.loads(self._stats_file.read_text())
            except Exception:
                self._usage_stats = {}

        # Load pending proposals
        if self._proposals_file.exists():
            try:
                data = json.loads(self._proposals_file.read_text())
                self._proposals = []
                for p in data:
                    prop = SkillUpdateProposal(p["skill_name"], p["field"], p.get("current_value", ""),
                                                p.get("proposed_value", ""), p["reason"], p.get("confidence", 0.5))
                    prop.id = p["id"]
                    prop.status = p["status"]
                    prop.created_at = p["created_at"]
                    prop.reviewed_at = p.get("reviewed_at")
                    self._proposals.append(prop)
            except Exception:
                self._proposals = []

        # Load creation proposals
        if self._creation_proposals_file.exists():
            try:
                data = json.loads(self._creation_proposals_file.read_text())
                self._creation_proposals = []
                for p in data:
                    cp = SkillCreationProposal(
                        id=p["id"],
                        proposed_definition=p["proposed_definition"],
                        source_task_id=p["source_task_id"],
                        source_agent_id=p["source_agent_id"],
                        reason=p["reason"],
                        confidence=p["confidence"],
                        status=p.get("status", "pending"),
                        created_at=p.get("created_at", ""),
                        reviewed_at=p.get("reviewed_at"),
                        reject_reason=p.get("reject_reason"),
                    )
                    self._creation_proposals.append(cp)
            except Exception:
                self._creation_proposals = []

        logger.info(f"Loaded {len(self._definitions)} skill definitions.")
        return self._definitions

    def get(self, name: str) -> SkillDefinition | None:
        return self._definitions.get(name)

    def list_all(self) -> list[SkillDefinition]:
        return list(self._definitions.values())

    def list_by_phase(self, phase: str) -> list[SkillDefinition]:
        return [d for d in self._definitions.values() if d.phase == phase]

    # --- CRUD Operations ---

    def create_skill(self, data: dict) -> SkillDefinition:
        """Create a new skill definition file."""
        self.ensure_definitions_dir()
        name = data["name"]
        data.setdefault("version", "1.0.0")
        data.setdefault("enabled", True)
        data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data.setdefault("changelog", [{"version": "1.0.0", "date": data["created_at"], "changes": "Initial creation"}])

        path = SKILLS_DIR / f"{name}.json"
        atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False))

        defn = SkillDefinition(path)
        self._definitions[name] = defn
        logger.info(f"Created skill: {name}")
        return defn

    def update_skill(self, name: str, updates: dict, changelog_entry: str = "") -> SkillDefinition:
        """Update a skill definition — increments version automatically."""
        defn = self._definitions.get(name)
        if not defn:
            raise ValueError(f"Skill not found: {name}")

        # Increment patch version
        parts = defn.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)

        # Update data
        defn.data.update(updates)
        defn.data["version"] = new_version
        defn.data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Add changelog
        changelog = defn.data.setdefault("changelog", [])
        changelog.append({
            "version": new_version,
            "date": defn.data["updated_at"],
            "changes": changelog_entry or f"Updated fields: {', '.join(updates.keys())}",
        })

        # Write back
        atomic_write(defn.path, json.dumps(defn.data, indent=2, ensure_ascii=False))
        logger.info(f"Updated skill: {name} → v{new_version}")
        return defn

    def delete_skill(self, name: str) -> bool:
        """Delete a skill definition file."""
        defn = self._definitions.get(name)
        if not defn:
            return False

        # Move to a backup instead of hard delete
        backup_dir = SKILLS_DIR / "_deleted"
        backup_dir.mkdir(exist_ok=True)
        shutil.move(str(defn.path), str(backup_dir / defn.path.name))

        del self._definitions[name]
        logger.info(f"Deleted skill: {name} (backed up)")
        return True

    def toggle_skill(self, name: str, enabled: bool) -> SkillDefinition:
        """Enable or disable a skill."""
        return self.update_skill(name, {"enabled": enabled},
                                  f"{'Enabled' if enabled else 'Disabled'} skill")

    # --- Usage Tracking ---

    def record_execution(self, skill_name: str, success: bool, quality_score: float = 0.0) -> None:
        """Record a skill execution for usage tracking (includes utility score).

        Skipped during autoresearch experiments — autoresearch tracks its own
        metrics in the model_skill_stats table.
        """
        from app.core.autoresearch_isolation import is_autoresearch_active
        if is_autoresearch_active():
            return
        stats = self._usage_stats.setdefault(skill_name, {
            "executions": 0, "successes": 0, "failures": 0,
            "total_quality": 0.0, "utility_score": 0.5, "last_used": None,
        })
        stats["executions"] += 1
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        stats["total_quality"] += quality_score
        stats["last_used"] = datetime.now(timezone.utc).isoformat()

        # Update utility score: EMA toward 1.0 on success, toward 0.0 on failure
        current_utility = stats.get("utility_score", 0.5)
        if success:
            stats["utility_score"] = current_utility * 0.9 + 0.1
        else:
            stats["utility_score"] = current_utility * 0.9

        self._save_stats()

        # Flag low-utility skills and auto-deprecate chronically failing ones
        if stats["executions"] >= 10 and stats["utility_score"] < 0.3:
            try:
                import asyncio
                from app.api.websocket import broadcast_suggestion

                # Auto-deprecate if utility is critically low
                if stats["utility_score"] < 0.2:
                    defn = self._definitions.get(skill_name)
                    if defn:
                        defn._data["lifecycle"] = "deprecated"
                        self._save_definition(skill_name)
                        logger.warning(f"Skill '{skill_name}' auto-deprecated (utility={stats['utility_score']:.2f} after {stats['executions']} runs)")

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        broadcast_suggestion(
                            f"Skill '{skill_name}' has low utility "
                            f"({stats['utility_score']:.0%} after "
                            f"{stats['executions']} runs). "
                            + ("It has been auto-deprecated." if stats["utility_score"] < 0.2 else "Consider reviewing or replacing it."),
                            "",
                        )
                    )
            except Exception:
                pass  # Non-critical broadcast

    def get_usage_stats(self, skill_name: str | None = None) -> dict:
        """Get usage statistics for one or all skills (includes utility_score)."""
        if skill_name:
            stats = self._usage_stats.get(skill_name, {})
            if stats and stats.get("executions", 0) > 0:
                stats["avg_quality"] = stats["total_quality"] / stats["executions"]
                stats["success_rate"] = stats["successes"] / stats["executions"]
            # Ensure utility_score is always present
            stats.setdefault("utility_score", 0.5)
            return stats
        return self._usage_stats

    def _save_stats(self) -> None:
        self.ensure_definitions_dir()
        atomic_write(self._stats_file, json.dumps(self._usage_stats, indent=2))

    # --- Self-Improvement ---

    def propose_improvement(
        self,
        skill_name: str,
        field: str,
        current_value: str,
        proposed_value: str,
        reason: str,
        confidence: float = 0.5,
    ) -> SkillUpdateProposal:
        """Create a proposed improvement for user review."""
        proposal = SkillUpdateProposal(skill_name, field, current_value, proposed_value, reason, confidence)
        self._proposals.append(proposal)
        self._save_proposals()
        logger.info(f"Proposed improvement for {skill_name}.{field}: {reason}")
        return proposal

    def get_pending_proposals(self) -> list[SkillUpdateProposal]:
        return [p for p in self._proposals if p.status == "pending"]

    def get_all_proposals(self, limit: int = 50) -> list[SkillUpdateProposal]:
        return self._proposals[-limit:]

    def approve_proposal(self, proposal_id: str) -> bool:
        """Approve and apply a proposed improvement."""
        for proposal in self._proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                proposal.status = "approved"
                proposal.reviewed_at = datetime.now(timezone.utc).isoformat()

                # Apply the change
                try:
                    self.update_skill(
                        proposal.skill_name,
                        {proposal.field: proposal.proposed_value},
                        f"Self-improvement applied: {proposal.reason}",
                    )
                except Exception as e:
                    logger.error(f"Failed to apply proposal {proposal_id}: {e}")
                    proposal.status = "failed"

                self._save_proposals()
                return True
        return False

    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Reject a proposed improvement."""
        for proposal in self._proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                proposal.status = "rejected"
                proposal.reviewed_at = datetime.now(timezone.utc).isoformat()
                if reason:
                    proposal.reason += f" [Rejected: {reason}]"
                self._save_proposals()
                return True
        return False

    def _save_proposals(self) -> None:
        self.ensure_definitions_dir()
        atomic_write(
            self._proposals_file,
            json.dumps([p.to_dict() for p in self._proposals], indent=2),
        )

    # --- Skill Health ---

    def get_skill_health(self, name: str) -> dict:
        """Get health score for a skill based on usage, quality, and definition completeness."""
        defn = self._definitions.get(name)
        if not defn:
            return {"status": "not_found"}

        stats = self._usage_stats.get(name, {})
        executions = stats.get("executions", 0)
        success_rate = stats.get("successes", 0) / max(executions, 1)
        avg_quality = stats.get("total_quality", 0) / max(executions, 1)

        # Definition completeness
        completeness = 1.0
        if not defn.data.get("plan_prompt"): completeness -= 0.2
        if not defn.data.get("execute_prompt"): completeness -= 0.3
        if not defn.data.get("output_schema"): completeness -= 0.2
        if not defn.data.get("description"): completeness -= 0.1
        if len(defn.data.get("execute_prompt", "")) < 100: completeness -= 0.1
        if len(defn.data.get("output_schema", "")) < 50: completeness -= 0.1

        health_score = (success_rate * 0.4 + avg_quality * 0.3 + completeness * 0.3) if executions > 0 else completeness * 0.3

        return {
            "name": name,
            "version": defn.version,
            "enabled": defn.enabled,
            "executions": executions,
            "success_rate": round(success_rate, 2),
            "avg_quality": round(avg_quality, 2),
            "completeness": round(completeness, 2),
            "health_score": round(health_score, 2),
            "last_used": stats.get("last_used"),
            "pending_proposals": len([p for p in self._proposals if p.skill_name == name and p.status == "pending"]),
        }

    def get_all_health(self) -> list[dict]:
        """Get health scores for all skills."""
        return [self.get_skill_health(name) for name in self._definitions]

    # --- Autonomous Skill Creation ---

    def propose_skill_creation(
        self,
        definition: dict,
        source_task_id: str,
        agent_id: str,
        reason: str,
        confidence: int,
    ) -> SkillCreationProposal:
        """Create a proposal for a brand-new skill definition.

        Validates the definition, scans prompts for injection, and persists
        the proposal for human review.
        """
        # Validate required fields
        required = [
            "name", "display_name", "description", "phase", "skill_type",
            "plan_prompt", "execute_prompt", "output_schema",
        ]
        missing = [f for f in required if f not in definition]
        if missing:
            raise ValueError(f"Proposed definition missing required fields: {missing}")

        # Scan prompts with ContentGuard for injection
        from app.core.content_guard import ContentGuard
        guard = ContentGuard()
        for prompt_field in ("plan_prompt", "execute_prompt"):
            scan = guard.scan_text(definition[prompt_field])
            if not scan.clean and scan.threat_level in ("high", "medium"):
                raise ValueError(
                    f"ContentGuard flagged {prompt_field}: {scan.threats}"
                )

        # Check no existing skill with same name
        if self._definitions.get(definition["name"]):
            raise ValueError(f"Skill already exists: {definition['name']}")

        proposal = SkillCreationProposal(
            id=f"create_{definition['name']}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            proposed_definition=definition,
            source_task_id=source_task_id,
            source_agent_id=agent_id,
            reason=reason,
            confidence=confidence,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._creation_proposals.append(proposal)
        self._save_creation_proposals()
        logger.info(f"Proposed new skill creation: {definition['name']} (confidence={confidence})")
        return proposal

    def get_pending_creation_proposals(self) -> list[SkillCreationProposal]:
        """Return creation proposals with status == 'pending'."""
        return [p for p in self._creation_proposals if p.status == "pending"]

    def get_all_creation_proposals(self, limit: int = 20) -> list[SkillCreationProposal]:
        """Return the last N creation proposals."""
        return self._creation_proposals[-limit:]

    def approve_creation_proposal(self, proposal_id: str) -> dict | None:
        """Approve a creation proposal — writes the skill JSON and marks approved.

        Returns the definition dict for registry loading, or None if not found.
        """
        for proposal in self._creation_proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                defn = proposal.proposed_definition
                defn.setdefault("version", "1.0.0")
                defn.setdefault("enabled", True)
                defn["created_at"] = datetime.now(timezone.utc).isoformat()
                defn.setdefault("changelog", [{
                    "version": "1.0.0",
                    "date": defn["created_at"],
                    "changes": "Initial creation via autonomous proposal",
                }])

                # Write to definitions/
                self.ensure_definitions_dir()
                path = SKILLS_DIR / f"{defn['name']}.json"
                atomic_write(path, json.dumps(defn, indent=2, ensure_ascii=False))

                # Load into manager
                try:
                    loaded = SkillDefinition(path)
                    self._definitions[loaded.name] = loaded
                except Exception as e:
                    logger.error(f"Failed to load approved skill {defn['name']}: {e}")

                proposal.status = "approved"
                proposal.reviewed_at = datetime.now(timezone.utc).isoformat()
                self._save_creation_proposals()
                logger.info(f"Approved skill creation: {defn['name']}")
                return defn
        return None

    def reject_creation_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Reject a creation proposal with an optional reason."""
        for proposal in self._creation_proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                proposal.status = "rejected"
                proposal.reviewed_at = datetime.now(timezone.utc).isoformat()
                proposal.reject_reason = reason or None
                self._save_creation_proposals()
                logger.info(f"Rejected skill creation: {proposal_id} — {reason}")
                return True
        return False

    def _save_creation_proposals(self) -> None:
        self.ensure_definitions_dir()
        atomic_write(
            self._creation_proposals_file,
            json.dumps([p.to_dict() for p in self._creation_proposals], indent=2),
        )


# Singleton
skill_manager = SkillManager()
