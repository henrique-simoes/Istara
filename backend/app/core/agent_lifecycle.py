"""Agent orchestrator lifecycle, inbox, collaboration, and task picking."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import (
    broadcast_agent_status,
    broadcast_agent_thinking,
    broadcast_finding_created,
    broadcast_plan_progress,
    broadcast_suggestion,
    broadcast_task_progress,
    broadcast_task_queue_update,
)
from app.config import settings
from app.core.agent_hooks import agent_hooks
from app.core.checkpoint import complete_checkpoint, create_checkpoint, update_checkpoint
from app.core.context_hierarchy import context_hierarchy
from app.core.datetime_utils import ensure_utc
from app.core.embeddings import TextChunk
from app.core.ollama import ollama
from app.core.rag import ingest_chunks, retrieve_context
from app.core.resource_governor import governor
from app.core.self_check import Confidence, verify_claim
from app.core.steering import steering_manager
from app.core.telemetry import telemetry_recorder
from app.models.agent import Agent, AgentState
from app.models.database import async_session
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.skills.base import SkillInput, SkillOutput
from app.skills.registry import registry
from app.skills.skill_manager import skill_manager

from app.core.agent_models import (
    _META_SKILL_SIMILARITY_THRESHOLD,
    _resolve_project_folder,
    ResearchPlan,
    ResearchStep,
)

logger = logging.getLogger("app.core.agent")

class AgentLifecycleMixin:
    def __init__(self, agent_id: str = "istara-main") -> None:
        self._running = False
        self._agent_id = agent_id
        self._current_task_id: str | None = None
        self._loop_interval = 30  # seconds between task checks
        self._idle_interval = 60  # seconds when no tasks available

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def _should_attempt_research_plan(self, task: Task) -> bool:
        """Return True when an auto-routed task is complex enough for DAG planning."""
        if task.skill_name:
            return False

        text = "\n".join(
            [
                task.title or "",
                task.description or "",
                getattr(task, "instructions", "") or "",
            ]
        )
        normalized = text.lower()
        if len(normalized.strip()) < 160:
            return False

        enumerated_steps = len(re.findall(r"(?:^|\s)\d+[.)]\s+", normalized)) >= 2
        bullet_steps = len(re.findall(r"(?m)^\s*[-*]\s+", text)) >= 2
        complex_markers = (
            "multi-stage",
            "multi step",
            "multi-step",
            "deep-dive",
            "decompose",
            "investigation",
            "contrast",
            "compare",
            "synthesize",
            "generate",
            "strategy",
            "visionary",
        )
        marker_hits = sum(1 for marker in complex_markers if marker in normalized)

        return enumerated_steps or bullet_steps or marker_hits >= 2 or len(normalized) >= 360

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
            except TimeoutError:
                pass

    def wake(self) -> None:
        """Wake the agent immediately to check for new tasks (e.g. after task assignment)."""
        if hasattr(self, "_wake_event"):
            self._wake_event.set()

    def stop(self) -> None:
        self._running = False
        logger.info("Agent Orchestrator stopped.")

    def _review_context_for_prompt(self, task: Task) -> str:
        """Compact human-review context for retries and revised tasks."""
        labels = task.get_labels() if hasattr(task, "get_labels") else []
        parts = []
        if getattr(task, "what_to_review", ""):
            parts.append(f"What to Review: {task.what_to_review}")
        if getattr(task, "last_review_feedback", ""):
            parts.append(f"Last human feedback: {task.last_review_feedback}")
        if labels:
            parts.append(f"Task labels: {json.dumps(labels)[:600]}")
        if getattr(task, "review_failure_category", None):
            parts.append(f"Failure category: {task.review_failure_category}")
        if getattr(task, "failure_streak", 0):
            parts.append(f"Consecutive unsuccessful reviews: {task.failure_streak}")
        return "\n".join(parts)

    async def _mark_task_ready_for_review(
        self,
        db: AsyncSession,
        task: Task,
        notes: str,
        progress: float = 1.0,
        review_state: str = "awaiting_review",
    ) -> None:
        task.status = TaskStatus.IN_REVIEW
        task.review_state = review_state
        task.next_agent_action = None
        task.progress = progress
        task.agent_notes = notes
        await db.commit()

    async def _record_system_failed_review(
        self,
        db: AsyncSession,
        task: Task,
        reason: str,
        *,
        next_review_state: str = "system_failed",
    ):
        """Expose agent/self-verification failure to humans instead of hiding it as Done."""
        from app.core.task_review import (
            SYSTEM_FAILED,
            diagnose_review_event,
            record_task_review_event,
        )

        event = await record_task_review_event(
            db,
            task,
            outcome=SYSTEM_FAILED,
            next_status=TaskStatus.IN_REVIEW,
            next_review_state=next_review_state,
            what_to_review=reason,
            created_by=self._agent_id,
            failure_category="agent_execution_failure",
            severity="major",
            quality_score=0.1,
            context_extra={"source": "agent_orchestrator"},
        )
        await diagnose_review_event(db, event.id)
        return event

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
                        agent_row.last_heartbeat_at = datetime.now(UTC)
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist agent state: {e}")

    async def _work_cycle(self) -> bool:
        """Run one work cycle. Returns True if a task was executed."""
        # ── Check project-bound steering queue FIRST — if there are pending
        # steering messages, create a steering task and execute it before
        # checking the normal task queue.
        if await self._process_project_steering():
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
                logger.warning(
                    f"Project not found for task {task.id} — sending to review (orphaned)"
                )
                task.agent_notes = f"Project not found: {task.project_id}"
                event = await self._record_system_failed_review(
                    db,
                    task,
                    f"Project not found for task {task.id}: {task.project_id}",
                    next_review_state="blocked",
                )
                await db.commit()
                from app.core.task_review import record_review_side_effects

                await record_review_side_effects(event)
                return False

            if project.is_paused:
                logger.info(
                    "Project %s is paused; deferring task %s for agent %s",
                    project.id,
                    task.id,
                    self._agent_id,
                )
                task.status = TaskStatus.BACKLOG
                task.agent_notes = "Project is paused; agent execution deferred."
                await db.commit()
                await broadcast_agent_status("paused", f"Project paused: {project.name}", project_id=project.id)
                return False

            # 3. Execute the task (register with governor for concurrent limits)
            governor.register_agent("task-executor")
            self._current_task_id = task.id
            await steering_manager.mark_working(self._agent_id, project_id=task.project_id)
            try:
                await self._execute_task(db, task, project)
            finally:
                self._current_task_id = None
                governor.unregister_agent("task-executor")
                await steering_manager.mark_idle(self._agent_id, project_id=task.project_id)

            # 4. Check queue depth and adapt loop interval
            pending_result = await db.execute(
                select(func.count(Task.id))
                .join(Project, Project.id == Task.project_id)
                .where(
                    Task.status == TaskStatus.BACKLOG,
                    Project.is_paused.is_(False),
                    Task.project_id == task.project_id,
                )
            )
            in_progress_result = await db.execute(
                select(func.count(Task.id))
                .join(Project, Project.id == Task.project_id)
                .where(
                    Task.status == TaskStatus.IN_PROGRESS,
                    Project.is_paused.is_(False),
                    Task.project_id == task.project_id,
                )
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
                    "working",
                    f"Task complete. {pending + in_progress} remaining in queue.",
                    project_id=task.project_id,
                )
            else:
                self._loop_interval = 30  # Back to normal
                await broadcast_agent_status("idle", "All tasks processed.", project_id=task.project_id)

            # ── Check follow-up queue — only processed when agent would
            # otherwise stop (no more tasks in the pipeline). This matches
            # pi-mono's followUpQueue pattern.
            follow_up_msgs = await steering_manager.get_follow_up(
                self._agent_id,
                project_id=task.project_id,
            )
            if follow_up_msgs:
                logger.info(f"Follow-up messages for {self._agent_id}: {len(follow_up_msgs)}")
                for msg in follow_up_msgs:
                    await steering_manager.mark_working(self._agent_id, project_id=project.id)
                    try:
                        await self._execute_steering_message(msg, project)
                    finally:
                        await steering_manager.mark_idle(self._agent_id, project_id=project.id)
                return True

            return True

    async def _process_project_steering(self) -> bool:
        project_ids = await steering_manager.project_ids_with_queued_steering(self._agent_id)
        if not project_ids:
            return False

        async with async_session() as db:
            for project_id in project_ids:
                project = await self._get_project(db, project_id)
                if not project:
                    logger.warning(
                        "Dropping steering messages for missing project %s and agent %s",
                        project_id,
                        self._agent_id,
                    )
                    await steering_manager.clear_steering(self._agent_id, project_id=project_id)
                    continue
                if project.is_paused:
                    logger.info(
                        "Project %s is paused; deferring steering for agent %s",
                        project.id,
                        self._agent_id,
                    )
                    continue
                steering_msgs = await steering_manager.get_steering(
                    self._agent_id,
                    project_id=project.id,
                )
                if not steering_msgs:
                    continue
                logger.info(
                    "Project-scoped steering messages detected for %s in %s: %s",
                    self._agent_id,
                    project.id,
                    len(steering_msgs),
                )
                for msg in steering_msgs:
                    await steering_manager.mark_working(self._agent_id, project_id=project.id)
                    try:
                        await self._execute_steering_message(msg, project)
                    finally:
                        await steering_manager.mark_idle(self._agent_id, project_id=project.id)
                return True
        return False

    async def _get_project(self, db: AsyncSession, project_id: str) -> Project | None:
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def _execute_steering_message(self, msg, project: Project | None = None) -> None:
        """Execute a steering message as an interim task.

        Steering messages are user-injected mid-execution instructions.
        They're treated as high-priority tasks that interrupt the normal
        task queue (but never interrupt a skill that's already running).

        This mirrors pi-mono's pattern where steering messages are
        delivered after the current turn completes.
        """

        message_text = msg.message if hasattr(msg, "message") else str(msg)
        source = msg.source if hasattr(msg, "source") else "user"
        metadata = getattr(msg, "metadata", {}) if hasattr(msg, "metadata") else {}
        project_id = str(metadata.get("project_id") or "").strip()

        if project is None and project_id:
            async with async_session() as db:
                project = await self._get_project(db, project_id)

        if not project:
            logger.warning(
                "Skipping steering message for %s because it has no valid project context",
                self._agent_id,
            )
            return

        if project.is_paused:
            logger.info(
                "Skipping steering message for paused project %s and agent %s",
                project.id,
                self._agent_id,
            )
            await broadcast_agent_status("paused", f"Project paused: {project.name}", project_id=project.id)
            return

        project_context = "\n".join(
            part
            for part in [
                project.name,
                project.description,
                project.project_context,
                project.guardrails,
            ]
            if part
        )

        logger.info(
            "Executing steering message (%s) for project %s: %s",
            source,
            project.id,
            message_text[:100],
        )

        # Broadcast that we're processing a steering message
        await broadcast_agent_status(
            "working",
            f"Processing steering message: {message_text[:80]}...",
            project_id=project.id,
        )

        try:
            # Create a temporary skill input from the steering message
            from app.skills.registry import SkillInput
            from app.skills.skill_manager import skill_manager

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
                    project_id=project.id,
                    task_id="",
                    parameters={"mode": "analyze"},
                    user_context=message_text,
                    project_context=project_context,
                    company_context=project.company_context or "",
                )
                output = await asyncio.wait_for(skill.execute(skill_input), timeout=120)

                # Broadcast the result
                await broadcast_agent_status(
                    "idle",
                    f"Steering message processed ({skill.display_name}): {output.summary[:120]}..."
                    if output.summary
                    else f"Steering message processed ({skill.display_name})",
                    project_id=project.id,
                )
            else:
                # No matching skill — use the general LLM to respond
                response = await ollama.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are Istara's main agent. Respond helpfully to the "
                                f"user's steering message for project {project.name}."
                            ),
                        },
                        {"role": "user", "content": message_text},
                    ]
                )
                reply = response.get("message", {}).get("content", "")
                await broadcast_agent_status(
                    "idle",
                    f"Steering response: {reply[:200]}...",
                    project_id=project.id,
                )
        except TimeoutError:
            logger.warning("Steering message execution timed out")
            await broadcast_agent_status(
                "warning",
                "Steering message timed out after 2 minutes",
                project_id=project.id,
            )
        except Exception as e:
            logger.error(f"Steering message execution failed: {e}")
            await broadcast_agent_status(
                "warning",
                f"Steering message failed: {str(e)[:100]}",
                project_id=project.id,
            )

    def _is_in_backoff(self, task: Task) -> bool:
        """Check if a task is still within its retry backoff window."""
        if task.last_retry_at and (task.retry_count or 0) > 0:
            # Backoff delays: [5, 15, 45, 120] seconds (capped at 120)
            backoff = min(5 * (3 ** (task.retry_count - 1)), 120)
            elapsed = (datetime.now(UTC) - ensure_utc(task.last_retry_at)).total_seconds()
            if elapsed < backoff:
                return True
        return False

    async def _process_a2a_inbox(self, db: AsyncSession) -> None:
        """Process pending A2A collaboration requests from other agents."""
        try:
            from app.services.a2a import get_project_inbox, mark_read

            messages = await get_project_inbox(db, self._agent_id, unread_only=True, limit=3)
            for msg in messages:
                msg_project_id = msg.get("project_id", "") if isinstance(msg, dict) else ""
                if not msg_project_id:
                    continue
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
                    await mark_read(db, msg_id, project_id=msg_project_id)
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

            if data.get("type") == "pi_delegate":
                # Governed Pi delegation: the A2A gate chain (auth, rate, size,
                # replay, project scope, persist, audit) already ran in the route;
                # this is where the admitted work actually executes. Only Pi-
                # selected delegations run through the real Pi Agent.
                from app.core.pi_replacement import pi_replacement_requested
                from app.core.pi_runtime.seams import run_pi_delegation

                metadata = data.get("metadata") or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata) if metadata else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                if not pi_replacement_requested(metadata=metadata):
                    return
                project_id = data.get("project_id") or metadata.get("project_id")
                msg_project_id = msg.get("project_id", "") if isinstance(msg, dict) else ""
                if not project_id or (msg_project_id and msg_project_id != project_id):
                    return
                task_text = data.get("task") or data.get("text") or data.get("message") or ""
                delegation = await run_pi_delegation(
                    project_id=project_id,
                    task_text=str(task_text),
                    agent_id=self._agent_id,
                    metadata=metadata,
                )
                if delegation is None:
                    return
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
                    message_type="response",
                    content=(delegation.get("text") or "Pi delegation completed.")[:4000],
                    project_id=project_id,
                    metadata={
                        "project_id": project_id,
                        "engine": "pi",
                        "delegation_result": True,
                        "turn_status": delegation.get("status"),
                        "endpoint_id": delegation.get("endpoint_id"),
                    },
                )
                return

            if data.get("type") == "mece_report_request":
                from app.core.report_manager import report_manager
                from app.models.project_report import ProjectReport

                project_id = data.get("project_id")
                task_id = data.get("task_id")
                msg_project_id = msg.get("project_id", "") if isinstance(msg, dict) else ""
                if not project_id or (msg_project_id and msg_project_id != project_id):
                    return
                if task_id:
                    task = await db.get(Task, task_id)
                    if not task or task.project_id != project_id:
                        return

                # 1. Ensure MECE categorization on all eligible L2/L3 reports.
                # ProjectReport derives finding counts from finding_ids_json, so
                # filter in Python instead of relying on a transient ORM attribute.
                result = await db.execute(
                    select(ProjectReport).where(
                        ProjectReport.project_id == project_id,
                    )
                )
                reports = []
                for report in result.scalars().all():
                    try:
                        finding_ids = json.loads(report.finding_ids_json or "[]")
                    except (json.JSONDecodeError, TypeError):
                        finding_ids = []
                    if isinstance(finding_ids, list) and len(finding_ids) >= 3:
                        reports.append(report)
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
                    content=(
                        "Consulting-grade MECE reporting completed for project "
                        f"{project_id}. Updated {updated_count} reports."
                    ),
                    project_id=project_id,
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
            metadata_project_id = metadata.get("project_id") or msg.get("project_id", "")
            if metadata_project_id and metadata_project_id != task.project_id:
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

            thread = await get_conversation_thread(
                db,
                context_id,
                project_id=task.project_id,
            )

            # Build LLM messages from conversation history
            from app.core.agent_identity import get_capability_card

            card = get_capability_card(self._agent_id)
            specialties = metadata.get("specialties_needed", card.get("specialties", []))
            rag = await retrieve_context(
                task.project_id, task.title + " " + (task.description or "")
            )
            specialties_label = ", ".join(specialties) if specialties else "UX research"

            llm_messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are {self._agent_id}, a specialist in: {specialties_label}. "
                        f"Provide expert analysis. You are collaborating with {msg_from} "
                        f"on task '{task.title}'."
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
                project_id=task.project_id,
                metadata={
                    "task_id": task_id,
                    "project_id": task.project_id,
                    "context_id": context_id,
                    "responding_to": msg_id,
                },
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
            from app.services.a2a import get_messages, send_message

            # Find a collaborator — prefer devops for data quality, ux-eval for UX
            collaborators = ["istara-devops", "istara-ux-eval", "istara-ui-audit"]
            target = next((c for c in collaborators if c != self._agent_id), collaborators[0])

            context_id = f"debate-{task.id}-{uuid.uuid4().hex[:8]}"
            await send_message(
                db=db,
                from_agent_id=self._agent_id,
                to_agent_id=target,
                message_type="debate_request",
                content=(
                    "I need a critical review of this analysis.\n\n"
                    f"Task: {task.title}\n\nOutput:\n{output.summary[:1500]}"
                ),
                project_id=task.project_id,
                metadata={
                    "task_id": task.id,
                    "project_id": task.project_id,
                    "context_id": context_id,
                },
            )
            logger.info(f"A2A debate initiated with {target} for task {task.id}")

            # Wait for response (up to 30s, polling every 3s)
            for _ in range(10):
                await asyncio.sleep(3)
                msgs = await get_messages(
                    db,
                    self._agent_id,
                    unread_only=True,
                    limit=5,
                    project_id=task.project_id,
                )
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
                                    "content": (
                                        "Synthesize two perspectives on the same research "
                                        "analysis into a single improved output."
                                    ),
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        f"Original analysis:\n{output.summary[:1000]}\n\n"
                                        f"Critique from {target}:\n{critique[:1000]}\n\n"
                                        "Produce a refined analysis that addresses the critique."
                                    ),
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
            project_id = metadata.get("project_id") or msg.get("project_id", "")
            task_id = metadata.get("task_id", "")
            if task_id:
                task = await db.get(Task, task_id)
                if not task:
                    return
                if project_id and project_id != task.project_id:
                    return
                project_id = task.project_id
            if not project_id:
                return

            response = await ollama.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are {self._agent_id}, a critical reviewer. Identify gaps, "
                            "unsupported claims, missing perspectives, and areas for "
                            "improvement. Be constructive but rigorous."
                        ),
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
                project_id=project_id,
                metadata={
                    "context_id": metadata.get("context_id", ""),
                    "task_id": task_id,
                    "project_id": project_id,
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
            from app.services.a2a import send_message as a2a_send

            async with async_session() as db:
                task = (
                    await db.execute(
                        select(Task).where(
                            Task.id == task_id,
                            Task.project_id == project_id,
                        )
                    )
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
                    project_id=project_id,
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
            .join(Project, Project.id == Task.project_id)
            .where(
                Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                Task.agent_id == self._agent_id,
                Project.is_paused.is_(False),
                # Skip locked tasks (locked by someone else)
                or_(
                    Task.locked_by.is_(None),
                    Task.locked_by == self._agent_id,
                    Task.lock_expires_at < datetime.now(UTC),
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
                .join(Project, Project.id == Task.project_id)
                .where(
                    Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                    Task.agent_id.is_(None),
                    Project.is_paused.is_(False),
                )
                .order_by(priority_order, Task.position.asc(), Task.created_at.asc())
                .limit(10)
            )
            for task in result.scalars().all():
                if not self._is_in_backoff(task):
                    return task

        return None
