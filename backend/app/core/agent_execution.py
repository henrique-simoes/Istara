"""Agent task execution, skill routing, and governance hooks."""

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
from app.core.rag import ingest_chunks, retrieve_context
from app.core.resource_governor import governor
from app.core.self_check import Confidence, verify_claim
from app.core.self_improvement_policy import learning_signal_for_research_output
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


class AgentExecutionMixin:
    async def _execute_task(self, db: AsyncSession, task: Task, project: Project) -> None:
        """Execute a task using the appropriate skill."""
        logger.info(f"Executing task: {task.title} (skill: {task.skill_name or 'auto'})")

        if project.is_paused:
            logger.info(
                "Project %s is paused; task %s will stay in backlog",
                project.id,
                task.id,
            )
            task.status = TaskStatus.BACKLOG
            task.progress = 0.0
            task.agent_notes = "Project is paused; agent execution deferred."
            await db.commit()
            await broadcast_agent_status(
                "paused", f"Project paused: {project.name}", project_id=project.id
            )
            await broadcast_task_progress(
                task.id, 0.0, "Project paused; task deferred.", project_id=task.project_id
            )
            return

        # Checkpoint: started
        await create_checkpoint(db, task.id, self._agent_id, "started")

        # Move to in_progress and persist agent state
        task.status = TaskStatus.IN_PROGRESS
        task.progress = 0.1
        await db.commit()
        await self._persist_agent_state(AgentState.WORKING, task.title)
        await broadcast_agent_status(
            "working", f"Working on: {task.title}", project_id=task.project_id
        )
        await broadcast_task_progress(task.id, 0.1, "Starting task...", project_id=task.project_id)

        # Retrieve RAG context before skill selection (gives skills document awareness)
        rag_context = await retrieve_context(
            project.id, task.title + " " + (task.description or ""), top_k=5
        )

        # ── Plan-and-Execute: decompose complex auto-routed tasks before skill selection ──
        # Explicitly selected skills run directly. Complex auto tasks attempt a
        # DAG plan first so a broad keyword match does not collapse a multi-step
        # investigation into one oversized skill call.
        if self._should_attempt_research_plan(task):
            plan = await self._create_research_plan(task, project, rag_context)
            if plan and len(plan.steps) > 1:
                await self._execute_planned_task(db, task, project, plan, rag_context)
                await complete_checkpoint(db, task.id)
                return

        skill = await self._select_skill(task)
        if not skill:
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
            await broadcast_agent_status(
                "warning",
                f"Skill blocked: {skill.name} not in agent ACL",
                project_id=task.project_id,
            )
            return

        # Build skill input — include task instructions, context, and RAG documents
        task_context = task.user_context or task.description
        review_context = self._review_context_for_prompt(task)
        if review_context:
            task_context += f"\n\n## Human Review Feedback\n{review_context}"
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
                if f.is_file()
                and f.suffix.lower()
                in {".txt", ".md", ".pdf", ".docx", ".csv", ".mp3", ".wav", ".m4a", ".ogg"}
            ]

        await broadcast_task_progress(
            task.id, 0.3, f"Running {skill.display_name}...", project_id=task.project_id
        )

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
            except TimeoutError:
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

            # ── Operational response validation (if available) ──
            # This is a quality signal over the candidate summary, not formal
            # qualitative-coding reliability. Task-linked coding runs happen
            # after findings are stored through research_validity_service.
            try:
                import json as _json

                from app.core.adaptive_validation import AdaptiveSelector
                from app.core.validation import (
                    adversarial_review,
                    debate_rounds,
                    dual_run,
                    full_ensemble,
                    self_moa,
                )

                selector = AdaptiveSelector()
                method = await selector.select_method(project.id, skill.name, self.agent_id)

                if method and method != "skip" and output.summary:
                    await broadcast_task_progress(
                        task.id,
                        0.5,
                        f"Validating ({method})...",
                        project_id=task.project_id,
                    )
                    validation_fns = {
                        "self_moa": self_moa,
                        "adversarial_review": adversarial_review,
                        "dual_run": dual_run,
                        "full_ensemble": full_ensemble,
                        "debate_rounds": debate_rounds,
                    }
                    fn = validation_fns.get(method)
                    if fn:
                        from app.config import settings

                        validation_prompt = skill_input.user_context or task.description
                        validation_system = (
                            "Validate the candidate UX research output for accuracy, "
                            "completeness, evidence fit, and actionability."
                        )
                        validation_kwargs = {
                            "prompt": validation_prompt,
                            "system": validation_system,
                            "project_id": project.id,
                        }
                        if method == "adversarial_review":
                            validation_kwargs["initial_response"] = output.summary
                        else:
                            validation_kwargs["prompt"] = (
                                f"Task:\n{validation_prompt}\n\n"
                                f"Candidate output to validate:\n{output.summary}"
                            )

                        val_result = await asyncio.wait_for(
                            fn(**validation_kwargs),
                            timeout=max(
                                1, int(getattr(settings, "validation_timeout_seconds", 120))
                            ),
                        )
                        actual_method = val_result.method or method
                        task.validation_method = actual_method
                        task.validation_result = _json.dumps(
                            {
                                "requested_method": method,
                                "actual_method": actual_method,
                                "agreement_score": val_result.consensus.agreement_score,
                                "kappa": val_result.consensus.kappa,
                                "cosine_sim": val_result.consensus.cosine_sim,
                                "confidence": val_result.consensus.confidence,
                                "best_response": val_result.best_response,
                                "response_count": len(val_result.responses),
                                "route_evidence": val_result.metadata.get("route_evidence", []),
                                "models_used": val_result.metadata.get("models_used", []),
                                "assurance": val_result.metadata.get("assurance", actual_method),
                            }
                        )
                        task.consensus_score = val_result.consensus.agreement_score

                        # Record metrics for adaptive learning
                        await selector.record_outcome(
                            project.id,
                            skill.name,
                            self.agent_id,
                            actual_method,
                            val_result.consensus.agreement_score,
                            val_result.consensus.agreement_score >= 0.5,
                        )
                        logger.info(
                            "Validation [%s]: score=%.2f",
                            actual_method,
                            val_result.consensus.agreement_score,
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
                                "validation_method": actual_method,
                                "requested_validation_method": method,
                                "validation_passed": val_result.consensus.agreement_score >= 0.5,
                                "consensus_score": val_result.consensus.agreement_score,
                                "validation_quality": val_result.consensus.agreement_score,
                                "route_evidence": val_result.metadata.get("route_evidence", []),
                                "models_used": val_result.metadata.get("models_used", []),
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
            await broadcast_task_progress(
                task.id, 0.7, "Storing findings...", project_id=task.project_id
            )

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
                await broadcast_task_progress(
                    task.id, 0.8, "Verifying findings...", project_id=task.project_id
                )
                await self._verify_findings(db, project.id, output)

            # Self-verify output quality (LLM reflection with heuristic fallback)
            verified, verify_reason = await self._self_verify_output(task, output)
            learning_signal = learning_signal_for_research_output(
                execution_success=bool(output.success),
                verification_success=bool(verified),
            )
            quality_score = learning_signal.research_quality_score

            try:
                await self._record_reasoning_memory_for_task(
                    task=task,
                    project=project,
                    skill=skill,
                    output=output,
                    verified=verified,
                    verify_reason=verify_reason,
                    quality_score=quality_score,
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.debug(f"ReasoningBank task trace skipped: {e}")

            if verified:
                # Update task — passed verification
                await self._mark_task_ready_for_review(db, task, output.summary)

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

                await broadcast_task_progress(
                    task.id,
                    1.0,
                    "Complete — ready for review.",
                    outcome="ready_for_review",
                    project_id=task.project_id,
                )
                await self._persist_agent_state(AgentState.IDLE)
                await broadcast_agent_status(
                    "idle", f"Completed: {task.title}", project_id=task.project_id
                )
            else:
                # Verification failed — surface it for human review and feedback.
                task.agent_notes = f"[Verification failed] {verify_reason}\n\n{output.summary}"
                task.progress = 1.0
                await self._record_system_failed_review(
                    db,
                    task,
                    f"Agent self-verification failed: {verify_reason}",
                )
                await db.commit()

                await broadcast_task_progress(
                    task.id,
                    1.0,
                    f"Verification failed: {verify_reason}",
                    outcome="verification_failed",
                    project_id=task.project_id,
                )
                await self._persist_agent_state(AgentState.IDLE)
                await broadcast_agent_status(
                    "warning",
                    f"Needs attention: {task.title} — {verify_reason}",
                    project_id=task.project_id,
                )

            # Record skill usage and check health for self-evolution
            skill_manager.record_execution(
                skill.name,
                learning_signal.learning_success,
                quality_score,
                project_id=task.project_id,
            )
            try:
                health = skill_manager.get_skill_health(skill.name, project_id=task.project_id)
                try:
                    await telemetry_recorder.record_research_validity_event(
                        operation="memento_skill.health",
                        project_id=task.project_id,
                        task_id=task.id,
                        skill_name=skill.name,
                        agent_id=self.agent_id,
                        status=("success" if health.get("health_score", 0) >= 0.5 else "degraded"),
                        quality_score=health.get("health_score"),
                        error_type=(
                            None
                            if health.get("health_score", 0) >= 0.5
                            else "memento_skill_low_health"
                        ),
                    )
                except Exception as exc:
                    logger.debug(f"Memento skill health telemetry skipped: {exc}")
                # LLM-based skill improvement when quality is consistently low
                if health.get("executions", 0) >= 3 and health.get("avg_quality", 1.0) < 0.5:
                    # Ask LLM to reflect on why the skill is underperforming
                    improvement_text = ""
                    avg_quality = health.get("avg_quality", 0)
                    execution_count = health["executions"]
                    output_preview = (output.summary or "")[:300]
                    try:
                        # W3 (L7): skill-improvement reflection through the
                        # AgenticDispatcher (``spine.skill_reflection``).
                        from app.core.agentic import agentic
                        from app.core.agentic.types import TurnParams

                        reflection = await agentic.completion(
                            purpose="spine.skill_reflection",
                            project_id=project.id,
                            system=None,
                            messages=[
                                {
                                    "role": "user",
                                    "content": (
                                        f"Skill '{skill.name}' has been underperforming "
                                        f"(quality: {avg_quality:.0%} over "
                                        f"{execution_count} runs).\n"
                                        f"Last task: '{task.title}'\n"
                                        f"Last output (first 300 chars): {output_preview}\n"
                                        f"Errors: {output.errors}\n\n"
                                        "How should the skill's execution prompt be improved "
                                        "to produce better results? "
                                        "Be specific and concise (2-3 sentences)."
                                    ),
                                },
                            ],
                            params=TurnParams(temperature=0.3),
                            task_id=task.id,
                            spine_phase="governance",
                        )
                        improvement_text = reflection.text
                    except Exception:
                        improvement_text = (
                            f"Low quality ({avg_quality:.0%}) after {execution_count} runs"
                        )

                    skill_def = skill_manager.get(skill.name)
                    proposal = skill_manager.propose_improvement(
                        skill_name=skill.name,
                        field="execute_prompt",
                        current_value=(skill_def or {}).get("execute_prompt", "")[:200]
                        if isinstance(skill_def, dict)
                        else "",
                        proposed_value=improvement_text[:500],
                        reason=(
                            f"LLM reflection: quality {avg_quality:.0%} after "
                            f"{execution_count} runs"
                        ),
                        confidence=0.6,
                        project_id=task.project_id,
                    )
                    try:
                        from app.core.improvement_governance import improvement_governance

                        await improvement_governance.register_skill_update_proposal(
                            proposal.to_dict(),
                            project_id=task.project_id,
                        )
                    except Exception:
                        pass
                    await broadcast_suggestion(
                        (
                            f"Skill '{skill.display_name}' needs improvement "
                            f"(quality: {avg_quality:.0%}). An improvement proposal "
                            "has been created. Check Agents → Skill Proposals."
                        ),
                        project.id,
                    )
            except Exception:
                pass  # Don't fail task on self-evolution check

            # Autonomous skill creation check
            total_findings = len(output.nuggets) + len(output.facts) + len(output.insights)
            if learning_signal.learning_success and quality_score >= 0.8 and total_findings >= 3:
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

            state_label = "completed" if verified else "needs review"
            logger.info("Task %s: %s — %s", state_label, task.title, output.summary)

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

                resolution = await agent_learning.get_error_resolution(
                    self._agent_id,
                    error_msg,
                    project_id=task.project_id,
                )
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

            try:
                from app.core.reasoning_bank import reasoning_bank

                await reasoning_bank.record_trace(
                    project_id=task.project_id,
                    agent_id=self._agent_id,
                    query=f"{task.title}\n{task.description or ''}",
                    trajectory={
                        "task_id": task.id,
                        "skill_name": skill.name,
                        "error_message": error_msg,
                        "retry_count": task.retry_count,
                        "resolution_hint": resolution_hint,
                    },
                    outcome="failure",
                    source_kind="skill",
                    source_id=task.id,
                    tags=[skill.name, "memento", "exception"],
                    domain=skill.name,
                    judge_score=0.0,
                )
            except Exception as memory_err:
                logger.debug(f"ReasoningBank error trace skipped: {memory_err}")

            # Retry logic with backoff
            task.retry_count = (task.retry_count or 0) + 1
            task.last_retry_at = datetime.now(UTC)
            task.agent_notes = f"Error: {error_msg}{resolution_hint}"

            if task.retry_count < (task.max_retries or 3):
                task.status = TaskStatus.BACKLOG  # Return to backlog for retry
                await db.commit()
                await self._persist_agent_state(AgentState.ERROR, error_msg)
                await broadcast_agent_status(
                    "warning",
                    (
                        f"Task retry {task.retry_count}/{task.max_retries or 3}: "
                        f"{task.title} — {error_msg[:80]}"
                    ),
                    project_id=task.project_id,
                )
            else:
                task.progress = 1.0
                await self._record_system_failed_review(
                    db,
                    task,
                    f"Task failed after {task.retry_count} retries: {error_msg}{resolution_hint}",
                )
                await db.commit()
                await self._persist_agent_state(AgentState.ERROR, error_msg)
                await broadcast_agent_status(
                    "error",
                    (
                        f"Task failed after {task.retry_count} retries: "
                        f"{task.title} — {error_msg[:80]}"
                    ),
                    project_id=task.project_id,
                )

            # Leave checkpoint in place for crash recovery awareness

    async def _record_reasoning_memory_for_task(
        self,
        *,
        task: Task,
        project: Project,
        skill,
        output: SkillOutput,
        verified: bool,
        verify_reason: str,
        quality_score: float,
        trace_id: str,
    ) -> None:
        """Distill a completed skill execution into reusable reasoning memory."""
        from app.core.reasoning_bank import reasoning_bank

        await reasoning_bank.record_task_execution(
            project_id=project.id,
            agent_id=task.agent_id or self._agent_id,
            task_id=task.id,
            task_title=task.title,
            task_description=task.description or "",
            skill_name=skill.name,
            output_summary=output.summary or "",
            success=output.success,
            verified=verified,
            quality_score=quality_score,
            errors=list(output.errors or []),
            validation_reason=verify_reason,
            trace_id=trace_id,
        )

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
        usage = skill_manager.get_usage_stats(project_id=task.project_id)
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
            "plan_prompt": "Create a research plan for: {context}",
            "execute_prompt": (
                "Analyze the following data for patterns and insights.\n"
                "Context: {context}\n\nData:\n{content}"
            ),
            "output_schema": output.summary[:500] if output.summary else "Standard findings output",
        }

        try:
            proposal = skill_manager.propose_skill_creation(
                definition=proposed_definition,
                source_task_id=task.id,
                agent_id=self._agent_id,
                reason=f"High-quality output ({total_findings} findings) from task: {task.title}",
                confidence=min(70, 50 + total_findings * 5),
                project_id=task.project_id,
            )
            try:
                from app.core.improvement_governance import improvement_governance

                await improvement_governance.register_skill_creation_proposal(
                    proposal.to_dict(),
                    project_id=task.project_id,
                )
            except Exception:
                pass
            await broadcast_suggestion(
                (
                    f"New skill proposed: '{proposed_definition['display_name']}' — "
                    "review in Skill Creation Proposals."
                ),
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

        from app.core.agent_skill_tools import SKILL_KEYWORDS

        for keyword, skill_name in SKILL_KEYWORDS.items():
            if keyword in title_lower:
                skill = registry.get(skill_name)
                if skill:
                    return skill

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
        description embeddings.  Returns the best match above the current
        cosine similarity threshold, or None.
        """

        all_skills = registry.list_all()
        if not all_skills:
            return None

        task_text = f"{task.title} {task.description or ''}"
        if len(task_text.strip()) < 5:
            return None

        try:
            from app.core.reasoning_bank import reasoning_bank

            memory_context = await reasoning_bank.context_for_query(
                project_id=getattr(task, "project_id", "") or "",
                query=task_text,
                agent_id=getattr(task, "agent_id", None) or self._agent_id,
                source_kinds=["skill", "autoresearch"],
                limit=3,
                max_chars=900,
            )
            if memory_context:
                task_text = f"{task_text}\n{memory_context}"
        except Exception as exc:
            logger.debug(f"ReasoningBank routing context skipped: {exc}")

        # Build / refresh description embedding cache
        from app.core.embeddings import embed_text

        task_vec = await embed_text(task_text[:1200])
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

        threshold = _META_SKILL_SIMILARITY_THRESHOLD
        try:
            from app.core.meta_overrides import get_parameter_override

            threshold = float(
                get_parameter_override(
                    "agent.skill_similarity_threshold",
                    project_id=getattr(task, "project_id", ""),
                    default=threshold,
                )
            )
        except Exception:
            pass

        if best_skill and best_score >= threshold:
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

                # If agent has "skill_execution" capability but no explicit allowed_skills
                # in memory, allow all skills
                memory = json.loads(agent.memory) if agent.memory else {}
                allowed = memory.get("allowed_skills")
                if allowed is None:
                    return True  # No ACL = allow all
                return skill_name in allowed
        except Exception:
            return True  # On error, allow
