"""Update proposal workflow for existing skills."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.core.checkpoint import atomic_write
from app.skills.skill_models import SkillUpdateProposal

logger = logging.getLogger(__name__)


class SkillProposalMixin:
    @staticmethod
    def _require_proposal_project_id(project_id: str | None) -> str:
        scoped_project_id = str(project_id or "").strip()
        if not scoped_project_id:
            raise ValueError("project_id is required for skill improvement proposals")
        return scoped_project_id

    def propose_improvement(
        self,
        skill_name: str,
        field: str,
        current_value: str,
        proposed_value: str,
        reason: str,
        confidence: float = 0.5,
        project_id: str = "",
    ) -> SkillUpdateProposal:
        """Create a proposed improvement for user review."""
        scoped_project_id = self._require_proposal_project_id(project_id)
        proposal = SkillUpdateProposal(
            skill_name,
            field,
            current_value,
            proposed_value,
            reason,
            confidence,
            project_id=scoped_project_id,
        )
        self._proposals.append(proposal)
        self._save_proposals()
        logger.info("Proposed improvement for %s.%s: %s", skill_name, field, reason)
        return proposal

    def _matches_project(self, proposal: SkillUpdateProposal, project_id: str | None) -> bool:
        if project_id is None:
            return True
        scoped_project_id = str(project_id or "").strip()
        return bool(scoped_project_id) and proposal.project_id == scoped_project_id

    def get_pending_proposals(self, project_id: str | None = None) -> list[SkillUpdateProposal]:
        return [
            p
            for p in self._proposals
            if p.status == "pending" and self._matches_project(p, project_id)
        ]

    def get_all_proposals(
        self,
        limit: int = 50,
        project_id: str | None = None,
    ) -> list[SkillUpdateProposal]:
        return [p for p in self._proposals if self._matches_project(p, project_id)][-limit:]

    def approve_proposal(self, proposal_id: str, project_id: str | None = None) -> bool:
        """Approve and apply a proposed improvement."""
        for proposal in self._proposals:
            if (
                proposal.id == proposal_id
                and proposal.status == "pending"
                and self._matches_project(proposal, project_id)
            ):
                proposal.status = "approved"
                proposal.reviewed_at = datetime.now(UTC).isoformat()
                try:
                    self.update_skill(
                        proposal.skill_name,
                        {proposal.field: proposal.proposed_value},
                        f"Self-improvement applied: {proposal.reason}",
                    )
                except Exception as e:
                    logger.error("Failed to apply proposal %s: %s", proposal_id, e)
                    proposal.status = "failed"
                self._save_proposals()
                return True
        return False

    def reject_proposal(
        self,
        proposal_id: str,
        reason: str = "",
        project_id: str | None = None,
    ) -> bool:
        """Reject a proposed improvement."""
        for proposal in self._proposals:
            if (
                proposal.id == proposal_id
                and proposal.status == "pending"
                and self._matches_project(proposal, project_id)
            ):
                proposal.status = "rejected"
                proposal.reviewed_at = datetime.now(UTC).isoformat()
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
