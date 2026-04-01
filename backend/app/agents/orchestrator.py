"""Meta-Orchestrator — coordinates all Istara agents autonomously.

During development and runtime, this orchestrator:
1. Manages agent lifecycle (start, stop, health)
2. Prevents duplicate/conflicting work
3. Distributes tasks respecting resource limits
4. Cross-checks agent outputs for consistency
5. Detects gaps and assigns work proactively
6. Maintains an audit trail of all agent actions

Agents under management:
- DevOps Audit Agent: code quality, data integrity, system health
- UI Audit Agent: heuristics, accessibility, consistency
- UX Evaluation Agent: platform usability, onboarding, user flows
- User Simulation Agent: end-to-end testing, simulated usage
- Task Executor Agent: the main worker (picks Kanban tasks, runs skills)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.core.resource_governor import governor
from app.api.websocket import broadcast_agent_status

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    TASK_EXECUTOR = "task_executor"
    DEVOPS_AUDIT = "devops_audit"
    UI_AUDIT = "ui_audit"
    UX_EVALUATION = "ux_evaluation"
    USER_SIMULATION = "user_simulation"


class AgentState(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ManagedAgent:
    """An agent managed by the orchestrator."""

    id: str
    role: AgentRole
    name: str
    system_prompt: str  # Configurable per-agent system prompt
    state: AgentState = AgentState.IDLE
    current_task: str = ""
    last_output: str = ""
    error_count: int = 0
    executions: int = 0
    started_at: datetime | None = None
    last_active: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "name": self.name,
            "state": self.state.value,
            "current_task": self.current_task,
            "error_count": self.error_count,
            "executions": self.executions,
            "system_prompt_preview": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


# Agent ID -> Role mapping for identity loading
_ROLE_AGENT_IDS = {
    AgentRole.TASK_EXECUTOR: "istara-main",
    AgentRole.DEVOPS_AUDIT: "istara-devops",
    AgentRole.UI_AUDIT: "istara-ui-audit",
    AgentRole.UX_EVALUATION: "istara-ux-eval",
    AgentRole.USER_SIMULATION: "istara-sim",
}

# Short fallback prompts (used only if persona MD files are missing)
_FALLBACK_PROMPTS = {
    AgentRole.TASK_EXECUTOR: "You are Istara, the primary research coordinator. You orchestrate UX research workflows, execute analytical skills, and synthesize findings.",
    AgentRole.DEVOPS_AUDIT: "You are Sentinel, the DevOps audit agent. You monitor data integrity, system health, and operational reliability.",
    AgentRole.UI_AUDIT: "You are Pixel, the UI audit agent. You evaluate interfaces against Nielsen's heuristics and WCAG 2.2 AA standards.",
    AgentRole.UX_EVALUATION: "You are Sage, the UX evaluation agent. You evaluate the end-to-end experience from a human-centered design perspective.",
    AgentRole.USER_SIMULATION: "You are Echo, the user simulation agent. You rigorously test the platform by simulating realistic research workflows.",
}


def _load_role_prompt(role: AgentRole) -> str:
    """Load the full system prompt for a role from persona MD files.

    Falls back to a short default if persona files are missing.
    """
    try:
        from app.core.agent_identity import load_agent_identity
        agent_id = _ROLE_AGENT_IDS.get(role, "")
        if agent_id:
            identity = load_agent_identity(agent_id)
            if identity:
                return identity
    except Exception:
        pass
    return _FALLBACK_PROMPTS.get(role, "You are a Istara agent.")


# Legacy alias — some code references DEFAULT_SYSTEM_PROMPTS directly
DEFAULT_SYSTEM_PROMPTS = _FALLBACK_PROMPTS


class MetaOrchestrator:
    """Coordinates all Istara agents, preventing conflicts and ensuring coverage."""

    def __init__(self) -> None:
        self._agents: dict[str, ManagedAgent] = {}
        self._running = False
        self._cycle_interval = 60  # seconds between orchestration cycles
        self._work_log: list[dict] = []  # Audit trail

    def _create_default_agents(self) -> None:
        """Create the default set of managed agents with full persona identities."""
        # Agent display names (persona names)
        _role_names = {
            AgentRole.TASK_EXECUTOR: "Istara",
            AgentRole.DEVOPS_AUDIT: "Sentinel",
            AgentRole.UI_AUDIT: "Pixel",
            AgentRole.UX_EVALUATION: "Sage",
            AgentRole.USER_SIMULATION: "Echo",
        }
        for role in AgentRole:
            agent_id = _ROLE_AGENT_IDS.get(role, f"istara-{role.value}")
            if agent_id not in self._agents:
                self._agents[agent_id] = ManagedAgent(
                    id=agent_id,
                    role=role,
                    name=_role_names.get(role, role.value.replace("_", " ").title()),
                    system_prompt=_load_role_prompt(role),
                )

    async def start(self) -> None:
        """Start the meta-orchestrator."""
        self._running = True
        self._create_default_agents()
        logger.info(f"Meta-Orchestrator started with {len(self._agents)} agents.")

        while self._running:
            try:
                await self._orchestration_cycle()
            except Exception as e:
                logger.error(f"Orchestration cycle error: {e}")

            await asyncio.sleep(self._cycle_interval)

    def stop(self) -> None:
        self._running = False
        for agent in self._agents.values():
            agent.state = AgentState.STOPPED
        logger.info("Meta-Orchestrator stopped.")

    def _compute_swarm_tier(self) -> str:
        """Determine swarm tier based on local resources + compute pool."""
        try:
            from app.core.compute_pool import compute_pool
            pool_nodes = compute_pool.total_capacity()
        except Exception:
            pool_nodes = 0

        total = 1 + pool_nodes  # 1 for local
        if total >= 8:
            return "full_swarm"
        elif total >= 4:
            return "standard"
        elif total >= 2:
            return "conservative"
        elif total >= 1:
            return "minimal"
        return "paused"

    async def _orchestration_cycle(self) -> None:
        """Run one orchestration cycle."""
        budget = governor.compute_budget()

        if budget.paused:
            # Pause all agents and notify user
            for agent in self._agents.values():
                if agent.state == AgentState.WORKING:
                    agent.state = AgentState.PAUSED
                    self._log_action(agent.id, "paused", "Resource pressure — system paused")
            try:
                from app.api.websocket import broadcast_resource_throttle
                await broadcast_resource_throttle(
                    "System resources under pressure — agents paused",
                    budget.__dict__ if hasattr(budget, "__dict__") else {},
                )
            except Exception:
                pass
            return

        # Resume paused agents if resources allow
        for agent in self._agents.values():
            if agent.state == AgentState.PAUSED:
                agent.state = AgentState.IDLE
                self._log_action(agent.id, "resumed", "Resources available")

        # Dynamic swarm orchestration — adjust based on compute pool
        swarm_tier = self._compute_swarm_tier()
        self._log_action("orchestrator", "swarm_tier", f"Current tier: {swarm_tier}")

        # Sync sub-agent states from their actual running instances
        await self._sync_sub_agent_states()

        # Check for conflicts — no two agents should work on the same data
        active_tasks = {a.current_task for a in self._agents.values() if a.current_task}
        if len(active_tasks) != len([a for a in self._agents.values() if a.current_task]):
            logger.warning("Conflict detected: multiple agents on same task!")
            seen: set[str] = set()
            for agent in self._agents.values():
                if agent.current_task in seen:
                    agent.current_task = ""
                    agent.state = AgentState.IDLE
                    self._log_action(agent.id, "deconflicted", "Duplicate task assignment removed")
                elif agent.current_task:
                    seen.add(agent.current_task)

        # Check agent health
        for agent in self._agents.values():
            if agent.error_count >= 3:
                agent.state = AgentState.PAUSED
                self._log_action(agent.id, "paused", f"Too many errors ({agent.error_count})")

        # Distribute unassigned tasks
        await self._distribute_pending_tasks()

    async def _sync_sub_agent_states(self) -> None:
        """Sync managed agent states from actual running sub-agent instances."""
        try:
            from app.agents.devops_agent import devops_agent
            from app.agents.ui_audit_agent import ui_audit_agent
            from app.agents.ux_eval_agent import ux_eval_agent
            from app.agents.user_sim_agent import user_sim_agent

            agent_map = {
                "istara-devops": devops_agent,
                "istara-ui-audit": ui_audit_agent,
                "istara-ux-eval": ux_eval_agent,
                "istara-sim": user_sim_agent,
            }

            for agent_id, real_agent in agent_map.items():
                managed = self._agents.get(agent_id)
                if not managed:
                    continue

                # Update running state
                if hasattr(real_agent, "_running") and real_agent._running:
                    if managed.state == AgentState.STOPPED:
                        managed.state = AgentState.IDLE

                    # Check for reports to track executions
                    reports = []
                    if hasattr(real_agent, "_reports"):
                        reports = real_agent._reports
                    elif hasattr(real_agent, "_audit_log"):
                        reports = real_agent._audit_log

                    new_count = len(reports)
                    if new_count > managed.executions:
                        managed.executions = new_count
                        managed.last_active = datetime.now(timezone.utc)

                        # Get latest report summary
                        if reports:
                            latest = reports[-1]
                            if isinstance(latest, dict):
                                managed.last_output = str(latest.get("summary", latest.get("status", "")))[:200]
                            else:
                                managed.last_output = str(getattr(latest, "overall_score", ""))[:200]
                else:
                    managed.state = AgentState.STOPPED

        except Exception as e:
            logger.error(f"Sub-agent state sync error: {e}")

    async def _distribute_pending_tasks(self) -> None:
        """Route unassigned tasks to the best agent based on specialties."""
        try:
            from app.models.database import async_session
            from app.models.task import Task, TaskStatus
            from app.core.task_router import route_task
            from app.services.a2a import send_message
            from sqlalchemy import select

            async with async_session() as db:
                result = await db.execute(
                    select(Task)
                    .where(
                        Task.status == TaskStatus.BACKLOG,
                        Task.agent_id.is_(None),
                    )
                    .order_by(Task.created_at.asc())
                    .limit(10)
                )
                tasks = result.scalars().all()

                if not tasks:
                    return

                for task in tasks:
                    # Route using the intelligent task router
                    routing = await route_task(
                        db,
                        task.title,
                        task.description or "",
                        task.skill_name,
                    )

                    task.agent_id = routing["primary_agent_id"]

                    # Merge any existing A2A collaboration responses into task context
                    try:
                        from app.services.a2a import get_messages
                        collab_responses = await get_messages(db, routing["primary_agent_id"], limit=10)
                        for resp in collab_responses:
                            resp_type = resp.get("message_type") if isinstance(resp, dict) else getattr(resp, "message_type", "")
                            if resp_type != "collaboration_response":
                                continue
                            resp_meta = resp.get("metadata", {}) if isinstance(resp, dict) else getattr(resp, "metadata", {})
                            if isinstance(resp_meta, str):
                                resp_meta = json.loads(resp_meta) if resp_meta else {}
                            if resp_meta.get("task_id") == task.id:
                                resp_from = resp.get("from_agent_id", "") if isinstance(resp, dict) else getattr(resp, "from_agent_id", "")
                                resp_content = resp.get("content", "") if isinstance(resp, dict) else getattr(resp, "content", "")
                                collab_context = f"\n[{resp_from} analysis]: {resp_content[:500]}"
                                task.user_context = (task.user_context or "") + collab_context
                    except Exception as e:
                        logger.debug(f"Collaboration response merge skipped: {e}")

                    self._log_action(
                        routing["primary_agent_id"],
                        "task_assigned",
                        f"Auto-routed: {task.title} ({routing['routing_reason']})",
                    )

                    # Detect capability gaps when routing falls back to istara-main
                    if (
                        routing["primary_agent_id"] == "istara-main"
                        and "fallback" in routing.get("routing_reason", "").lower()
                    ):
                        try:
                            from app.core.agent_factory import AgentFactory
                            from app.core.task_router import get_available_agents

                            factory = AgentFactory()
                            available_agents = await get_available_agents(db)
                            agents_list = [
                                a.to_dict()
                                for a in available_agents
                                if a.is_active
                            ]
                            gap = factory.detect_capability_gap(
                                routing.get("specialties_needed", []),
                                agents_list,
                            )
                            if gap:
                                proposal = factory.propose_agent_creation(
                                    gap,
                                    task.title,
                                    task.description or "",
                                    task.id,
                                    routing.get("specialties_needed", []),
                                )
                                logger.info(
                                    f"Agent creation proposed: {proposal.proposed_name}"
                                )
                                self._log_action(
                                    "orchestrator",
                                    "agent_proposal",
                                    f"Proposed new agent: {proposal.proposed_name} — {gap}",
                                )
                                try:
                                    from app.api.websocket import manager as ws_manager

                                    await ws_manager.broadcast(
                                        "agent_creation_proposed",
                                        {
                                            "proposal_id": proposal.id,
                                            "proposed_name": proposal.proposed_name,
                                            "reason": gap,
                                        },
                                    )
                                except Exception:
                                    pass
                        except Exception as e:
                            logger.debug(f"Agent gap detection skipped: {e}")

                    # Send A2A collaboration requests for multi-specialty tasks
                    for collab_id in routing.get("collaborators", []):
                        try:
                            await send_message(
                                db=db,
                                from_agent_id=routing["primary_agent_id"],
                                to_agent_id=collab_id,
                                message_type="collaboration_request",
                                content=f"Task '{task.title}' needs your expertise. Specialties: {', '.join(routing['specialties_needed'])}. Please review when complete and provide feedback.",
                                metadata={
                                    "task_id": task.id,
                                    "task_title": task.title,
                                    "specialties_needed": routing["specialties_needed"],
                                },
                            )
                        except Exception as e:
                            logger.warning(f"A2A collab request failed: {e}")

                await db.commit()
                assigned_agents = set(t.agent_id for t in tasks)
                logger.info(f"Distributed {len(tasks)} tasks to agents: {assigned_agents}")

                # Wake the appropriate agent orchestrators
                for agent_id in assigned_agents:
                    try:
                        if agent_id == "istara-main":
                            from app.core.agent import agent as agent_orchestrator
                            agent_orchestrator.wake()
                        # Sub-agents are woken via their own check cycles
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Task distribution error: {e}")

    def _log_action(self, agent_id: str, action: str, details: str) -> None:
        """Log an orchestrator action for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "action": action,
            "details": details,
        }
        self._work_log.append(entry)
        if len(self._work_log) > 500:
            self._work_log = self._work_log[-500:]

    # --- Agent Management API ---

    def get_agent(self, agent_id: str) -> ManagedAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[ManagedAgent]:
        return list(self._agents.values())

    def update_agent_prompt(self, agent_id: str, system_prompt: str) -> bool:
        """Update an agent's system prompt."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.system_prompt = system_prompt
        self._log_action(agent_id, "prompt_updated", f"System prompt updated ({len(system_prompt)} chars)")
        return True

    def create_custom_agent(self, name: str, role: AgentRole, system_prompt: str) -> ManagedAgent:
        """Create a custom agent with a user-defined system prompt."""
        agent_id = f"custom-{uuid.uuid4().hex[:8]}"
        agent = ManagedAgent(
            id=agent_id,
            role=role,
            name=name,
            system_prompt=system_prompt,
        )
        self._agents[agent_id] = agent
        self._log_action(agent_id, "created", f"Custom agent: {name}")
        return agent

    def pause_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.state = AgentState.PAUSED
        self._log_action(agent_id, "paused", "Manual pause")
        return True

    def resume_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent or agent.state != AgentState.PAUSED:
            return False
        agent.state = AgentState.IDLE
        self._log_action(agent_id, "resumed", "Manual resume")
        return True

    def get_work_log(self, limit: int = 50) -> list[dict]:
        return self._work_log[-limit:]

    def get_status(self) -> dict:
        """Get full orchestrator status."""
        return {
            "running": self._running,
            "agents": [a.to_dict() for a in self._agents.values()],
            "active_count": sum(1 for a in self._agents.values() if a.state == AgentState.WORKING),
            "paused_count": sum(1 for a in self._agents.values() if a.state == AgentState.PAUSED),
            "resource_status": governor.get_status(),
            "recent_actions": self._work_log[-10:],
        }


# Singleton
meta_orchestrator = MetaOrchestrator()
