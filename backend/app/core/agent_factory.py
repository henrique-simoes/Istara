"""Agent Factory — automatic agent creation inspired by Memento-Skills.

When the system detects tasks requiring capabilities no existing agent covers,
it proposes new specialized agents for user approval.

Reference: Zhou et al. (2026). "Memento-Skills: Let Agents Design Agents."
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
PROPOSALS_FILE = DATA_DIR / "_agent_proposals.json"


@dataclass
class AgentCreationProposal:
    id: str
    proposed_name: str
    proposed_role: str
    proposed_system_prompt: str
    proposed_specialties: list[str]
    proposed_core_md: str
    source_task_id: str
    reason: str
    confidence: int  # 0-100
    status: str = "pending"  # pending|approved|rejected
    created_at: str = ""
    reviewed_at: str | None = None


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


class AgentFactory:
    """Detects capability gaps and proposes new agent creation."""

    def __init__(self) -> None:
        self._proposals: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load proposals from disk."""
        if PROPOSALS_FILE.exists():
            try:
                self._proposals = json.loads(PROPOSALS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._proposals = []

    def _save(self) -> None:
        """Persist proposals to disk using atomic write."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write(PROPOSALS_FILE, json.dumps(self._proposals, indent=2))

    def detect_capability_gap(
        self,
        task_specialties: list[str],
        available_agents: list[dict],
    ) -> str | None:
        """Check if any agent covers >= 60% of task specialties.

        Args:
            task_specialties: List of specialty domains needed for the task.
            available_agents: List of agent dicts with 'specialties' field.

        Returns:
            Gap description string if gap detected, None if covered.
        """
        if not task_specialties:
            return None

        best_coverage = 0.0
        for agent in available_agents:
            agent_specs = agent.get("specialties", [])
            if isinstance(agent_specs, str):
                try:
                    agent_specs = json.loads(agent_specs)
                except (json.JSONDecodeError, TypeError):
                    agent_specs = []
            overlap = len(set(task_specialties) & set(agent_specs))
            coverage = overlap / len(task_specialties) if task_specialties else 0
            best_coverage = max(best_coverage, coverage)

        if best_coverage >= 0.6:
            return None  # adequately covered

        uncovered = [
            s
            for s in task_specialties
            if not any(
                s
                in (
                    agent.get("specialties", [])
                    if isinstance(agent.get("specialties"), list)
                    else json.loads(agent.get("specialties", "[]"))
                )
                for agent in available_agents
            )
        ]
        return (
            f"No agent covers specialties: {', '.join(uncovered)} "
            f"(best coverage: {best_coverage:.0%})"
        )

    def propose_agent_creation(
        self,
        gap_description: str,
        task_title: str,
        task_description: str,
        task_id: str,
        specialties_needed: list[str],
    ) -> AgentCreationProposal:
        """Create a proposal for a new agent based on capability gap."""
        # Generate agent name from specialties
        primary_specialty = specialties_needed[0] if specialties_needed else "general"
        agent_name = f"reclaw-{primary_specialty}"

        # Generate role description
        role = f"Specialized agent for {', '.join(specialties_needed)} tasks"

        # Generate system prompt
        system_prompt = (
            f"You are a specialized ReClaw agent focused on "
            f"{', '.join(specialties_needed)}. "
            f"Your role is to handle tasks requiring expertise in these domains. "
            f"Follow the Atomic Research methodology and produce structured findings."
        )

        # Generate CORE.md
        core_md = (
            f"# {agent_name.replace('reclaw-', '').title()} Agent\n"
            f"\n"
            f"## Identity\n"
            f"I am **{agent_name}**, a specialized ReClaw agent created to fill "
            f"a capability gap in {', '.join(specialties_needed)}.\n"
            f"\n"
            f"## Purpose\n"
            f"{role}\n"
            f"\n"
            f"## Created Because\n"
            f"{gap_description}\n"
            f"\n"
            f"## Communication Style\n"
            f"- Evidence-driven and methodical\n"
            f"- Follow Atomic Research methodology\n"
            f"- Produce structured findings (nuggets, facts, insights, recommendations)\n"
            f"\n"
            f"## Collaboration\n"
            f"- Participate in A2A messaging with other ReClaw agents\n"
            f"- Accept task routing for matching specialties\n"
            f"- Report findings through standard ReClaw protocols\n"
        )

        proposal = AgentCreationProposal(
            id=f"agent_{uuid.uuid4().hex[:12]}",
            proposed_name=agent_name,
            proposed_role=role,
            proposed_system_prompt=system_prompt,
            proposed_specialties=specialties_needed,
            proposed_core_md=core_md,
            source_task_id=task_id,
            reason=gap_description,
            confidence=65,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        self._proposals.append(asdict(proposal))
        self._save()
        return proposal

    def get_pending_proposals(self) -> list[dict]:
        """Return proposals awaiting review."""
        return [p for p in self._proposals if p.get("status") == "pending"]

    def get_all_proposals(self, limit: int = 20) -> list[dict]:
        """Return the most recent proposals (all statuses)."""
        return self._proposals[-limit:]

    def approve_proposal(self, proposal_id: str) -> dict | None:
        """Approve a proposal -- returns the proposal data for agent creation."""
        for p in self._proposals:
            if p["id"] == proposal_id and p["status"] == "pending":
                p["status"] = "approved"
                p["reviewed_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                self._save()
                return p
        return None

    def reject_proposal(self, proposal_id: str, reason: str = "") -> dict | None:
        """Reject a proposal with optional reason."""
        for p in self._proposals:
            if p["id"] == proposal_id and p["status"] == "pending":
                p["status"] = "rejected"
                p["reviewed_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                if reason:
                    p["reject_reason"] = reason
                self._save()
                return p
        return None
