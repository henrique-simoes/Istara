"""Autonomous skill creation workflow."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.checkpoint import atomic_write
from app.skills.skill_models import (
    SkillCreationProposal,
    SkillDefinition,
    runtime_skills_dir,
    writeable_skill_path,
)

logger = logging.getLogger(__name__)


class SkillCreationMixin:
    def propose_skill_creation(
        self,
        definition: dict,
        source_task_id: str,
        agent_id: str,
        reason: str,
        confidence: int,
    ) -> SkillCreationProposal:
        """Create a proposal for a brand-new skill definition."""
        required = [
            "name",
            "display_name",
            "description",
            "phase",
            "skill_type",
            "plan_prompt",
            "execute_prompt",
            "output_schema",
        ]
        missing = [field for field in required if field not in definition]
        if missing:
            raise ValueError(f"Proposed definition missing required fields: {missing}")

        from app.core.content_guard import ContentGuard

        guard = ContentGuard()
        for prompt_field in ("plan_prompt", "execute_prompt"):
            scan = guard.scan_text(definition[prompt_field])
            if not scan.clean and scan.threat_level in ("high", "medium"):
                raise ValueError(f"ContentGuard flagged {prompt_field}: {scan.threats}")

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
        logger.info("Proposed new skill creation: %s (confidence=%s)", definition["name"], confidence)
        return proposal

    def get_pending_creation_proposals(self) -> list[SkillCreationProposal]:
        """Return creation proposals with status == 'pending'."""
        return [p for p in self._creation_proposals if p.status == "pending"]

    def get_all_creation_proposals(self, limit: int = 20) -> list[SkillCreationProposal]:
        """Return the last N creation proposals."""
        return self._creation_proposals[-limit:]

    async def verify_skill_proposal(self, proposal_id: str) -> dict:
        """Run automatic verification on a proposed skill before human approval."""
        proposal = next((p for p in self._creation_proposals if p.id == proposal_id), None)
        if not proposal or proposal.status != "pending":
            return {"passed": False, "issues": ["Proposal not found or not pending"]}

        defn = proposal.proposed_definition
        try:
            import asyncio
            import importlib

            from app.skills.base import SkillInput

            registry = importlib.import_module("app.skills.registry").registry
            self.ensure_definitions_dir()
            test_path = runtime_skills_dir() / f"_test_{defn.get('name', 'unknown')}.json"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            defn.setdefault("version", "1.0.0")
            defn.setdefault("enabled", True)
            atomic_write(test_path, json.dumps(defn, indent=2, ensure_ascii=False))

            loaded = SkillDefinition(test_path)
            test_input = SkillInput(
                project_id="__verification_test__",
                user_context=(
                    f"Verification test for skill: {loaded.display_name}. "
                    "Generate a minimal sample output demonstrating this skill works."
                ),
            )
            skill = registry.get(loaded.name) if loaded.name in registry.list_names() else None
            if not skill:
                self._definitions[loaded.name] = loaded
                skill = registry.get(loaded.name)

            if skill:
                output = await asyncio.wait_for(skill.execute(test_input), timeout=60)
                issues = await skill.validate_output(output)
                result = {
                    "passed": output.success and len(issues) <= 3,
                    "issues": issues[:5] if issues else [],
                    "test_output": (output.summary or "")[:500],
                }
            else:
                result = {"passed": False, "issues": ["Could not instantiate skill for testing"]}

            test_path.unlink(missing_ok=True)
            if loaded.name in self._definitions and self._definitions[loaded.name].path == test_path:
                del self._definitions[loaded.name]

            proposal.test_result = result
            self._save_creation_proposals()
            logger.info(
                "Skill verification %s: %s",
                "PASSED" if result["passed"] else "FAILED",
                defn.get("name"),
            )
            return result
        except Exception as e:
            test_path = runtime_skills_dir() / f"_test_{defn.get('name', 'unknown')}.json"
            test_path.unlink(missing_ok=True)
            return {"passed": False, "issues": [f"Verification error: {str(e)[:200]}"]}

    def approve_creation_proposal(self, proposal_id: str) -> dict | None:
        """Approve a creation proposal and write the skill JSON."""
        for proposal in self._creation_proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                if isinstance(proposal.test_result, dict) and not proposal.test_result.get("passed", True):
                    logger.warning(
                        "Skill approval blocked; verification failed: %s",
                        proposal.test_result.get("issues"),
                    )
                    proposal.status = "testing_failed"
                    self._save_creation_proposals()
                    return None

                defn = proposal.proposed_definition
                defn.setdefault("version", "1.0.0")
                defn.setdefault("enabled", True)
                defn["created_at"] = datetime.now(timezone.utc).isoformat()
                defn.setdefault(
                    "changelog",
                    [
                        {
                            "version": "1.0.0",
                            "date": defn["created_at"],
                            "changes": "Initial creation via autonomous proposal (verified)",
                        }
                    ],
                )

                self.ensure_definitions_dir()
                path = writeable_skill_path(defn["name"])
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(path, json.dumps(defn, indent=2, ensure_ascii=False))

                try:
                    loaded = SkillDefinition(path)
                    self._definitions[loaded.name] = loaded
                except Exception as e:
                    logger.error("Failed to load approved skill %s: %s", defn["name"], e)

                proposal.status = "approved"
                proposal.reviewed_at = datetime.now(timezone.utc).isoformat()
                self._save_creation_proposals()
                logger.info("Approved skill creation: %s", defn["name"])
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
                logger.info("Rejected skill creation: %s - %s", proposal_id, reason)
                return True
        return False

    def _save_creation_proposals(self) -> None:
        self.ensure_definitions_dir()
        atomic_write(
            self._creation_proposals_file,
            json.dumps([p.to_dict() for p in self._creation_proposals], indent=2),
        )
