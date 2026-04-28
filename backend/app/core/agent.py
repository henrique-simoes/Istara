"""Agent Orchestrator — the autonomous work loop that makes Istara an agent.

This is the brain of Istara. It:
1. Picks tasks from the Kanban board (highest priority first)
2. Selects the appropriate skill for each task
3. Executes the skill with project context
4. Stores outputs (nuggets, facts, insights, recommendations) in the database
5. Updates task progress via WebSocket
6. Self-checks findings against sources
7. Generates suggestions for the user
8. Loops continuously, respecting resource limits
9. Checkpoints progress for crash recovery
10. Proposes new skills when patterns emerge
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.datetime_utils import ensure_utc
from app.core.steering import steering_manager
from app.core.ollama import ollama
from app.core.rag import retrieve_context, ingest_chunks
from app.core.self_check import verify_claim, Confidence
from app.core.file_processor import process_file
from app.core.embeddings import TextChunk
from app.core.context_hierarchy import context_hierarchy
from app.core.resource_governor import governor
from app.core.telemetry import telemetry_recorder
from app.models.database import async_session
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.agent import Agent, AgentState
from app.api.websocket import (
    broadcast_agent_status,
    broadcast_task_progress,
    broadcast_suggestion,
    broadcast_task_queue_update,
    broadcast_finding_created,
    broadcast_agent_thinking,
    broadcast_plan_progress,
)
from app.core.checkpoint import create_checkpoint, update_checkpoint, complete_checkpoint
from app.skills.registry import registry
from app.skills.base import SkillInput, SkillOutput
from app.core.agent_hooks import agent_hooks
from app.skills.skill_manager import skill_manager

logger = logging.getLogger(__name__)


def _resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


@dataclass
class ResearchStep:
    """A single step in a research plan."""

    id: str
    description: str
    skill_name: str | None = None
    status: str = "pending"  # pending | executing | completed | failed
    result: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class ResearchPlan:
    """A decomposed research plan with ordered steps."""

    question: str
    steps: list[ResearchStep] = field(default_factory=list)
    past_steps: list[ResearchStep] = field(default_factory=list)
    status: str = "planning"  # planning | executing | replanning | complete

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "status": self.status,
            "steps": [
                {
                    "id": s.id,
                    "desc": s.description,
                    "skill": s.skill_name,
                    "status": s.status,
                    "result": s.result[:200],
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "completed": [
                {"id": s.id, "desc": s.description, "status": s.status} for s in self.past_steps
            ],
        }


class AgentOrchestrator:
    """Autonomous agent that picks tasks and runs skills."""

    def __init__(self, agent_id: str = "istara-main") -> None:
        self._running = False
        self._agent_id = agent_id
        self._current_task_id: str | None = None
        self._loop_interval = 30  # seconds between task checks
        self._idle_interval = 60  # seconds when no tasks available

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def start(self) -> None:
        """Start the autonomous work loop."""
        self._running = True
        self._wake_event = asyncio.Event()
        logger.info("Agent Orchestrator started.")
        await broadcast_agent_status("idle", "Agent ready, watching for tasks.")

        while self._running:
            try:
                executed = await self._work_cycle()
                interval = self._loop_interval if executed else self._idle_interval
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Agent work cycle error: {error_msg}")
                await broadcast_agent_status(
                    "warning", f"Agent recovered from error: {error_msg[:100]}. Retrying..."
                )
                interval = self._idle_interval
                # Record the error for learning
                try:
                    from app.core.agent_learning import agent_learning

                    await agent_learning.record_error_learning(
                        agent_id=self._agent_id,
                        error_message=error_msg,
                        resolution="Caught in work loop, retrying next cycle",
                    )
                except Exception:
                    pass

            # Wait for interval OR immediate wake signal
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=interval)
                self._wake_event.clear()
            except asyncio.TimeoutError:
                pass

    def wake(self) -> None:
        """Wake the agent immediately to check for new tasks (e.g. after task assignment)."""
        if hasattr(self, "_wake_event"):
            self._wake_event.set()

    def stop(self) -> None:
        self._running = False
        logger.info("Agent Orchestrator stopped.")

    async def _persist_agent_state(self, state: AgentState, current_task: str = "") -> None:
        """Persist the agent state to the database so the frontend can read it."""
        try:
            async with async_session() as db:
                result = await db.execute(select(Agent).where(Agent.id == self._agent_id))
                agent_row = result.scalar_one_or_none()
                if agent_row:
                    agent_row.state = state
                    agent_row.current_task = current_task
                    if state == AgentState.WORKING:
                        agent_row.last_heartbeat_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist agent state: {e}")

    async def _work_cycle(self) -> bool:
        """Run one work cycle. Returns True if a task was executed."""
        # ── Check steering queue FIRST — if there are pending steering
        # messages, create a steering task and execute it before checking
        # the normal task queue. This implements pi-mono's steering pattern:
        # steering messages are injected while the agent is idle or working,
        # and picked up at the next opportunity.
        steering_msgs = await steering_manager.get_steering(self._agent_id)
        if steering_msgs:
            logger.info(f"Steering messages detected for {self._agent_id}: {len(steering_msgs)}")
            for msg in steering_msgs:
                await self._execute_steering_message(msg)
            return True

        # Check resource budget before doing work
        can_start, reason = governor.can_start_agent("task-executor")
        if not can_start:
            logger.info(f"Agent paused: {reason}")
            await broadcast_agent_status("paused", f"Hardware throttle: {reason}")
            return False

        # Apply throttle if system is under pressure
        await governor.throttle_if_needed()

        # Check LLM availability — don't pick tasks if no LLM is reachable
        from app.core.compute_registry import compute_registry

        if not compute_registry.has_available_node():
            await broadcast_agent_status("paused", "Waiting for LLM — no servers available")
            await compute_registry.broadcast_llm_status(
                "llm_unavailable", "No LLM servers available. Agent work paused."
            )
            return False

        async with async_session() as db:
            # 0. Process A2A inbox (collaboration requests from other agents)
            await self._process_a2a_inbox(db)

            # 1. Find the next task to work on
            task = await self._pick_next_task(db)
            if not task:
                return False

            # 2. Get the project context
            project = await self._get_project(db, task.project_id)
            if not project:
                logger.warning(f"Project not found for task {task.id} — marking as done (orphaned)")
                task.status = TaskStatus.DONE
                await db.commit()
                return False

            # 3. Execute the task (register with governor for concurrent limits)
            governor.register_agent("task-executor")
            self._current_task_id = task.id
            await steering_manager.mark_working(self._agent_id)
            try:
                await self._execute_task(db, task, project)
            finally:
                self._current_task_id = None
                governor.unregister_agent("task-executor")
                await steering_manager.mark_idle(self._agent_id)

            # 4. Check queue depth and adapt loop interval
            pending_result = await db.execute(
                select(func.count(Task.id)).where(Task.status == TaskStatus.BACKLOG)
            )
            in_progress_result = await db.execute(
                select(func.count(Task.id)).where(Task.status == TaskStatus.IN_PROGRESS)
            )
            done_result = await db.execute(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.DONE,
                    Task.project_id == task.project_id,
                )
            )
            pending = pending_result.scalar() or 0
            in_progress = in_progress_result.scalar() or 0
            completed = done_result.scalar() or 0

            # Broadcast queue update to frontend
            await broadcast_task_queue_update(task.project_id, pending, in_progress, completed)

            if (pending + in_progress) > 0:
                self._loop_interval = 5  # Process queue quickly
                await broadcast_agent_status(
                    "working", f"Task complete. {pending + in_progress} remaining in queue."
                )
            else:
                self._loop_interval = 30  # Back to normal
                await broadcast_agent_status("idle", "All tasks processed.")

            # ── Check follow-up queue — only processed when agent would
            # otherwise stop (no more tasks in the pipeline). This matches
            # pi-mono's followUpQueue pattern.
            follow_up_msgs = await steering_manager.get_follow_up(self._agent_id)
            if follow_up_msgs:
                logger.info(f"Follow-up messages for {self._agent_id}: {len(follow_up_msgs)}")
                for msg in follow_up_msgs:
                    await self._execute_steering_message(msg)
                return True

            return True

    async def _execute_steering_message(self, msg) -> None:
        """Execute a steering message as an interim task.

        Steering messages are user-injected mid-execution instructions.
        They're treated as high-priority tasks that interrupt the normal
        task queue (but never interrupt a skill that's already running).

        This mirrors pi-mono's pattern where steering messages are
        delivered after the current turn completes.
        """
        from app.core.steering import SteeringMessage
        from app.models.task import Task, TaskStatus
        from app.skills.registry import load_skill

        message_text = msg.message if hasattr(msg, "message") else str(msg)
        source = msg.source if hasattr(msg, "source") else "user"
        logger.info(f"Executing steering message ({source}): {message_text[:100]}")

        # Broadcast that we're processing a steering message
        await broadcast_agent_status(
            "working", f"Processing steering message: {message_text[:80]}..."
        )

        try:
            # Create a temporary skill input from the steering message
            from app.skills.skill_manager import skill_manager
            from app.skills.registry import SkillInput

            # Try to find an appropriate skill based on the message content
            skill = None
            # Check if the message references a specific skill
            lower_msg = message_text.lower()
            if any(kw in lower_msg for kw in ["audit", "check", "review", "wcag", "accessibility"]):
                skill = skill_manager.get_skill("accessibility-audit")
            elif any(kw in lower_msg for kw in ["ux", "usability", "heuristic"]):
                skill = skill_manager.get_skill("heuristic-evaluation")
            elif any(kw in lower_msg for kw in ["analyze", "theme", "insight", "finding"]):
                skill = skill_manager.get_skill("kappa-thematic-analysis")
            elif any(kw in lower_msg for kw in ["summarize", "summary", "report"]):
                skill = skill_manager.get_skill("stakeholder-presentation")

            if skill:
                # Execute the skill with the steering message as context
                skill_input = SkillInput(
                    project_id="",  # Steering messages don't require a project
                    task_id="",
                    parameters={"mode": "analyze"},
                    user_context=message_text,
                    project_context="",
                    company_context="",
                )
                output = await asyncio.wait_for(skill.execute(skill_input), timeout=120)

                # Broadcast the result
                await broadcast_agent_status(
                    "idle",
                    f"Steering message processed ({skill.display_name}): {output.summary[:120]}..."
                    if output.summary
                    else f"Steering message processed ({skill.display_name})",
                )
            else:
                # No matching skill — use the general LLM to respond
                response = await ollama.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are Istara's main agent. Respond helpfully to the user's steering message.",
                        },
                        {"role": "user", "content": message_text},
                    ]
                )
                reply = response.get("message", {}).get("content", "")
                await broadcast_agent_status("idle", f"Steering response: {reply[:200]}...")
        except asyncio.TimeoutError:
            logger.warning("Steering message execution timed out")
            await broadcast_agent_status("warning", "Steering message timed out after 2 minutes")
        except Exception as e:
            logger.error(f"Steering message execution failed: {e}")
            await broadcast_agent_status("warning", f"Steering message failed: {str(e)[:100]}")

    def _is_in_backoff(self, task: Task) -> bool:
        """Check if a task is still within its retry backoff window."""
        if task.last_retry_at and (task.retry_count or 0) > 0:
            # Backoff delays: [5, 15, 45, 120] seconds (capped at 120)
            backoff = min(5 * (3 ** (task.retry_count - 1)), 120)
            elapsed = (datetime.now(timezone.utc) - ensure_utc(task.last_retry_at)).total_seconds()
            if elapsed < backoff:
                return True
        return False

    async def _process_a2a_inbox(self, db: AsyncSession) -> None:
        """Process pending A2A collaboration requests from other agents."""
        try:
            from app.services.a2a import get_messages, mark_read

            messages = await get_messages(db, self._agent_id, unread_only=True, limit=3)
            for msg in messages:
                msg_type = (
                    msg.get("message_type", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "message_type", "")
                )
                if msg_type == "collaboration_request":
                    await self._handle_collaboration(db, msg)
                elif msg_type == "debate_request":
                    await self._handle_debate(db, msg)
                elif msg_type == "delegate":
                    await self._handle_delegate(db, msg)
                msg_id = msg.get("id") if isinstance(msg, dict) else getattr(msg, "id", "")
                if msg_id:
                    await mark_read(db, msg_id)
        except Exception as e:
            logger.debug(f"A2A inbox check skipped: {e}")

    async def _handle_delegate(self, db: AsyncSession, msg) -> None:
        """Handle delegated tasks from other agents (e.g. MECE reporting)."""
        try:
            content_str = (
                msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            )
            if not content_str:
                return
            data = json.loads(content_str)

            if data.get("type") == "mece_report_request":
                from app.core.report_manager import report_manager
                from app.models.project_report import ProjectReport

                project_id = data.get("project_id")
                task_id = data.get("task_id")

                # 1. Ensure MECE categorization on all eligible L2/L3 reports
                result = await db.execute(
                    select(ProjectReport).where(
                        ProjectReport.project_id == project_id,
                        ProjectReport.finding_count >= 3,  # Minimum findings for meaningful MECE
                    )
                )
                reports = result.scalars().all()
                updated_count = 0
                for report in reports:
                    # Force update to consulting-grade MECE
                    await report_manager._generate_mece_categories(report, db)
                    updated_count += 1

                # 2. Trigger/Update L4 Final Report (Consulting Grade)
                # This now uses the upgraded Minto/SCR pipeline
                await report_manager._check_synthesis_trigger(project_id, db)

                # 3. Send A2A confirmation
                from app.services.a2a import send_message as a2a_send

                msg_from = (
                    msg.get("from_agent_id", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "from_agent_id", "")
                )
                await a2a_send(
                    db=db,
                    from_agent_id=self._agent_id,
                    to_agent_id=msg_from,
                    message_type="report",
                    content=f"Consulting-grade MECE reporting completed for project {project_id}. Updated {updated_count} reports.",
                    metadata={"project_id": project_id, "task_id": task_id},
                )
        except Exception as e:
            logger.error(f"Delegate handling failed: {e}", exc_info=True)

    async def _handle_collaboration(self, db: AsyncSession, msg) -> None:
        """Respond to a collaboration request with full conversation context.

        Uses context_id to maintain multi-turn threads — agents can have
        back-and-forth exchanges about a task, not just fire-and-forget.
        """
        try:
            metadata = msg.get("metadata", {}) if isinstance(msg, dict) else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata else {}
            task_id = metadata.get("task_id")
            if not task_id:
                return

            task = await db.get(Task, task_id)
            if not task or task.status not in ("backlog", "in_progress"):
                return

            msg_id = msg.get("id", "") if isinstance(msg, dict) else getattr(msg, "id", "")
            msg_from = (
                msg.get("from_agent_id", "")
                if isinstance(msg, dict)
                else getattr(msg, "from_agent_id", "")
            )
            msg_content = (
                msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            )

            # Use context_id for multi-turn conversation (or msg_id as first message)
            context_id = metadata.get("context_id") or msg_id

            # Load conversation thread for multi-turn context
            from app.services.a2a import get_conversation_thread, send_message

            thread = await get_conversation_thread(db, context_id)

            # Build LLM messages from conversation history
            from app.core.agent_identity import get_capability_card

            card = get_capability_card(self._agent_id)
            specialties = metadata.get("specialties_needed", card.get("specialties", []))
            rag = await retrieve_context(
                task.project_id, task.title + " " + (task.description or "")
            )

            llm_messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are {self._agent_id}, a specialist in: {', '.join(specialties) if specialties else 'UX research'}. "
                        f"Provide expert analysis. You are collaborating with {msg_from} on task '{task.title}'."
                    ),
                },
            ]
            # Add thread history
            for t in thread:
                t_from = t.get("from_agent_id", "")
                role = "assistant" if t_from == self._agent_id else "user"
                llm_messages.append({"role": role, "content": t.get("content", "")})

            # Add current message if not in thread
            if not thread or thread[-1].get("id") != msg_id:
                llm_messages.append(
                    {
                        "role": "user",
                        "content": msg_content
                        or f"Task: {task.title}\nDescription: {task.description or 'N/A'}",
                    }
                )

            # Add RAG context
            if rag.has_context:
                llm_messages.append(
                    {"role": "user", "content": f"[Relevant documents]\n{rag.context_text[:800]}"}
                )

            response = await ollama.chat(messages=llm_messages)
            analysis = response.get("message", {}).get("content", "")
            if not analysis:
                return

            # Send response in same conversation thread
            await send_message(
                db=db,
                from_agent_id=self._agent_id,
                to_agent_id=msg_from,
                message_type="collaboration_response",
                content=analysis[:2000],
                metadata={"task_id": task_id, "context_id": context_id, "responding_to": msg_id},
            )

            # Append to task notes
            collab_note = f"\n\n--- {self._agent_id} collaboration ---\n{analysis[:1000]}"
            task.agent_notes = (task.agent_notes or "") + collab_note
            await db.commit()
            logger.info(
                f"A2A: {self._agent_id} responded in thread {context_id[:8]} for task {task_id}"
            )
        except Exception as e:
            logger.debug(f"A2A collaboration handling failed: {e}")

    async def _initiate_debate(
        self, db: AsyncSession, task: Task, output: SkillOutput
    ) -> str | None:
        """Initiate a debate with another agent when consensus is uncertain.

        Sends the output to a collaborator for critical review. Waits up to 30s
        for a response. Synthesizes both perspectives into a refined output.
        """
        try:
            from app.services.a2a import send_message, get_messages
            from app.core.agent_identity import get_capability_card

            # Find a collaborator — prefer devops for data quality, ux-eval for UX
            collaborators = ["istara-devops", "istara-ux-eval", "istara-ui-audit"]
            target = next((c for c in collaborators if c != self._agent_id), collaborators[0])

            context_id = f"debate-{task.id}-{uuid.uuid4().hex[:8]}"
            await send_message(
                db=db,
                from_agent_id=self._agent_id,
                to_agent_id=target,
                message_type="debate_request",
                content=f"I need a critical review of this analysis.\n\nTask: {task.title}\n\nOutput:\n{output.summary[:1500]}",
                metadata={"task_id": task.id, "context_id": context_id},
            )
            logger.info(f"A2A debate initiated with {target} for task {task.id}")

            # Wait for response (up to 30s, polling every 3s)
            for _ in range(10):
                await asyncio.sleep(3)
                msgs = await get_messages(db, self._agent_id, unread_only=True, limit=5)
                for msg in msgs:
                    msg_meta = msg.get("metadata", {}) if isinstance(msg, dict) else {}
                    if isinstance(msg_meta, str):
                        msg_meta = json.loads(msg_meta) if msg_meta else {}
                    if (
                        msg_meta.get("context_id") == context_id
                        and msg.get("message_type") == "debate_response"
                    ):
                        critique = msg.get("content", "")
                        # Synthesize both perspectives
                        synth = await ollama.chat(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Synthesize two perspectives on the same research analysis into a single improved output.",
                                },
                                {
                                    "role": "user",
                                    "content": f"Original analysis:\n{output.summary[:1000]}\n\nCritique from {target}:\n{critique[:1000]}\n\nProduce a refined analysis that addresses the critique.",
                                },
                            ]
                        )
                        return synth.get("message", {}).get("content", "")

            logger.debug(f"A2A debate timed out — no response from {target}")
        except Exception as e:
            logger.debug(f"A2A debate failed: {e}")
        return None

    async def _handle_debate(self, db: AsyncSession, msg: dict) -> None:
        """Respond to a debate request with critical analysis."""
        try:
            content = (
                msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            )
            msg_from = (
                msg.get("from_agent_id", "")
                if isinstance(msg, dict)
                else getattr(msg, "from_agent_id", "")
            )
            metadata = (
                msg.get("metadata", {}) if isinstance(msg, dict) else getattr(msg, "metadata", {})
            )
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata else {}

            response = await ollama.chat(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are {self._agent_id}, a critical reviewer. Identify gaps, unsupported claims, missing perspectives, and areas for improvement. Be constructive but rigorous.",
                    },
                    {"role": "user", "content": content},
                ]
            )
            critique = response.get("message", {}).get("content", "")
            if not critique:
                return

            from app.services.a2a import send_message

            await send_message(
                db=db,
                from_agent_id=self._agent_id,
                to_agent_id=msg_from,
                message_type="debate_response",
                content=critique[:2000],
                metadata={
                    "context_id": metadata.get("context_id", ""),
                    "task_id": metadata.get("task_id", ""),
                },
            )
        except Exception as e:
            logger.debug(f"Debate response failed: {e}")

    async def _trigger_mece_reporting(self, task_id: str, project_id: str) -> None:
        """Trigger autonomous MECE reporting sub-agent when a task is verified → DONE.

        This creates an A2A message to the report_manager agent that will:
        1. Draft Layer 2/3/4 reports using Pyramid/MECE logic
        2. Send via A2A messaging for user review
        """
        try:
            from app.api.websocket import broadcast_task_progress
            from app.services.a2a import send_message as a2a_send

            async with async_session() as db:
                task = (
                    await db.execute(select(Task).where(Task.id == task_id))
                ).scalar_one_or_none()
                if not task or task.status != TaskStatus.DONE:
                    return

                report_msg = {
                    "type": "mece_report_request",
                    "task_id": task_id,
                    "project_id": project_id,
                    "task_title": task.title,
                    "agent_notes": getattr(task, "agent_notes", "") or "",
                    "skill_name": getattr(task, "skill_name", ""),
                }

                await a2a_send(
                    db=db,
                    from_agent_id=self._agent_id,
                    to_agent_id="istara-main",
                    message_type="delegate",
                    content=json.dumps(report_msg),
                    metadata={"project_id": project_id},
                )

            logger.info(f"MECE report triggered for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger MECE reporting for task {task_id}: {e}")

    async def _pick_next_task(self, db: AsyncSession) -> Task | None:
        """Pick the highest priority task assigned to THIS agent.

        Priority order:
        1. Tasks explicitly assigned to this agent — by priority then position
        2. Unassigned tasks (only for istara-main as fallback)

        Priority mapping: critical > high > medium > low
        Skips tasks in backoff period after retries.
        """
        priority_order = case(
            (Task.priority == "critical", 0),
            (Task.priority == "high", 1),
            (Task.priority == "medium", 2),
            (Task.priority == "low", 3),
            else_=4,
        )

        # First: tasks assigned to THIS agent
        result = await db.execute(
            select(Task)
            .where(
                Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                Task.agent_id == self._agent_id,
                # Skip locked tasks (locked by someone else)
                or_(
                    Task.locked_by.is_(None),
                    Task.locked_by == self._agent_id,
                    Task.lock_expires_at < datetime.now(timezone.utc),
                ),
            )
            .order_by(priority_order, Task.position.asc(), Task.created_at.asc())
            .limit(10)
        )
        for task in result.scalars().all():
            if not self._is_in_backoff(task):
                return task

        # Fallback: pick unassigned tasks (main agent only to avoid contention)
        if self._agent_id == "istara-main":
            result = await db.execute(
                select(Task)
                .where(
                    Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                    Task.agent_id.is_(None),
                )
                .order_by(priority_order, Task.position.asc(), Task.created_at.asc())
                .limit(10)
            )
            for task in result.scalars().all():
                if not self._is_in_backoff(task):
                    return task

        return None

    async def _get_project(self, db: AsyncSession, project_id: str) -> Project | None:
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def _execute_task(self, db: AsyncSession, task: Task, project: Project) -> None:
        """Execute a task using the appropriate skill."""
        logger.info(f"Executing task: {task.title} (skill: {task.skill_name or 'auto'})")

        # Checkpoint: started
        await create_checkpoint(db, task.id, self._agent_id, "started")

        # Move to in_progress and persist agent state
        task.status = TaskStatus.IN_PROGRESS
        task.progress = 0.1
        await db.commit()
        await self._persist_agent_state(AgentState.WORKING, task.title)
        await broadcast_agent_status("working", f"Working on: {task.title}")
        await broadcast_task_progress(task.id, 0.1, "Starting task...")

        # Retrieve RAG context before skill selection (gives skills document awareness)
        rag_context = await retrieve_context(
            project.id, task.title + " " + (task.description or ""), top_k=5
        )

        # ── Plan-and-Execute: decompose complex tasks before executing ──
        # If the task has no explicit skill and has a substantive description,
        # create a research plan first. Simple tasks skip planning.
        skill = await self._select_skill(task)
        if not skill:
            # Complex task — create plan, then execute step by step
            plan = await self._create_research_plan(task, project, rag_context)
            if plan and len(plan.steps) > 1:
                await self._execute_planned_task(db, task, project, plan, rag_context)
                await complete_checkpoint(db, task.id)
                return
            # Simple task or planning failed — fall back to ReAct loop
            await self._execute_general_task(db, task, project)
            await complete_checkpoint(db, task.id)
            return

        # Checkpoint: skill_selected
        await update_checkpoint(db, task.id, "skill_selected", {"skill": skill.name})

        # Check per-agent skill ACL
        if not await self._check_agent_skill_acl(task.agent_id, skill.name):
            logger.warning(f"Agent {task.agent_id} not allowed to use skill {skill.name}")
            task.agent_notes = f"Skill '{skill.name}' not allowed for this agent."
            task.status = TaskStatus.BACKLOG
            await db.commit()
            await complete_checkpoint(db, task.id)
            await broadcast_agent_status("warning", f"Skill blocked: {skill.name} not in agent ACL")
            return

        # Build skill input — include task instructions, context, and RAG documents
        task_context = task.user_context or task.description
        if getattr(task, "instructions", None):
            task_context += f"\n\nSpecific instructions: {task.instructions}"
        if rag_context.has_context:
            task_context += f"\n\n## Relevant Documents\n{rag_context.context_text}"
        skill_input = SkillInput(
            project_id=project.id,
            task_id=task.id,
            urls=task.get_urls() if hasattr(task, "get_urls") else [],
            parameters={"mode": "analyze"},
            user_context=task_context,
            project_context=project.project_context,
            company_context=project.company_context,
        )

        # Get files from the project's folder (watch_folder_path or internal uploads)
        folder = _resolve_project_folder(project, project.id)
        if folder.exists():
            skill_input.files = [
                str(f)
                for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in {
                    ".txt", ".md", ".pdf", ".docx", ".csv",
                    ".mp3", ".wav", ".m4a", ".ogg"
                }
            ]

        await broadcast_task_progress(task.id, 0.3, f"Running {skill.display_name}...")

        trace_id = __import__("uuid").uuid4().hex[:36]

        try:
            await agent_hooks.fire(
                "pre_task",
                {
                    "trace_id": trace_id,
                    "skill_name": skill.name,
                    "model_name": getattr(self, "model_name", ""),
                    "agent_id": self.agent_id,
                    "project_id": project.id,
                    "task_id": task.id,
                    "temperature": 0.3,
                },
            )

            # Checkpoint: executing
            await update_checkpoint(db, task.id, "executing")

            # Execute the skill (with timeout protection)
            try:
                output = await asyncio.wait_for(skill.execute(skill_input), timeout=600)
            except asyncio.TimeoutError:
                output = SkillOutput(
                    success=False, summary="Skill timed out after 10 minutes.", errors=["timeout"]
                )
                logger.warning(f"Skill {skill.name} timed out for task {task.id}")

            await agent_hooks.fire(
                "post_task",
                {
                    "trace_id": trace_id,
                    "skill_name": skill.name,
                    "model_name": getattr(self, "model_name", ""),
                    "agent_id": self.agent_id,
                    "project_id": project.id,
                    "task_id": task.id,
                    "temperature": 0.3,
                    "success": output.success,
                    "quality_score": getattr(output, "quality_score", None),
                },
            )

            # ── Ensemble validation (if available) ──
            # Validates findings using multi-perspective methods before storing.
            # Self-MoA works with a single server (varies temperature).
            try:
                from app.core.adaptive_validation import AdaptiveSelector
                from app.core.validation import (
                    self_moa,
                    adversarial_review,
                    dual_run,
                    full_ensemble,
                    debate_rounds,
                )
                import json as _json

                selector = AdaptiveSelector()
                method = await selector.select_method(project.id, skill.name, self.agent_id)

                if method and method != "skip" and output.summary:
                    await broadcast_task_progress(task.id, 0.5, f"Validating ({method})...")
                    validation_fns = {
                        "self_moa": self_moa,
                        "adversarial_review": adversarial_review,
                        "dual_run": dual_run,
                        "full_ensemble": full_ensemble,
                        "debate_rounds": debate_rounds,
                    }
                    fn = validation_fns.get(method)
                    if fn:
                        # All validation functions accept (prompt, system, model, n)
                        val_result = await fn(
                            prompt=skill_input.user_context or task.description,
                            system=output.summary,
                        )
                        task.validation_method = method
                        task.validation_result = _json.dumps(
                            {
                                "agreement_score": val_result.consensus.agreement_score,
                                "kappa": val_result.consensus.kappa,
                                "cosine_sim": val_result.consensus.cosine_sim,
                                "confidence": val_result.consensus.confidence,
                            }
                        )
                        task.consensus_score = val_result.consensus.agreement_score

                        # Use best response if consensus is high
                        if (
                            val_result.best_response
                            and val_result.consensus.agreement_score >= 0.55
                        ):
                            output.summary = val_result.best_response

                        # Record metrics for adaptive learning
                        await selector.record_outcome(
                            project.id,
                            skill.name,
                            self.agent_id,
                            method,
                            val_result.consensus.agreement_score,
                            val_result.consensus.agreement_score >= 0.5,
                        )
                        logger.info(
                            f"Validation [{method}]: score={val_result.consensus.agreement_score:.2f}"
                        )

                        await agent_hooks.fire(
                            "post_validation",
                            {
                                "trace_id": trace_id,
                                "skill_name": skill.name,
                                "model_name": getattr(self, "model_name", ""),
                                "agent_id": self.agent_id,
                                "project_id": project.id,
                                "task_id": task.id,
                                "validation_method": method,
                                "validation_passed": val_result.consensus.agreement_score >= 0.5,
                                "consensus_score": val_result.consensus.agreement_score,
                                "validation_quality": val_result.consensus.agreement_score,
                            },
                        )
            except Exception as e:
                logger.debug(f"Ensemble validation skipped: {e}")

            # Validate output structure before storing
            try:
                validation_issues = await skill.validate_output(output)
                if validation_issues:
                    logger.warning(f"Output validation for {skill.name}: {validation_issues[:3]}")
                    task.agent_notes = (
                        task.agent_notes or ""
                    ) + f"\n[Validation: {'; '.join(validation_issues[:3])}]"
            except Exception as e:
                logger.debug(f"Output validation skipped: {e}")

            # ── A2A Debate for uncertain consensus ──
            # When ensemble validation produces borderline consensus (0.4-0.6),
            # initiate a debate with another agent for a second perspective.
            try:
                consensus_score = getattr(task, "consensus_score", None)
                if consensus_score and 0.4 <= consensus_score <= 0.6:
                    debate_result = await self._initiate_debate(db, task, output)
                    if debate_result:
                        output.summary = debate_result
                        task.agent_notes = (
                            task.agent_notes or ""
                        ) + "\n[A2A debate refined output]"
            except Exception as e:
                logger.debug(f"A2A debate skipped: {e}")

            # Store findings in the database
            await self._store_findings(db, project.id, output, task)
            await broadcast_task_progress(task.id, 0.7, "Storing findings...")

            # Checkpoint: findings_stored
            await update_checkpoint(db, task.id, "findings_stored")

            # Store key insights in agent memory
            try:
                from app.core.agent_memory import agent_memory

                if hasattr(output, "insights") and output.insights:
                    for insight in output.insights[:3]:
                        text = (
                            insight.get("text", "") if isinstance(insight, dict) else str(insight)
                        )
                        if text:
                            await agent_memory.memory_store(
                                task.agent_id or "istara-main",
                                project.id,
                                text,
                                tags=["auto-insight", task.skill_name or "general"],
                            )
            except Exception as e:
                logger.debug(f"Agent memory store skipped: {e}")

            # Self-check key insights
            if output.insights:
                await broadcast_task_progress(task.id, 0.8, "Verifying findings...")
                await self._verify_findings(db, project.id, output)

            # Self-verify output quality (LLM reflection with heuristic fallback)
            verified, verify_reason = await self._self_verify_output(task, output)
            quality_score = 0.8 if output.success else 0.2

            if verified:
                # Update task — passed verification
                task.status = TaskStatus.IN_REVIEW
                task.progress = 1.0
                task.agent_notes = output.summary
                await db.commit()

                await agent_hooks.fire(
                    "on_completion",
                    {
                        "trace_id": trace_id,
                        "skill_name": skill.name,
                        "model_name": getattr(self, "model_name", ""),
                        "agent_id": self.agent_id,
                        "project_id": project.id,
                        "task_id": task.id,
                        "success": True,
                        "final_quality": quality_score,
                        "total_duration_ms": 0,
                    },
                )

                await broadcast_task_progress(task.id, 1.0, "Complete — ready for review.")
                await self._persist_agent_state(AgentState.IDLE)
                await broadcast_agent_status("idle", f"Completed: {task.title}")
            else:
                # Verification failed — keep in progress for retry/attention
                task.status = TaskStatus.IN_PROGRESS
                task.progress = 0.5
                task.agent_notes = f"[Verification failed] {verify_reason}\n\n{output.summary}"
                await db.commit()

                await broadcast_task_progress(task.id, 0.5, f"Verification failed: {verify_reason}")
                await self._persist_agent_state(AgentState.IDLE)
                await broadcast_agent_status(
                    "warning", f"Needs attention: {task.title} — {verify_reason}"
                )

            # Record skill usage and check health for self-evolution
            skill_manager.record_execution(skill.name, output.success, quality_score)
            try:
                health = skill_manager.get_skill_health(skill.name)
                # LLM-based skill improvement when quality is consistently low
                if health.get("executions", 0) >= 3 and health.get("avg_quality", 1.0) < 0.5:
                    # Ask LLM to reflect on why the skill is underperforming
                    improvement_text = ""
                    try:
                        reflection = await ollama.chat(
                            messages=[
                                {
                                    "role": "user",
                                    "content": (
                                        f"Skill '{skill.name}' has been underperforming "
                                        f"(quality: {health.get('avg_quality', 0):.0%} over {health['executions']} runs).\n"
                                        f"Last task: '{task.title}'\n"
                                        f"Last output (first 300 chars): {(output.summary or '')[:300]}\n"
                                        f"Errors: {output.errors}\n\n"
                                        "How should the skill's execution prompt be improved to produce better results? "
                                        "Be specific and concise (2-3 sentences)."
                                    ),
                                },
                            ],
                            temperature=0.3,
                        )
                        improvement_text = reflection.get("message", {}).get("content", "")
                    except Exception:
                        improvement_text = f"Low quality ({health['avg_quality']:.0%}) after {health['executions']} runs"

                    skill_def = skill_manager.get(skill.name)
                    skill_manager.propose_improvement(
                        skill_name=skill.name,
                        field="execute_prompt",
                        current_value=(skill_def or {}).get("execute_prompt", "")[:200]
                        if isinstance(skill_def, dict)
                        else "",
                        proposed_value=improvement_text[:500],
                        reason=f"LLM reflection: quality {health['avg_quality']:.0%} after {health['executions']} runs",
                        confidence=0.6,
                    )
                    await broadcast_suggestion(
                        f"Skill '{skill.display_name}' needs improvement (quality: {health['avg_quality']:.0%}). "
                        f"An improvement proposal has been created. Check Agents → Skill Proposals.",
                        project.id,
                    )
            except Exception:
                pass  # Don't fail task on self-evolution check

            # Autonomous skill creation check
            total_findings = len(output.nuggets) + len(output.facts) + len(output.insights)
            if output.success and quality_score >= 0.8 and total_findings >= 3:
                try:
                    await self._maybe_propose_skill(db, task, skill, output, total_findings)
                except Exception:
                    pass  # Don't fail task on skill creation check

            # Generate suggestions
            if output.suggestions:
                for suggestion in output.suggestions[:3]:
                    await broadcast_suggestion(suggestion, project.id)

            # Checkpoint: complete (remove checkpoint)
            await complete_checkpoint(db, task.id)

            logger.info(
                f"Task {'completed' if verified else 'needs review'}: {task.title} — {output.summary}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Skill execution failed for task {task.id}: {error_msg}")

            await agent_hooks.fire(
                "on_error",
                {
                    "trace_id": trace_id
                    if "trace_id" in dir()
                    else __import__("uuid").uuid4().hex[:36],
                    "skill_name": skill.name,
                    "model_name": getattr(self, "model_name", ""),
                    "agent_id": self.agent_id,
                    "project_id": project.id,
                    "task_id": task.id,
                    "operation": "skill_execute",
                    "error_type": type(e).__name__,
                    "error_message": error_msg[:500],
                },
            )

            # Check if we have a known resolution for this error type
            resolution_hint = ""
            try:
                from app.core.agent_learning import agent_learning

                resolution = await agent_learning.get_error_resolution(self._agent_id, error_msg)
                if resolution:
                    resolution_hint = f"\n\nKnown resolution: {resolution}"
                    logger.info(f"Found known resolution for error: {resolution}")
                else:
                    # Record this as a new error pattern
                    await agent_learning.record_error_learning(
                        agent_id=self._agent_id,
                        error_message=error_msg,
                        resolution="Returned task to backlog for retry",
                        project_id=task.project_id,
                    )
            except Exception:
                pass

            # Retry logic with backoff
            task.retry_count = (task.retry_count or 0) + 1
            task.last_retry_at = datetime.now(timezone.utc)
            task.agent_notes = f"Error: {error_msg}{resolution_hint}"

            if task.retry_count < (task.max_retries or 3):
                task.status = TaskStatus.BACKLOG  # Return to backlog for retry
                await db.commit()
                await self._persist_agent_state(AgentState.ERROR, error_msg)
                await broadcast_agent_status(
                    "warning",
                    f"Task retry {task.retry_count}/{task.max_retries or 3}: {task.title} — {error_msg[:80]}",
                )
            else:
                task.status = TaskStatus.DONE
                await db.commit()
                await self._persist_agent_state(AgentState.ERROR, error_msg)
                await broadcast_agent_status(
                    "error",
                    f"Task failed after {task.retry_count} retries: {task.title} — {error_msg[:80]}",
                )

            # Leave checkpoint in place for crash recovery awareness

    async def _maybe_propose_skill(
        self,
        db: AsyncSession,
        task: Task,
        skill,
        output: SkillOutput,
        total_findings: int,
    ) -> None:
        """Check if the agent should propose creating a new skill based on this task."""
        # Maturity gate: agent must have executed 5+ tasks
        usage = skill_manager.get_usage_stats()
        total_executions = sum(s.get("executions", 0) for s in usage.values())
        if total_executions < 5:
            return

        # Check no existing skill matches closely (by task title keywords)
        task_keywords = set(task.title.lower().split())
        for existing_skill in registry.list_all():
            existing_words = set(existing_skill.name.replace("-", " ").split())
            overlap = task_keywords & existing_words
            if len(overlap) >= 2:
                return  # Close match exists

        # Build a proposal from the task context
        proposed_name = f"auto-{task.skill_name or 'general'}-{task.id[:8]}"
        proposed_definition = {
            "name": proposed_name,
            "display_name": f"Auto: {task.title[:50]}",
            "description": f"Autonomously proposed skill based on task: {task.title}",
            "phase": skill.phase.value if skill else "discover",
            "skill_type": "mixed",
            "plan_prompt": f"Create a research plan for: {{context}}",
            "execute_prompt": f"Analyze the following data for patterns and insights.\nContext: {{context}}\n\nData:\n{{content}}",
            "output_schema": output.summary[:500] if output.summary else "Standard findings output",
        }

        try:
            proposal = skill_manager.propose_skill_creation(
                definition=proposed_definition,
                source_task_id=task.id,
                agent_id=self._agent_id,
                reason=f"High-quality output ({total_findings} findings) from task: {task.title}",
                confidence=min(70, 50 + total_findings * 5),
            )
            await broadcast_suggestion(
                f"New skill proposed: '{proposed_definition['display_name']}' — review in Skill Creation Proposals.",
                task.project_id,
            )
        except ValueError as e:
            logger.debug(f"Skill creation proposal skipped: {e}")

    async def _select_skill(self, task: Task):
        """Select the best skill for a task."""
        # If task has an explicit skill_name, use it
        if task.skill_name:
            skill = registry.get(task.skill_name)
            if skill:
                return skill

        # Try to infer skill from task title/description
        title_lower = (task.title + " " + task.description).lower()

        skill_keywords = {
            "interview": "user-interviews",
            "transcript": "user-interviews",
            "survey": "survey-design",
            "questionnaire": "survey-generator",
            "competitive": "competitive-analysis",
            "competitor": "competitive-analysis",
            "persona": "persona-creation",
            "journey": "journey-mapping",
            "affinity": "affinity-mapping",
            "thematic": "thematic-analysis",
            "usability": "usability-testing",
            "heuristic": "heuristic-evaluation",
            "ux audit": "browser-ux-audit",
            "site audit": "browser-ux-audit",
            "accessibility check": "browser-accessibility-check",
            "wcag": "browser-accessibility-check",
            "a11y": "browser-accessibility-check",
            "competitive benchmark": "browser-competitive-benchmark",
            "competitor audit": "browser-competitive-benchmark",
            "quality evaluation": "research-quality-evaluation",
            "evaluate quality": "research-quality-evaluation",
            "llm as judge": "research-quality-evaluation",
            "game theory participant simulation": "participant-simulation",
            "participant simulation": "participant-simulation",
            "game theory": "participant-simulation",
            "card sort": "card-sorting",
            "tree test": "tree-testing",
            "a/b test": "ab-test-analysis",
            "sus ": "sus-umux-scoring",
            "umux": "sus-umux-scoring",
            "nps": "nps-analysis",
            "stakeholder": "stakeholder-interviews",
            "diary": "diary-studies",
            "ethnograph": "field-studies",
            "field study": "field-studies",
            "accessibility": "accessibility-audit",
            "wcag": "accessibility-audit",
            "analytics": "analytics-review",
            "hmw": "hmw-statements",
            "how might we": "hmw-statements",
            "jobs to be done": "jtbd-analysis",
            "jtbd": "jtbd-analysis",
            "empathy map": "empathy-mapping",
            "user flow": "user-flow-mapping",
            "synthesis": "research-synthesis",
            "report": "research-synthesis",
            "prioriti": "prioritization-matrix",
            "concept test": "concept-testing",
            "cognitive walk": "cognitive-walkthrough",
            "design critique": "design-critique",
            "expert review": "design-critique",
            "prototype": "prototype-feedback",
            "workshop": "workshop-facilitation",
            "design system": "design-system-audit",
            "handoff": "handoff-documentation",
            "presentation": "stakeholder-presentation",
            "retro": "research-retro",
            "longitudinal": "longitudinal-tracking",
            "taxonomy": "taxonomy-generator",
            "kappa": "kappa-thematic-analysis",
            "intercoder": "kappa-thematic-analysis",
            "ai detect": "survey-ai-detection",
            "bot detect": "survey-ai-detection",
        }
        for keyword, skill_name in skill_keywords.items():
            if keyword in title_lower:
                skill = registry.get(skill_name)
                if skill:
                    return skill

        return None

        # Semantic matching fallback: embed task text and compare against skills
        try:
            match = await self._semantic_skill_match(task)
            if match:
                return match
        except Exception as e:
            logger.debug(f"Semantic skill match skipped: {e}")

        # No match — flag as skill creation candidate
        return None

    # --- Semantic Skill Matching ---

    _skill_desc_cache: dict[str, list[float]] = {}

    async def _semantic_skill_match(self, task: Task):
        """Try embedding-based semantic matching when keywords fail.

        Compares task title+description embeddings against cached skill
        description embeddings.  Returns the best match above a 0.6
        cosine similarity threshold, or None.
        """
        import math

        all_skills = registry.list_all()
        if not all_skills:
            return None

        task_text = f"{task.title} {task.description or ''}"
        if len(task_text.strip()) < 5:
            return None

        # Build / refresh description embedding cache
        from app.core.embeddings import embed_text

        task_vec = await embed_text(task_text[:512])
        if not task_vec:
            return None

        # Embed skill descriptions (cached in-memory)
        for skill in all_skills:
            if skill.name not in self._skill_desc_cache:
                desc = f"{skill.display_name} {skill.description}"
                vec = await embed_text(desc[:512])
                if vec:
                    self._skill_desc_cache[skill.name] = vec

        # Cosine similarity
        def _cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        best_score = 0.0
        best_skill = None
        for skill in all_skills:
            skill_vec = self._skill_desc_cache.get(skill.name)
            if not skill_vec:
                continue
            score = _cosine(task_vec, skill_vec)
            if score > best_score:
                best_score = score
                best_skill = skill

        if best_skill and best_score >= 0.6:
            logger.info(
                f"Semantic skill match: {best_skill.name} "
                f"(similarity={best_score:.2f}) for task '{task.title[:60]}'"
            )
            return best_skill

        return None

    async def _check_agent_skill_acl(self, agent_id: str | None, skill_name: str) -> bool:
        """Check if an agent is allowed to use a skill. Returns True if allowed."""
        if not agent_id or agent_id == "istara-main":
            return True  # Main agent can use all skills

        try:
            async with async_session() as db:
                result = await db.execute(select(Agent).where(Agent.id == agent_id))
                agent = result.scalar_one_or_none()
                if not agent:
                    return True  # Unknown agent — allow

                caps = json.loads(agent.capabilities) if agent.capabilities else []
                # If agent has "skill_execution" capability but no explicit allowed_skills
                # in memory, allow all skills
                memory = json.loads(agent.memory) if agent.memory else {}
                allowed = memory.get("allowed_skills")
                if allowed is None:
                    return True  # No ACL = allow all
                return skill_name in allowed
        except Exception:
            return True  # On error, allow

    async def _execute_general_task(self, db: AsyncSession, task: Task, project: Project) -> None:
        """Handle tasks without a specific skill — use general LLM reasoning."""
        trace_id = __import__("uuid").uuid4().hex[:36]
        context = await retrieve_context(project.id, task.title + " " + task.description)

        # Use the full context hierarchy as system prompt
        system_prompt = await context_hierarchy.compose_context(
            db,
            project_id=project.id,
            task_context=task.user_context or task.description,
        )

        if context.has_context:
            system_prompt += f"\n\n## Relevant Documents\n{context.context_text}"

        # Build user message with all task fields
        user_parts = [f"Task: {task.title}", f"Details: {task.description}"]
        if task.user_context:
            user_parts.append(f"Additional context: {task.user_context}")
        if getattr(task, "instructions", None):
            user_parts.append(f"Specific instructions: {task.instructions}")
        user_msg = "\n\n".join(user_parts)

        # Tool-augmented ReAct loop — same tools available in chat
        MAX_AGENT_TOOL_ITERATIONS = 5
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        result = ""
        tools_used = []

        try:
            from app.skills.system_actions import OPENAI_TOOLS, execute_tool

            use_tools = True
        except ImportError:
            use_tools = False

        for iteration in range(MAX_AGENT_TOOL_ITERATIONS + 1):
            if use_tools and iteration < MAX_AGENT_TOOL_ITERATIONS:
                response = await ollama.chat(messages=messages, tools=OPENAI_TOOLS)
            else:
                response = await ollama.chat(messages=messages)

            msg = response.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            if tool_calls and iteration < MAX_AGENT_TOOL_ITERATIONS and use_tools:
                # Append assistant message with tool calls
                messages.append(
                    {"role": "assistant", "content": content or "", "tool_calls": tool_calls}
                )
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    try:
                        tool_args = (
                            json.loads(fn.get("arguments", "{}"))
                            if isinstance(fn.get("arguments"), str)
                            else fn.get("arguments", {})
                        )
                        # Record successful JSON parse for telemetry tracking
                        asyncio.create_task(
                            telemetry_recorder.record_json_parse(
                                trace_id=trace_id,
                                model_name="",  # Model name not available at this scope
                                success=True,
                                agent_id=self._agent_id,
                                project_id=project.id,
                            )
                        )
                    except (json.JSONDecodeError, TypeError) as e:
                        tool_args = {}
                        # Record failed JSON parse for telemetry tracking
                        asyncio.create_task(
                            telemetry_recorder.record_json_parse(
                                trace_id=trace_id,
                                model_name="",
                                success=False,
                                error_type="JSONDecodeError",
                                error_message=str(e)[:200],
                                agent_id=self._agent_id,
                                project_id=project.id,
                            )
                        )
                    tools_used.append(tool_name)
                    logger.info(
                        f"Agent tool call [{iteration}]: {tool_name}({list(tool_args.keys())})"
                    )
                    tool_result = await execute_tool(
                        tool_name, tool_args, project.id, self._agent_id
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id", f"call_{iteration}"),
                            "content": json.dumps(tool_result)
                            if isinstance(tool_result, dict)
                            else str(tool_result),
                        }
                    )
            else:
                result = content
                break

        # Log tool usage
        if tools_used:
            tool_summary = f"[Tools used: {', '.join(tools_used)}]\n\n"
        else:
            tool_summary = ""

        # Quality check
        if not result or len(result.strip()) < 20:
            task.status = TaskStatus.IN_PROGRESS
            task.progress = 0.5
            task.agent_notes = (
                f"{tool_summary}[Verification failed] Response too short or empty\n\n{result}"
            )
            await db.commit()
            await broadcast_task_progress(task.id, 0.5, "Verification failed: response too short")
            await self._persist_agent_state(AgentState.IDLE)
            await broadcast_agent_status("warning", f"Needs attention: {task.title}")
        else:
            task.status = TaskStatus.IN_REVIEW
            task.progress = 1.0
            task.agent_notes = f"{tool_summary}{result}"
            await db.commit()
            await broadcast_task_progress(task.id, 1.0, "Complete — ready for review.")
            await self._persist_agent_state(AgentState.IDLE)
            await broadcast_agent_status("idle", f"Completed: {task.title}")

    # ── Plan-and-Execute Methods ──────────────────────────────────────

    async def _create_research_plan(
        self, task: Task, project: Project, rag_context
    ) -> ResearchPlan | None:
        """Ask the LLM to decompose a complex task into ordered research steps."""
        try:
            skill_names = [s.name for s in registry.list_all()[:25]]
            plan_prompt = (
                "You are a research planning agent. Decompose this task into 2-5 concrete steps.\n\n"
                f"Task: {task.title}\n"
                f"Description: {task.description or 'No description'}\n"
                f"Instructions: {getattr(task, 'instructions', '') or 'None'}\n"
                f"Available skills: {', '.join(skill_names)}\n\n"
                "For each step, provide:\n"
                "- id: step_1, step_2, etc.\n"
                "- description: what to do\n"
                "- skill_name: which skill to use (or null for general reasoning)\n"
                "- depends_on: list of step IDs this step depends on (empty [] if independent)\n\n"
                "Steps with empty depends_on can run in parallel.\n\n"
                'Respond with JSON: {"steps": [{"id": "step_1", "description": "...", "skill_name": "...", "depends_on": []}]}\n'
                'If this is a simple task that doesn\'t need decomposition, respond: {"steps": []}'
            )
            response = await ollama.chat(
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.3,
            )
            content = response.get("message", {}).get("content", "")
            logger.info(f"Research plan raw content: {content}")
            import re

            json_match = re.search(r'(\{.*"steps"\s*:\s*\[.*\]\s*\})', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                steps = [
                    ResearchStep(
                        id=s.get("id", f"step_{i}"),
                        description=s.get("description", ""),
                        skill_name=s.get("skill_name"),
                        depends_on=s.get("depends_on", []),
                    )
                    for i, s in enumerate(data.get("steps", []))
                ]
                if steps:
                    plan = ResearchPlan(question=task.title, steps=steps)
                    logger.info(f"Research plan created: {len(steps)} steps for '{task.title}'")
                    return plan
        except Exception as e:
            logger.debug(f"Research planning skipped: {e}")
        return None

    async def _execute_planned_task(
        self, db: AsyncSession, task: Task, project: Project, plan: ResearchPlan, rag_context
    ) -> None:
        """Execute a research plan with DAG-parallel step execution.

        Steps with no dependencies run in parallel via asyncio.gather().
        Steps with dependencies wait until all prerequisites complete.
        This is the LLMCompiler pattern (ICML 2024) adapted for research.
        """
        plan.status = "executing"
        total_steps = len(plan.steps)
        remaining = list(plan.steps)
        executed_ids: set[str] = set()
        step_num = 0

        while remaining:
            # Find steps whose dependencies are all satisfied
            ready = [s for s in remaining if all(d in executed_ids for d in (s.depends_on or []))]
            if not ready:
                # Deadlock: remaining steps have unresolvable dependencies
                for s in remaining:
                    s.status = "failed"
                    s.result = f"Deadlock: depends on {s.depends_on} but they never completed"
                    plan.past_steps.append(s)
                break

            parallel_count = len(ready)
            # Broadcast plan progress for each step
            for s in ready:
                await broadcast_plan_progress(
                    task.id, step_num + 1, total_steps, s.description[:80], "executing"
                )

            if parallel_count > 1:
                await broadcast_agent_thinking(
                    self._agent_id,
                    step_num + 1,
                    f"Running {parallel_count} steps in parallel",
                    total_steps,
                )
                await broadcast_task_progress(
                    task.id,
                    0.2 + (0.6 * step_num / total_steps),
                    f"Running {parallel_count} steps in parallel...",
                )
            else:
                await broadcast_agent_thinking(
                    self._agent_id, step_num + 1, ready[0].description[:80], total_steps
                )
                await broadcast_task_progress(
                    task.id,
                    0.2 + (0.6 * step_num / total_steps),
                    f"Step: {ready[0].description[:60]}",
                )

            # Execute ready steps in parallel
            results = await asyncio.gather(
                *[
                    self._execute_single_step(db, task, project, step, rag_context, plan)
                    for step in ready
                ],
                return_exceptions=True,
            )

            for step, result in zip(ready, results):
                if isinstance(result, Exception):
                    step.status = "failed"
                    step.result = f"Step failed: {str(result)[:200]}"
                remaining.remove(step)
                plan.past_steps.append(step)
                executed_ids.add(step.id)
                step_num += 1
                await broadcast_plan_progress(
                    task.id, step_num, total_steps, step.description[:80], step.status
                )

        # Compile results
        plan.status = "complete"
        plan_summary = json.dumps(plan.to_dict(), indent=2)
        compiled = "\n\n".join(
            f"### Step {i + 1}: {s.description}\n{s.result}"
            for i, s in enumerate(plan.past_steps)
            if s.result
        )

        task.status = TaskStatus.IN_REVIEW
        task.progress = 1.0
        task.agent_notes = f"[Research Plan]\n{plan_summary}\n\n[Results]\n{compiled}"
        await db.commit()

        await broadcast_task_progress(
            task.id, 1.0, f"Plan complete — {len(plan.past_steps)} steps ({total_steps} planned)."
        )
        await self._persist_agent_state(AgentState.IDLE)
        await broadcast_agent_status("idle", f"Completed plan: {task.title}")

    async def _execute_single_step(
        self,
        db: AsyncSession,
        task: Task,
        project: Project,
        step: ResearchStep,
        rag_context,
        plan: ResearchPlan,
    ) -> None:
        """Execute a single research step (used by DAG-parallel executor)."""
        step.status = "executing"
        try:
            if step.skill_name:
                skill = registry.get(step.skill_name)
                if skill:
                    task_context = step.description
                    if rag_context.has_context:
                        task_context += f"\n\n## Relevant Documents\n{rag_context.context_text}"
                    # Add context from completed steps
                    if plan.past_steps:
                        task_context += "\n\nPrevious findings:\n" + "\n".join(
                            f"- {s.description}: {s.result[:150]}"
                            for s in plan.past_steps
                            if s.result
                        )
                    skill_input = SkillInput(
                        project_id=project.id,
                        task_id=task.id,
                        urls=task.get_urls() if hasattr(task, "get_urls") else [],
                        parameters={"mode": "analyze"},
                        user_context=task_context,
                        project_context=project.project_context,
                        company_context=project.company_context,
                    )
                    output = await asyncio.wait_for(skill.execute(skill_input), timeout=300)
                    step.result = output.summary or ""
                    if output.success:
                        await self._store_findings(db, project.id, output, task)
                else:
                    step.result = f"Skill '{step.skill_name}' not found"
            else:
                system_prompt = await context_hierarchy.compose_context(
                    db,
                    project_id=project.id,
                    task_context=step.description,
                )
                prev_context = "\n".join(
                    f"- {s.description}: {s.result[:200]}" for s in plan.past_steps if s.result
                )
                response = await ollama.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Research step: {step.description}\n\nContext from previous steps:\n{prev_context}",
                        },
                    ]
                )
                step.result = response.get("message", {}).get("content", "")
            step.status = "completed"
        except asyncio.TimeoutError:
            step.status = "failed"
            step.result = "Step timed out after 5 minutes"
            raise
        except Exception as e:
            step.status = "failed"
            step.result = f"Step failed: {str(e)[:200]}"
            raise

    async def _store_findings(
        self, db: AsyncSession, project_id: str, output: SkillOutput, task: Task
    ) -> None:
        """Store skill output findings in the database with evidence chain links.

        The Atomic Research hierarchy is: Nuggets → Facts → Insights → Recommendations.
        Each level links to the one below via ID arrays (nugget_ids, fact_ids, insight_ids).
        If skills provide explicit IDs, we use them. Otherwise, we auto-link:
        all nuggets feed into all facts, all facts feed into all insights, etc.
        This ensures every finding has traceable evidence.
        """
        # === VALIDATION GATE: sanitize tags before storage ===
        for nugget_data in output.nuggets or []:
            tags = nugget_data.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []
            # Filter empty/too-short tags (but keep ux-law: tags)
            tags = [t for t in tags if t and (len(t.strip()) >= 2 or t.startswith("ux-law:"))]
            nugget_data["tags"] = tags

        # Determine base phase from skill (Double Diamond)
        skill = registry.get(task.skill_name) if task.skill_name else None
        skill_phase = skill.phase.value if skill else None

        # Each finding type has a natural phase in the Atomic Research hierarchy.
        # If the skill specifies a phase, use it; otherwise use the type's default.
        nugget_phase = skill_phase or "discover"
        fact_phase = skill_phase or "define"
        insight_phase = skill_phase or "define"
        rec_phase = skill_phase or "deliver"

        # Track created IDs for auto-linking
        created_nugget_ids: list[str] = []
        created_fact_ids: list[str] = []
        created_insight_ids: list[str] = []

        # Store nuggets
        for nugget_data in output.nuggets:
            nid = str(uuid.uuid4())
            # Laws of UX finding enrichment
            try:
                from app.services.laws_of_ux_service import laws_service

                _raw_tags = nugget_data.get("tags", [])
                if isinstance(_raw_tags, str):
                    try:
                        _raw_tags = json.loads(_raw_tags)
                    except Exception:
                        _raw_tags = []
                _enriched_tags = laws_service.enrich_tags(
                    list(_raw_tags), nugget_data.get("text", "")
                )
            except Exception:
                _enriched_tags = nugget_data.get("tags", [])
            # Map confidence string to float
            _conf_str = nugget_data.get("confidence", "")
            _conf_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
            _conf_val = (
                _conf_map.get(_conf_str, 1.0)
                if isinstance(_conf_str, str)
                else float(_conf_str or 1.0)
            )

            nugget = Nugget(
                id=nid,
                project_id=project_id,
                text=nugget_data.get("text", ""),
                source=nugget_data.get("source", task.title),
                source_location=nugget_data.get("source_location", ""),
                tags=json.dumps(_enriched_tags),
                phase=nugget_phase,
                confidence=_conf_val,
            )
            db.add(nugget)
            created_nugget_ids.append(nid)

            # If chain-of-thought reasoning is provided, create CodeApplication record
            _reasoning = nugget_data.get("coding_reasoning", "")
            if _reasoning and isinstance(_enriched_tags, list) and _enriched_tags:
                try:
                    from app.models.code_application import CodeApplication

                    for _tag in _enriched_tags[:5]:  # Cap per nugget
                        if isinstance(_tag, str) and _tag.strip():
                            ca = CodeApplication(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                code_id=_tag,
                                source_text=nugget_data.get("text", "")[:2000],
                                source_location=nugget_data.get("source_location", ""),
                                coder_id=self.agent_id,
                                coder_type="llm",
                                confidence=_conf_val,
                                reasoning=_reasoning,
                            )
                            db.add(ca)
                except Exception as e:
                    logger.debug("CodeApplication creation skipped: %s", e)

        # Store facts — link to nuggets
        for fact_data in output.facts:
            fid = str(uuid.uuid4())
            # Use explicit nugget_ids from skill output if provided, else link to
            # the most recent nuggets (capped at 5 to avoid meaningless N-to-N mapping)
            linked_nuggets = fact_data.get("nugget_ids") or created_nugget_ids[-5:]
            fact = Fact(
                id=fid,
                project_id=project_id,
                text=fact_data.get("text", ""),
                nugget_ids=json.dumps(linked_nuggets),
                phase=fact_phase,
            )
            db.add(fact)
            created_fact_ids.append(fid)

        # Store insights — link to facts
        for insight_data in output.insights:
            iid = str(uuid.uuid4())
            # Use explicit fact_ids from skill output if provided, else link to
            # the most recent facts (capped at 3 to avoid meaningless N-to-N mapping)
            linked_facts = insight_data.get("fact_ids") or created_fact_ids[-3:]
            insight = Insight(
                id=iid,
                project_id=project_id,
                text=insight_data.get("text", ""),
                fact_ids=json.dumps(linked_facts),
                phase=insight_phase,
                impact=insight_data.get("impact", "medium"),
            )
            db.add(insight)
            created_insight_ids.append(iid)

        # Store recommendations — link to insights
        for rec_data in output.recommendations:
            # Use explicit insight_ids from skill output if provided, else link to
            # the most recent insights (capped at 2 to avoid meaningless N-to-N mapping)
            linked_insights = rec_data.get("insight_ids") or created_insight_ids[-2:]
            rec = Recommendation(
                id=str(uuid.uuid4()),
                project_id=project_id,
                text=rec_data.get("text", ""),
                insight_ids=json.dumps(linked_insights),
                phase=rec_phase,
                priority=rec_data.get("priority", "medium"),
                effort=rec_data.get("effort", "medium"),
            )
            db.add(rec)

        await db.commit()

        # Route findings to convergent project reports (with consensus score)
        try:
            from app.core.report_manager import report_manager

            all_finding_ids = created_nugget_ids + created_fact_ids + created_insight_ids
            if all_finding_ids and skill:
                consensus = getattr(task, "consensus_score", None)
                await report_manager.route_findings(
                    project_id,
                    skill.name,
                    all_finding_ids,
                    db,
                    consensus_score=consensus,
                )
        except Exception as e:
            logger.warning("Report routing failed: %s", e)

        # Broadcast finding_created events so the frontend updates in real-time
        total_findings = (
            len(output.nuggets)
            + len(output.facts)
            + len(output.insights)
            + len(output.recommendations)
        )
        if total_findings > 0:
            if output.nuggets:
                await broadcast_finding_created(
                    "nugget", len(output.nuggets), project_id, task.title
                )
            if output.insights:
                await broadcast_finding_created(
                    "insight", len(output.insights), project_id, task.title
                )
            if output.recommendations:
                await broadcast_finding_created(
                    "recommendation", len(output.recommendations), project_id, task.title
                )

        # Ingest text artifacts into RAG AND create Document records
        artifact_doc_ids = []
        for filename, content in output.artifacts.items():
            if isinstance(content, str) and len(content) > 50:
                chunks = [
                    TextChunk(text=content[:2000], source=f"skill:{task.skill_name}:{filename}")
                ]
                await ingest_chunks(project_id, chunks)
                # Create a Document record so artifacts appear in Documents view
                try:
                    from app.models.document import Document

                    doc = Document(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        title=filename,
                        file_name=filename,
                        source="agent_output",
                        content_preview=content[:500],
                        status="ready",
                    )
                    db.add(doc)
                    artifact_doc_ids.append(doc.id)
                except Exception as e:
                    logger.debug(f"Artifact document creation skipped: {e}")

        # Link artifact documents to task output
        if artifact_doc_ids:
            try:
                existing = json.loads(task.output_document_ids or "[]")
                task.output_document_ids = json.dumps(existing + artifact_doc_ids)
                await db.commit()
            except Exception:
                pass

        logger.info(
            f"Stored findings: {len(output.nuggets)} nuggets, {len(output.facts)} facts, "
            f"{len(output.insights)} insights, {len(output.recommendations)} recs"
        )

    async def _verify_findings(
        self, db: AsyncSession, project_id: str, output: SkillOutput
    ) -> None:
        """Self-check key insights against the knowledge base."""
        for insight_data in output.insights[:5]:  # Check top 5
            text = insight_data.get("text", "")
            if text:
                try:
                    result = await verify_claim(text, project_id)
                    if (
                        result.confidence == Confidence.LOW
                        or result.confidence == Confidence.UNVERIFIED
                    ):
                        logger.warning(f"Low-confidence insight: '{text[:60]}...' — {result.notes}")
                except Exception as e:
                    logger.error(f"Verification failed for insight: {e}")

    # --- Self-Verification ---

    def _self_verify_output_heuristic(self, output: SkillOutput) -> tuple[bool, str]:
        """Quick heuristic verification — used as fallback when LLM reflection fails."""
        if not output.success:
            return False, f"Skill reported failure: {output.summary}"
        if output.errors:
            return False, f"Skill produced errors: {'; '.join(output.errors)}"
        error_patterns = ["No files provided", "Error:", "failed", "could not", "unable to"]
        summary_lower = (output.summary or "").lower()
        for pattern in error_patterns:
            if pattern.lower() in summary_lower:
                return False, f"Output contains error pattern '{pattern}'"
        total_findings = (
            len(output.nuggets)
            + len(output.facts)
            + len(output.insights)
            + len(output.recommendations)
        )
        if total_findings == 0:
            return False, "No findings produced"
        return True, "Output verified successfully"

    async def _self_verify_output(self, task: Task, output: SkillOutput) -> tuple[bool, str]:
        """LLM-based self-reflection on output quality.

        Asks the model to evaluate whether the output addresses the task,
        has complete evidence chains, and avoids hallucinations. Falls back
        to heuristic verification if the LLM call fails.
        """
        # Quick heuristic gate — if obviously broken, skip expensive LLM call
        heuristic_ok, heuristic_reason = self._self_verify_output_heuristic(output)
        if not heuristic_ok:
            return False, heuristic_reason

        try:
            total = (
                len(output.nuggets)
                + len(output.facts)
                + len(output.insights)
                + len(output.recommendations)
            )
            reflection_prompt = (
                "You are a quality reviewer for UX research outputs.\n\n"
                f"Task: {task.title}\n"
                f"Description: {task.description or 'N/A'}\n"
                f"Instructions: {getattr(task, 'instructions', '') or 'None'}\n\n"
                f"Generated Output (first 1500 chars):\n{(output.summary or '')[:1500]}\n\n"
                f"Findings: {len(output.nuggets)} nuggets, {len(output.facts)} facts, "
                f"{len(output.insights)} insights, {len(output.recommendations)} recommendations "
                f"({total} total)\n\n"
                "Evaluate:\n"
                "1. Does the output address the original task?\n"
                "2. Are findings specific and evidence-based (not generic)?\n"
                "3. Is the evidence chain complete (nuggets support facts support insights)?\n"
                "4. Are there obvious hallucinations or unsupported claims?\n\n"
                "Respond with EXACTLY one JSON object:\n"
                '{"verified": true, "confidence": 0.85, "reason": "one sentence"}'
            )
            response = await ollama.chat(
                messages=[{"role": "user", "content": reflection_prompt}],
                temperature=0.1,
            )
            content = response.get("message", {}).get("content", "")
            # Extract JSON from response (model may wrap in markdown)
            import re

            json_match = re.search(r'\{[^{}]*"verified"[^{}]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                verified = result.get("verified", True)
                reason = result.get("reason", "LLM reflection passed")
                logger.info(
                    f"LLM reflection: verified={verified}, confidence={result.get('confidence', '?')}, reason={reason}"
                )
                return verified, reason
            # If no JSON found, trust heuristic result
            return True, "LLM reflection returned non-JSON — heuristic passed"
        except Exception as e:
            logger.debug(f"LLM reflection failed ({e}), using heuristic")
            return True, "Heuristic verification passed (LLM reflection unavailable)"

    # --- Manual Skill Execution (from API/Chat) ---

    async def execute_skill(
        self,
        skill_name: str,
        project_id: str,
        files: list[str] | None = None,
        parameters: dict | None = None,
        user_context: str = "",
    ) -> SkillOutput:
        """Execute a skill manually (from API or chat).

        Returns:
            SkillOutput with findings.
        """
        skill = registry.get(skill_name)
        if not skill:
            return SkillOutput(
                success=False,
                summary=f"Skill not found: {skill_name}",
                errors=[f"Unknown skill: {skill_name}"],
            )

        async with async_session() as db:
            project = await self._get_project(db, project_id)
            if not project:
                return SkillOutput(
                    success=False,
                    summary="Project not found",
                    errors=[f"Project not found: {project_id}"],
                )

            skill_input = SkillInput(
                project_id=project_id,
                files=files or [],
                parameters=parameters or {},
                user_context=user_context,
                project_context=project.project_context,
                company_context=project.company_context,
            )

            await broadcast_agent_status("working", f"Running {skill.display_name}...")

            try:
                output = await skill.execute(skill_input)

                # Self-verify the output quality (heuristic — no task for manual execution)
                verified, verify_reason = self._self_verify_output_heuristic(output)

                if verified:
                    task_status = TaskStatus.DONE
                    task_notes = output.summary
                else:
                    task_status = TaskStatus.IN_REVIEW
                    task_notes = f"[Verification failed] {verify_reason}\n\n{output.summary}"

                # Create a temporary task to store findings
                task = Task(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=f"Manual: {skill.display_name}",
                    skill_name=skill_name,
                    status=task_status,
                    progress=1.0,
                    agent_notes=task_notes,
                )
                db.add(task)

                # Store findings (non-fatal — embedding/vector errors shouldn't block skill output)
                try:
                    await self._store_findings(db, project_id, output, task)
                except Exception as store_err:
                    logger.warning(f"Failed to store findings for {skill_name}: {store_err}")
                    await db.commit()  # Commit the task even if findings storage fails

                skill_manager.record_execution(
                    skill_name, output.success, 0.8 if output.success else 0.2
                )

                if verified:
                    await broadcast_agent_status("idle", f"Completed: {skill.display_name}")
                else:
                    await broadcast_agent_status(
                        "warning", f"Needs review: {skill.display_name} — {verify_reason}"
                    )

                return output

            except Exception as e:
                logger.error(f"Manual skill execution failed: {e}")
                await broadcast_agent_status("error", str(e))
                return SkillOutput(success=False, summary=f"Execution failed: {e}", errors=[str(e)])

    async def plan_skill(self, skill_name: str, project_id: str, user_context: str = "") -> dict:
        """Generate a research plan using a skill."""
        skill = registry.get(skill_name)
        if not skill:
            return {"error": f"Skill not found: {skill_name}"}

        async with async_session() as db:
            project = await self._get_project(db, project_id)
            if not project:
                return {"error": f"Project not found: {project_id}"}

            skill_input = SkillInput(
                project_id=project_id,
                user_context=user_context,
                project_context=project.project_context,
                company_context=project.company_context,
            )

            return await skill.plan(skill_input)


# Singleton
agent = AgentOrchestrator()
