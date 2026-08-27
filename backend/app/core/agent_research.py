"""Agent research planning, finding storage, verification, and skill APIs."""

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
from app.core.token_counter import count_tokens
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

class AgentResearchMixin:
    async def _execute_general_task(self, db: AsyncSession, task: Task, project: Project) -> None:
        """Handle tasks without a specific skill — use general LLM reasoning."""
        trace_id = __import__("uuid").uuid4().hex[:36]
        context = await retrieve_context(project.id, task.title + " " + (task.description or ""))

        # Use the full context hierarchy as system prompt
        system_prompt = await context_hierarchy.compose_context(
            db,
            project_id=project.id,
            task_context=task.user_context or task.description,
        )

        if context.has_context:
            system_prompt += f"\n\n## Relevant Documents\n{context.context_text}"

        from app.core.agent_skill_tools import (
            build_run_skill_tool,
            format_candidate_skill_context,
            rank_skill_candidates,
        )

        skill_candidates = await rank_skill_candidates(
            task=task,
            project=project,
            agent_id=self._agent_id,
            db=db,
            limit=settings.agent_react_skill_candidate_limit,
        )
        candidate_context = format_candidate_skill_context(skill_candidates)
        if candidate_context:
            system_prompt += (
                "\n\n"
                f"{candidate_context}\n"
                "Use the run_skill tool only when a candidate skill materially improves the "
                "answer. Do not invent skill names outside the enum."
            )

        # Build user message with all task fields
        user_parts = [f"Task: {task.title}", f"Details: {task.description}"]
        if task.user_context:
            user_parts.append(f"Additional context: {task.user_context}")
        if getattr(task, "instructions", None):
            user_parts.append(f"Specific instructions: {task.instructions}")
        user_msg = "\n\n".join(user_parts)

        # Tool-augmented ReAct loop — same tools available in chat.
        # W3 (L1): the loop transport migrated to the AgenticDispatcher
        # (``spine.react``); prompt building, skill-candidate constraint, tool
        # execution, and telemetry stay here. ONE Pi session per task.
        max_agent_tool_iterations = 5

        try:
            from app.skills.system_actions import OPENAI_TOOLS, execute_tool

            use_tools = True
        except ImportError:
            use_tools = False
            OPENAI_TOOLS = []
            execute_tool = None

        skill_tools = build_run_skill_tool(skill_candidates)
        available_tools = [*OPENAI_TOOLS, *skill_tools]
        candidate_by_name = {candidate.name: candidate for candidate in skill_candidates}

        tool_names = [t.get("function", {}).get("name", "") for t in available_tools]
        tool_names = [name for name in tool_names if name]
        # Per-run dynamic tools for the Pi path (master plan §5.3): the ranked
        # run_skill schema is sent with the session catalog; the Python-side
        # allowlist (tool_names) stays the authority on both engines.
        extra_tools = [
            {
                "name": t.get("function", {}).get("name", ""),
                "description": t.get("function", {}).get("description", ""),
                "parameters": t.get("function", {}).get("parameters", {}),
            }
            for t in skill_tools
        ]

        async def _react_tool_executor(tool_name, tool_args, _project_id, _agent_id):
            # Tool-call arguments arrive pre-parsed from the engine; record the
            # parse telemetry the manual loop recorded per call.
            asyncio.create_task(
                telemetry_recorder.record_json_parse(
                    trace_id=trace_id,
                    model_name="",  # Model name not available at this scope
                    success=True,
                    agent_id=self._agent_id,
                    project_id=project.id,
                )
            )
            logger.info(f"Agent tool call: {tool_name}({list((tool_args or {}).keys())})")
            if tool_name == "run_skill":
                return await self._execute_react_skill_tool(
                    db=db,
                    task=task,
                    project=project,
                    params=tool_args,
                    candidate_by_name=candidate_by_name,
                    trace_id=trace_id,
                    rag_context=context,
                )
            if execute_tool is not None:
                started = datetime.now(UTC)
                tool_result = await execute_tool(
                    tool_name, tool_args, project.id, self._agent_id
                )
                duration_ms = (datetime.now(UTC) - started).total_seconds() * 1000
                asyncio.create_task(
                    telemetry_recorder.record_span(
                        trace_id=trace_id,
                        operation="tool_call",
                        tool_name=tool_name,
                        tool_success=bool(
                            isinstance(tool_result, dict)
                            and tool_result.get("success", True)
                        ),
                        tool_duration_ms=duration_ms,
                        agent_id=self._agent_id,
                        project_id=project.id,
                        task_id=task.id,
                    )
                )
                return tool_result
            return {"success": False, "error": "Tool executor unavailable"}

        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        outcome = await agentic.react(
            purpose="spine.react",
            project_id=project.id,
            agent_id=self._agent_id,
            session_key=f"task:{task.id}",
            system=system_prompt,
            messages=[],
            user_text=user_msg,
            tool_executor=_react_tool_executor if (use_tools or skill_tools) else None,
            tool_names=tool_names,
            tools=available_tools or None,
            extra_tools=extra_tools or None,
            params=TurnParams(max_turns=max_agent_tool_iterations),
            task_id=task.id,
            spine_phase="execution",
        )
        result = outcome.text
        tools_used = [tc.get("tool", "") for tc in outcome.tool_calls]

        # Log tool usage
        if tools_used:
            tool_summary = f"[Tools used: {', '.join(tools_used)}]\n\n"
        else:
            tool_summary = ""

        # Quality check
        if not result or len(result.strip()) < 20:
            task.agent_notes = (
                f"{tool_summary}[Verification failed] Response too short or empty\n\n{result}"
            )
            task.progress = 1.0
            await self._record_system_failed_review(
                db,
                task,
                "General agent response was too short or empty.",
            )
            await db.commit()
            await broadcast_task_progress(task.id, 1.0, "Verification failed: response too short")
            await self._persist_agent_state(AgentState.IDLE)
            await broadcast_agent_status("warning", f"Needs attention: {task.title}", project_id=task.project_id)
        else:
            await self._mark_task_ready_for_review(db, task, f"{tool_summary}{result}")
            await broadcast_task_progress(task.id, 1.0, "Complete — ready for review.")
            await self._persist_agent_state(AgentState.IDLE)
            await broadcast_agent_status("idle", f"Completed: {task.title}", project_id=task.project_id)

    async def _execute_react_skill_tool(
        self,
        *,
        db: AsyncSession,
        task: Task,
        project: Project,
        params: dict,
        candidate_by_name: dict,
        trace_id: str,
        rag_context,
    ) -> dict:
        """Execute the constrained ReAct skill tool and return a compact observation."""
        from app.core.agent_skill_tools import compact_skill_observation, execute_ranked_skill_tool

        skill_name = str(params.get("skill_name") or "").strip()
        candidate = candidate_by_name.get(skill_name)
        if not candidate:
            return {
                "success": False,
                "error": f"Skill '{skill_name}' is not in the ranked candidate set.",
                "allowed_skills": list(candidate_by_name),
            }

        if not await self._check_agent_skill_acl(task.agent_id, skill_name):
            return {"success": False, "error": f"Skill '{skill_name}' is not allowed for this agent."}

        skill = registry.get(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_name}"}

        objective = str(params.get("objective") or task.title)
        extra_context = str(params.get("context") or "")
        task_context = (
            f"Objective: {objective}\n"
            f"Task: {task.title}\n"
            f"Description: {task.description or ''}\n"
            f"Rationale: {params.get('rationale') or ''}\n"
            f"{extra_context}"
        ).strip()
        if task.user_context:
            task_context += f"\n\nAdditional context: {task.user_context}"
        if getattr(task, "instructions", None):
            task_context += f"\n\nSpecific instructions: {task.instructions}"
        if rag_context.has_context:
            task_context += f"\n\n## Relevant Documents\n{rag_context.context_text}"

        skill_input = SkillInput(
            project_id=project.id,
            task_id=task.id,
            urls=task.get_urls() if hasattr(task, "get_urls") else [],
            parameters={"mode": "analyze", "called_from": "react_tool"},
            user_context=task_context,
            project_context=project.project_context,
            company_context=project.company_context,
        )

        use_project_files = params.get("use_project_files", True)
        if use_project_files is not False:
            folder = _resolve_project_folder(project, project.id)
            if folder.exists():
                skill_input.files = [
                    str(f)
                    for f in folder.iterdir()
                    if f.is_file()
                    and f.suffix.lower()
                    in {".txt", ".md", ".pdf", ".docx", ".csv", ".mp3", ".wav", ".m4a", ".ogg"}
                ]

        output, duration_ms = await execute_ranked_skill_tool(
            skill_name=skill_name,
            skill_input=skill_input,
            trace_id=trace_id,
            agent_id=self._agent_id,
            project_id=project.id,
            task_id=task.id,
            timeout_seconds=settings.agent_react_skill_tool_timeout_seconds,
        )
        learning_signal = learning_signal_for_research_output(
            execution_success=bool(output.success),
        )

        skill_manager.record_execution(
            skill_name,
            learning_signal.learning_success,
            learning_signal.research_quality_score,
            project_id=project.id,
        )
        task.skill_name = skill_name
        if output.success:
            try:
                await self._store_findings(db, project.id, output, task)
            except Exception as exc:
                logger.debug("ReAct skill finding storage skipped: %s", exc)
        await db.commit()

        await telemetry_recorder.record_span(
            trace_id=trace_id,
            operation="tool_call",
            skill_name=skill_name,
            tool_name="run_skill",
            tool_success=output.success,
            tool_duration_ms=duration_ms,
            duration_ms=duration_ms,
            status="success" if output.success else "error",
            quality_score=learning_signal.research_quality_score,
            agent_id=self._agent_id,
            project_id=project.id,
            task_id=task.id,
        )

        try:
            from app.core.reasoning_bank import reasoning_bank

            await reasoning_bank.record_trace(
                project_id=project.id,
                agent_id=self._agent_id,
                query=f"{task.title}\n{task.description or ''}",
                trajectory={
                    "tool": "run_skill",
                    "skill_name": skill_name,
                    "candidate_score": candidate.score,
                    "candidate_reasons": candidate.reasons,
                    "summary": output.summary,
                    "json_success": output.json_success,
                    "learning_state": learning_signal.learning_state,
                },
                outcome=learning_signal.learning_state,
                source_kind="skill",
                source_id=task.id,
                tags=[skill_name, "memento", "react-tool"],
                domain=skill_name,
                judge_score=learning_signal.research_quality_score,
            )
        except Exception as exc:
            logger.debug("ReAct skill reasoning memory skipped: %s", exc)

        observation = compact_skill_observation(skill_name, output)
        observation["duration_ms"] = round(duration_ms, 1)
        observation["candidate"] = candidate.to_dict()
        return observation

    # ── Plan-and-Execute Methods ──────────────────────────────────────

    async def _create_research_plan(
        self, task: Task, project: Project, rag_context
    ) -> ResearchPlan | None:
        """Ask the LLM to decompose a complex task into ordered research steps."""
        try:
            from app.core.agent_skill_tools import (
                format_candidate_skill_context,
                rank_skill_candidates,
            )

            candidates = await rank_skill_candidates(
                task=task,
                project=project,
                agent_id=self._agent_id,
                limit=max(8, settings.agent_react_skill_candidate_limit),
                include_semantic=False,
            )
            skill_names = [candidate.name for candidate in candidates]
            if not skill_names:
                skill_names = [s.name for s in registry.list_all()[:25]]
            candidate_context = format_candidate_skill_context(candidates)
            step_schema = {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "skill_name": {"enum": [*skill_names, None]},
                                "depends_on": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "requires_react": {"type": "boolean"},
                                "success_criteria": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [
                                "id",
                                "description",
                                "skill_name",
                                "depends_on",
                                "requires_react",
                                "success_criteria",
                            ],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["steps"],
                "additionalProperties": False,
            }
            plan_prompt = (
                "You are a research planning agent. Decompose this task into 2-5 "
                "concrete steps.\n\n"
                f"Task: {task.title}\n"
                f"Description: {task.description or 'No description'}\n"
                f"Instructions: {getattr(task, 'instructions', '') or 'None'}\n"
                f"Available candidate skills: {', '.join(skill_names)}\n"
                f"{candidate_context}\n\n"
                "For each step, provide:\n"
                "- id: step_1, step_2, etc.\n"
                "- description: what to do\n"
                "- skill_name: one candidate skill to use, or null for general reasoning/ReAct\n"
                "- depends_on: list of step IDs this step depends on (empty [] if independent)\n\n"
                "Steps with empty depends_on can run in parallel.\n\n"
                "Respond only with the attached JSON schema. "
                'If this is a simple task that doesn\'t need decomposition, respond: {"steps": []}'
            )
            # W3 (L2): structured plan call through the AgenticDispatcher
            # (``spine.plan``); the same step schema drives both engines
            # (forced-tool structured output on Pi, response_format on legacy).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.structured(
                purpose="spine.plan",
                project_id=project.id,
                system=None,
                messages=[{"role": "user", "content": plan_prompt}],
                schema=step_schema,
                params=TurnParams(
                    temperature=0.3,
                    max_tokens=900,
                    min_context=(
                        count_tokens(plan_prompt)
                        + count_tokens(json.dumps(step_schema, ensure_ascii=False))
                        + 900
                    ),
                    thinking_mode="off",
                ),
                task_id=task.id,
                spine_phase="plan",
            )
            data = outcome.value or None
            logger.info(f"Research plan raw content: {outcome.text}")
            await telemetry_recorder.record_json_parse(
                trace_id=uuid.uuid4().hex[:36],
                model_name=getattr(self, "model_name", ""),
                success=bool(data),
                agent_id=self._agent_id,
                project_id=project.id,
            )
            if data:
                steps = [
                    ResearchStep(
                        id=s.get("id", f"step_{i}"),
                        description=s.get("description", ""),
                        skill_name=s.get("skill_name")
                        if s.get("skill_name") in set(skill_names)
                        else None,
                        depends_on=s.get("depends_on", []),
                    )
                    for i, s in enumerate(data.get("steps", []))
                    if isinstance(s, dict)
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

        await self._mark_task_ready_for_review(
            db,
            task,
            f"[Research Plan]\n{plan_summary}\n\n[Results]\n{compiled}",
        )

        await broadcast_task_progress(
            task.id, 1.0, f"Plan complete — {len(plan.past_steps)} steps ({total_steps} planned)."
        )
        await self._persist_agent_state(AgentState.IDLE)
        await broadcast_agent_status("idle", f"Completed plan: {task.title}", project_id=task.project_id)

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
                # W3 (L3): skill-less plan step through the AgenticDispatcher
                # (``spine.step_execute``); DAG-parallel callers fan out to
                # parallel dispatcher calls exactly as before.
                from app.core.agentic import agentic
                from app.core.agentic.types import TurnParams

                outcome = await agentic.completion(
                    purpose="spine.step_execute",
                    project_id=project.id,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Research step: {step.description}\n\n"
                                f"Context from previous steps:\n{prev_context}"
                            ),
                        },
                    ],
                    params=TurnParams(),
                    task_id=task.id,
                    spine_phase="execution",
                )
                step.result = outcome.text
            step.status = "completed"
        except TimeoutError:
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
        """Store visible candidate findings without bypassing the Research Spine."""
        output.mark_research_artifacts_candidate()

        for nugget_data in output.nuggets or []:
            tags = nugget_data.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []
            tags = [t for t in tags if t and (len(t.strip()) >= 2 or t.startswith("ux-law:"))]
            nugget_data["tags"] = tags

        skill = registry.get(task.skill_name) if task.skill_name else None
        skill_phase = skill.phase.value if skill else None

        nugget_phase = skill_phase or "discover"
        fact_phase = skill_phase or "define"
        insight_phase = skill_phase or "define"
        rec_phase = skill_phase or "deliver"

        # Track created IDs for auto-linking
        created_nugget_ids: list[str] = []
        created_fact_ids: list[str] = []
        created_insight_ids: list[str] = []
        created_recommendation_ids: list[str] = []
        created_evidence_unit_ids: list[str] = []
        finding_agent_id = task.agent_id or self.agent_id

        from app.services.research_finding_links import persist_scoped_derivation_links as persist_links  # noqa: E501,I001

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
                agent_id=finding_agent_id,
                task_id=task.id,
                text=nugget_data.get("text", ""),
                source=nugget_data.get("source", task.title),
                source_location=nugget_data.get("source_location", ""),
                tags=json.dumps(_enriched_tags),
                phase=nugget_phase,
                confidence=_conf_val,
            )
            db.add(nugget)
            created_nugget_ids.append(nid)

            evidence_unit_id = None
            source_document_id = nugget_data.get("source_document_id")
            source_location = nugget_data.get("source_location", "")
            exact_source_text = str(
                nugget_data.get("source_text")
                or nugget_data.get("source_quote")
                or nugget_data.get("quote")
                or ""
            ).strip()
            has_exact_source_span = bool(source_document_id and source_location and exact_source_text)
            evidence_source_text = (
                exact_source_text if has_exact_source_span else str(nugget_data.get("text", ""))
            )[:2000]
            units = []
            if evidence_source_text.strip():
                try:
                    from app.services.research_validity_service import persist_task_nugget_evidence_units
                    units = await persist_task_nugget_evidence_units(
                        db,
                        project_id=project_id,
                        task_id=task.id,
                        nugget_id=nid,
                        source_text=evidence_source_text,
                        source_location=source_location,
                        source_document_id=source_document_id,
                        method=task.skill_name or "",
                        phase=nugget_phase,
                        source_type="source_span" if has_exact_source_span else "candidate_atom",
                        candidate_only=not has_exact_source_span,
                    )
                    for unit in units:
                        if not evidence_unit_id:
                            evidence_unit_id = unit.id
                        if has_exact_source_span:
                            created_evidence_unit_ids.append(unit.id)
                    if units and not has_exact_source_span:
                        task.what_to_review = (
                            "Generated findings are provisional: exact source document/span evidence is "
                            "required before governed coding can promote them."
                        )
                except Exception as e:
                    logger.debug("EvidenceUnit creation skipped: %s", e)

            _reasoning = nugget_data.get("coding_reasoning", "")
            if _reasoning and isinstance(_enriched_tags, list) and _enriched_tags:
                try:
                    from app.services.research_validity_service import add_agent_initial_code_applications
                    add_agent_initial_code_applications(
                        db,
                        project_id=project_id,
                        task_id=task.id,
                        tags=_enriched_tags,
                        evidence_unit_id=evidence_unit_id,
                        source_document_id=source_document_id,
                        source_text=evidence_source_text,
                        source_location=source_location,
                        start_offset=units[0].start_offset if units else None,
                        end_offset=units[0].end_offset if units else None,
                        agent_id=self.agent_id,
                        confidence=_conf_val,
                        reasoning=_reasoning,
                    )
                except Exception as e:
                    logger.debug("CodeApplication creation skipped: %s", e)

        for fact_data in output.facts:
            fid = str(uuid.uuid4())
            linked_nuggets = await persist_links(db, Nugget, fact_data.get("nugget_ids"), created_nugget_ids[-5:], project_id, task, "fact", fid, "nugget")  # noqa: E501
            fact = Fact(
                id=fid,
                project_id=project_id,
                agent_id=finding_agent_id,
                task_id=task.id,
                text=fact_data.get("text", ""),
                nugget_ids=json.dumps(linked_nuggets),
                phase=fact_phase,
            )
            db.add(fact)
            created_fact_ids.append(fid)

        for insight_data in output.insights:
            iid = str(uuid.uuid4())
            linked_facts = await persist_links(db, Fact, insight_data.get("fact_ids"), created_fact_ids[-3:], project_id, task, "insight", iid, "fact")  # noqa: E501
            insight = Insight(
                id=iid,
                project_id=project_id,
                agent_id=finding_agent_id,
                task_id=task.id,
                text=insight_data.get("text", ""),
                fact_ids=json.dumps(linked_facts),
                phase=insight_phase,
                impact=insight_data.get("impact", "medium"),
            )
            db.add(insight)
            created_insight_ids.append(iid)

        for rec_data in output.recommendations:
            rid = str(uuid.uuid4())
            linked_insights = await persist_links(db, Insight, rec_data.get("insight_ids"), created_insight_ids[-2:], project_id, task, "recommendation", rid, "insight")  # noqa: E501
            rec = Recommendation(
                id=rid,
                project_id=project_id,
                agent_id=finding_agent_id,
                task_id=task.id,
                text=rec_data.get("text", ""),
                insight_ids=json.dumps(linked_insights),
                phase=rec_phase,
                priority=rec_data.get("priority", "medium"),
                effort=rec_data.get("effort", "medium"),
            )
            db.add(rec)
            created_recommendation_ids.append(rid)

        total_visible_findings = (
            len(created_nugget_ids)
            + len(created_fact_ids)
            + len(created_insight_ids)
            + len(created_recommendation_ids)
        )
        if total_visible_findings and not created_evidence_unit_ids:
            from app.services.research_validity_service import mark_task_provisional_skill_artifacts

            mark_task_provisional_skill_artifacts(task)

        await db.commit()
        if created_evidence_unit_ids:
            try:
                from app.services.research_validity_service import run_task_coding_run_and_mark_review
                await run_task_coding_run_and_mark_review(
                    db,
                    task=task,
                    project_id=project_id,
                    evidence_unit_ids=created_evidence_unit_ids,
                    created_by=task.agent_id or self.agent_id,
                )
            except Exception as e:
                logger.debug("Governed coding run skipped: %s", e)

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
                from app.core.artifact_document import render_artifact_document

                readable_artifact = render_artifact_document(
                    filename,
                    content,
                    skill_name=task.skill_name,
                )
                readable_content = readable_artifact["content"]
                chunks = [
                    TextChunk(
                        text=readable_content[:2000],
                        source=f"skill:{task.skill_name}:{readable_artifact['file_name']}",
                    ),
                    TextChunk(
                        text=content[:2000], source=f"skill:{task.skill_name}:{filename}:raw"
                    ),
                ]
                await ingest_chunks(project_id, chunks)
                # Create a Document record so artifacts appear in Documents view
                try:
                    from app.models.document import Document

                    doc = Document(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        title=readable_artifact["title"],
                        description=f"Human-readable skill artifact generated from {filename}.",
                        file_name=readable_artifact["file_name"],
                        file_type=readable_artifact["file_type"],
                        source="agent_output",
                        content_preview=readable_content[:500],
                        content_text=readable_content,
                        status="ready",
                    )
                    doc.set_skill_names([task.skill_name] if task.skill_name else [])
                    doc.set_tags(["generated-artifact", "skill-output"])
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
                "2. Are candidate findings specific and source-grounded (not generic)?\n"
                "3. Is the provisional chain internally linked without claiming acceptance?\n"
                "4. Are there obvious hallucinations or unsupported claims?\n\n"
                "Respond with EXACTLY one JSON object:\n"
                '{"verified": true, "confidence": 0.85, "reason": "one sentence"}'
            )
            # W3 (L5): reflection through the AgenticDispatcher (``spine.verify``)
            # as a proper structured call — the regex-JSON extraction upgrades
            # to a schema BOTH engines enforce (deliberate baseline improvement,
            # master plan §8 W3).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            reflection_schema = {
                "type": "object",
                "properties": {
                    "verified": {"type": "boolean"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["verified", "confidence", "reason"],
                "additionalProperties": False,
            }
            outcome = await agentic.structured(
                purpose="spine.verify",
                project_id=task.project_id,
                system=None,
                messages=[{"role": "user", "content": reflection_prompt}],
                schema=reflection_schema,
                params=TurnParams(temperature=0.1),
                task_id=task.id,
                spine_phase="review",
            )
            if outcome.status == "success" and outcome.value:
                result = outcome.value
                verified = bool(result.get("verified", True))
                reason = str(result.get("reason") or "LLM reflection passed")
                logger.info(
                    "LLM reflection: verified=%s, confidence=%s, reason=%s",
                    verified,
                    result.get("confidence", "?"),
                    reason,
                )
                return verified, reason
            # If no structured object came back, trust heuristic result
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

            task_id = str(uuid.uuid4())
            skill_input = SkillInput(
                project_id=project_id,
                task_id=task_id,
                files=files or [],
                parameters=parameters or {},
                user_context=user_context,
                project_context=project.project_context,
                company_context=project.company_context,
            )

            await broadcast_agent_status("working", f"Running {skill.display_name}...", project_id=project_id)

            try:
                output = await skill.execute(skill_input)

                # Self-verify the output quality (heuristic — no task for manual execution)
                verified, verify_reason = self._self_verify_output_heuristic(output)

                task_status = TaskStatus.IN_REVIEW
                task_notes = (
                    output.summary
                    if verified
                    else f"[Verification failed] {verify_reason}\n\n{output.summary}"
                )

                # Commit the task before persistence fan-out. Report generation,
                # artifact indexing, and finding storage are valuable, but they
                # must not poison the user-facing skill response if SQLite is
                # briefly locked by another agent process.
                task = Task(
                    id=task_id,
                    project_id=project_id,
                    title=f"Manual: {skill.display_name}",
                    skill_name=skill_name,
                    status=task_status,
                    review_state="awaiting_review" if verified else "system_failed",
                    progress=1.0,
                    agent_notes=task_notes,
                )
                db.add(task)
                await db.commit()

                # Store findings in a fresh session. A failed report/artifact
                # transaction then rolls back locally without converting a good
                # LLM result into a failed skill execution.
                try:
                    async with async_session() as store_db:
                        try:
                            stored_task = await store_db.get(Task, task_id)
                            if stored_task is None:
                                raise RuntimeError(f"Manual task was not persisted: {task_id}")
                            await self._store_findings(store_db, project_id, output, stored_task)
                        except Exception:
                            await store_db.rollback()
                            raise
                except Exception as store_err:
                    logger.warning("Failed to store findings for %s: %s", skill_name, store_err)

                learning_signal = learning_signal_for_research_output(
                    execution_success=bool(output.success),
                    verification_success=bool(verified),
                )
                skill_manager.record_execution(
                    skill_name,
                    learning_signal.learning_success,
                    learning_signal.research_quality_score,
                    project_id=project_id,
                )

                if verified:
                    await broadcast_agent_status("idle", f"Completed: {skill.display_name}", project_id=project_id)
                else:
                    await broadcast_agent_status(
                        "warning",
                        f"Needs review: {skill.display_name} — {verify_reason}",
                        project_id=project_id,
                    )

                return output

            except Exception as e:
                logger.exception("Manual skill execution failed")
                await broadcast_agent_status("error", str(e), project_id=project_id)
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
