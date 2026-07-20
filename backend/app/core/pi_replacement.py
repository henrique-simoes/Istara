"""Pi replacement candidate hooks for production Istara contracts.

The candidate is deliberately opt-in. It reuses Istara's existing routing,
tool, A2A, channel, research-spine, and telemetry surfaces instead of adding a
parallel app path.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID, PiEndpointResolutionError, PiEndpointResolver
from app.core.telemetry import telemetry_recorder
from app.core.token_counter import count_tokens

logger = logging.getLogger(__name__)

PI_ENGINE_VALUES = {"pi", "pi-candidate", "pi-replacement", "deepseek-pi"}


def _request_header_value(request: Request | None) -> str:
    if request is None:
        return ""
    header_name = settings.pi_replacement_request_header.strip() or "x-istara-agent-engine"
    return (request.headers.get(header_name) or "").strip().lower()


def pi_replacement_requested(
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Return True when the reversible Pi candidate path is explicitly selected."""
    if settings.pi_replacement_enabled:
        return True
    if _request_header_value(request) in PI_ENGINE_VALUES:
        return True
    meta = metadata or {}
    value = meta.get("pi_replacement") or meta.get("pi_candidate") or meta.get("engine")
    return str(value or "").strip().lower() in {"true", "1", *PI_ENGINE_VALUES}


def ensure_pi_deepseek_registered() -> tuple[bool, str]:
    """Validate the default Pi endpoint without touching donated compute.

    Kept under its historical name temporarily for fail-closed route callers.
    It no longer registers an ``LLMServerEntry`` or makes a Pi endpoint
    discoverable by ordinary model-alias routing.
    """
    try:
        PiEndpointResolver().resolve(DEFAULT_ENDPOINT_ID)
    except PiEndpointResolutionError as exc:
        return False, str(exc)
    return True, "resolved_private_endpoint"


def pi_chat_model(default_model: str | None = None) -> str | None:
    """Resolve the model used by a selected Pi chat path."""
    return settings.pi_replacement_deepseek_model or default_model


async def record_pi_span(
    *,
    operation: str,
    project_id: str,
    agent_id: str = "istara-main",
    status: str = "success",
    duration_ms: float = 0.0,
    tool_name: str | None = None,
    tool_success: bool | None = None,
    error_message: str | None = None,
    event_kind: str = "pi_replacement_candidate",
    route_id: str = "pi-deepseek-candidate",
) -> None:
    await telemetry_recorder.record_span(
        trace_id=f"pi-{uuid.uuid4().hex}",
        operation=operation,
        model_name=settings.pi_replacement_deepseek_model,
        agent_id=agent_id,
        project_id=project_id,
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
        event_kind=event_kind,
        route_id=route_id,
        tool_name=tool_name,
        tool_success=tool_success,
        source="pi-replacement-candidate",
    )


async def record_pi_a2a_event(
    *,
    request: Request | None,
    project_id: str,
    metadata: dict[str, Any] | None,
    message_id: str,
    from_agent_id: str,
    to_agent_id: str,
) -> None:
    if not pi_replacement_requested(request, metadata):
        return
    await record_pi_span(
        operation="pi_candidate_a2a_tasks_send",
        project_id=project_id,
        agent_id=from_agent_id or "external",
        event_kind="a2a_jsonrpc",
        route_id=f"{from_agent_id or 'external'}->{to_agent_id or 'istara-main'}:{message_id}",
    )


async def build_pi_channel_response(
    *,
    message_channel: str,
    channel_id: str,
    instance_id: str,
    project_id: str,
    inbound_message_id: str,
    metadata: dict[str, Any] | None,
) -> Any | None:
    """Return a local candidate channel response only when Pi mode is selected."""
    if not pi_replacement_requested(metadata=metadata):
        return None
    from app.channels.base import OutgoingMessage

    await record_pi_span(
        operation="pi_candidate_channel_inbound",
        project_id=project_id,
        agent_id="channel-router",
        event_kind="credential_free_channel_adapter",
        route_id=f"{instance_id}:{inbound_message_id}",
    )
    return OutgoingMessage(
        channel=message_channel,
        channel_id=channel_id,
        text="Pi candidate recorded the inbound channel message for local benchmark routing.",
        instance_id=instance_id,
        metadata={
            "pi_replacement": True,
            "inbound_message_id": inbound_message_id,
        },
    )


class PiChatRunMetrics:
    """Small accumulator for candidate chat/tool-loop metrics."""

    def __init__(self, *, project_id: str, agent_id: str | None) -> None:
        self.project_id = project_id
        self.agent_id = agent_id or "istara-main"
        self.started = time.perf_counter()
        self.chunk_count = 0
        self.tool_call_count = 0
        self.output_chars = 0
        self.output_tokens = 0
        self.input_tokens = 0
        self.registration_status = ""

    def observe_input(self, messages: list[dict]) -> None:
        content = "\n".join(str(m.get("content") or "") for m in messages)
        self.input_tokens = count_tokens(content)

    def observe_chunk(self, chunk: str) -> None:
        self.chunk_count += 1
        self.output_chars += len(chunk)
        self.output_tokens += count_tokens(chunk)

    def observe_tool_call(self) -> None:
        self.tool_call_count += 1

    async def finish(self, *, status: str = "success", error_message: str | None = None) -> None:
        await record_pi_span(
            operation="pi_candidate_chat_sse_tool_loop",
            project_id=self.project_id,
            agent_id=self.agent_id,
            status=status,
            duration_ms=(time.perf_counter() - self.started) * 1000,
            error_message=error_message,
            route_id=json.dumps(
                {
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens,
                    "chunks": self.chunk_count,
                    "tool_calls": self.tool_call_count,
                    "registration": self.registration_status,
                },
                sort_keys=True,
            ),
        )


async def write_pi_source_evidence_chain(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    agent_id: str = "istara-main",
) -> dict[str, Any]:
    """Write a credential-free Pi source/evidence chain through real tables."""
    from app.models.document import Document, DocumentSource, DocumentStatus
    from app.models.finding import Nugget
    from app.services.research_validity_service import persist_task_nugget_evidence_units

    source_text = (
        "Pi production-readiness benchmark source unit. The candidate must keep "
        "the original Istara evidence chain intact before any finding can enter reports."
    )
    document = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="Pi production-readiness source",
        description="Credential-free Pi replacement production-test evidence document.",
        file_name="pi-production-readiness.md",
        file_type="md",
        status=DocumentStatus.READY,
        source=DocumentSource.TASK_OUTPUT,
        task_id=task_id,
        phase="develop",
        content_preview=source_text,
        content_text=source_text,
    )
    document.set_agent_ids([agent_id])
    document.set_skill_names(["pi-replacement-benchmark"])
    document.set_tags(["pi-replacement", "production-readiness"])
    db.add(document)

    nugget = Nugget(
        id=str(uuid.uuid4()),
        project_id=project_id,
        agent_id=agent_id,
        task_id=task_id,
        text="Pi candidate preserved a source-grounded production evidence chain.",
        source=document.id,
        source_location="pi-production-readiness.md#unit-1",
        tags=json.dumps(["pi-replacement", "production-readiness"]),
        phase="develop",
        confidence=0.92,
    )
    db.add(nugget)
    await db.flush()

    evidence_units = await persist_task_nugget_evidence_units(
        db,
        project_id=project_id,
        task_id=task_id,
        nugget_id=nugget.id,
        source_text=source_text,
        source_location="pi-production-readiness.md#unit-1",
        source_document_id=document.id,
        method="pi_replacement_production_test",
        phase="develop",
        candidate_only=True,
    )

    await record_pi_span(
        operation="pi_candidate_source_evidence_chain",
        project_id=project_id,
        agent_id=agent_id,
        event_kind="research_spine",
        route_id=json.dumps(
            {
                "task_id": task_id,
                "document_id": document.id,
                "evidence_units": len(evidence_units),
                "governance": "unavailable_without_independent_coding",
            },
            sort_keys=True,
        ),
    )
    return {
        "document_id": document.id,
        "nugget_id": nugget.id,
        "evidence_unit_ids": [unit.id for unit in evidence_units],
        "governance_source": "computed",
        "governance_available": False,
        "reason": "credential_free probe has no independent multi-model coding/reconciliation",
    }


async def exercise_pi_done_report_gate(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    reviewed_by: str = "pi-production-test",
) -> dict[str, Any]:
    """Exercise the real review/report gate without manufacturing acceptance."""
    from app.models.task import Task, TaskStatus

    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise ValueError("Task not found in requested project")
    task.status = TaskStatus.IN_REVIEW
    task.review_state = "in_review"

    evidence = await write_pi_source_evidence_chain(
        db,
        project_id=project_id,
        task_id=task.id,
        agent_id=task.agent_id or "istara-main",
    )
    await db.commit()
    await record_pi_span(
        operation="pi_candidate_done_report_gate",
        project_id=project_id,
        agent_id=task.agent_id or "istara-main",
        event_kind="task_review_report_gate",
        route_id=json.dumps(
            {
                "task_id": task.id,
                "review_event_id": None,
                "report_finding_count": 0,
            },
            sort_keys=True,
        ),
    )
    return {
        "task_id": task.id,
        "review_event_id": None,
        "report_finding_count": 0,
        **evidence,
    }


async def record_pi_memory_governance_fanout(
    db: AsyncSession,
    *,
    project_id: str,
    task_id: str,
    agent_id: str = "istara-main",
    skill_name: str = "pi-replacement-benchmark",
) -> dict[str, Any]:
    """Exercise scoped process memory without promoting a raw probe result."""
    from app.core.reasoning_bank import reasoning_bank
    from app.models.model_skill_stats import ModelSkillStats

    memory = await reasoning_bank.record_memory(
        project_id=project_id,
        agent_id=agent_id,
        source_kind="skill",
        source_id=task_id,
        outcome="observed",
        title="Pi replacement production-readiness memory",
        description="Credential-free readiness path wrote a real ReasoningBank item.",
        content="Pi candidate preserved task, source, evidence, telemetry, and report gates.",
        tags=["pi-replacement", "production-readiness", "memento"],
        domain=skill_name,
        evidence_refs=[{"task_id": task_id, "engine": "pi"}],
        judge_score=None,
        confidence=0.0,
        db=db,
    )
    await db.flush()
    await record_pi_span(
        operation="pi_candidate_memory_governance_fanout",
        project_id=project_id,
        agent_id=agent_id,
        event_kind="memory_rag_skill_stats",
        route_id=json.dumps({"task_id": task_id, "memory_id": memory.id}, sort_keys=True),
    )
    return {"memory_id": memory.id, "model_skill_stats_id": None, "promotion": "not_attempted"}


async def exercise_pi_steering_interrupt_probe(
    *,
    agent_id: str,
    project_id: str,
) -> dict[str, Any]:
    """Prove the Pi test path can interrupt an active agent steering queue."""
    from app.core.steering import steering_manager

    await steering_manager.mark_working(agent_id, project_id=project_id)
    await steering_manager.steer(
        agent_id,
        "Pause current Pi benchmark action and preserve state.",
        source="pi-production-test",
        metadata={"pi_candidate": True},
        project_id=project_id,
    )
    before = steering_manager.get_status(agent_id, project_id=project_id)
    cleared = await steering_manager.abort(agent_id, project_id=project_id)
    after = steering_manager.get_status(agent_id, project_id=project_id)
    await record_pi_span(
        operation="pi_candidate_steering_interrupt",
        project_id=project_id,
        agent_id=agent_id,
        event_kind="steering_interrupt",
        route_id=json.dumps(
            {
                "before": before,
                "after": after,
                "cleared_steering": len(cleared["steering"]),
                "cleared_follow_up": len(cleared["follow_up"]),
            },
            sort_keys=True,
        ),
    )
    return {
        "before": before,
        "after": after,
        "cleared_steering_count": len(cleared["steering"]),
        "cleared_follow_up_count": len(cleared["follow_up"]),
    }


async def exercise_pi_production_readiness(
    db: AsyncSession,
    *,
    project_id: str,
    agent_id: str = "istara-main",
) -> dict[str, Any]:
    """Run credential-free production-contract probes for benchmark readiness."""
    from app.models.task import Task, TaskStatus
    from app.services.research_validity_service import build_evidence_graph_traceability

    task = Task(
        id=str(uuid.uuid4()),
        project_id=project_id,
        agent_id=agent_id,
        title="Pi replacement production-readiness benchmark",
        description="Synthetic credential-free task that exercises real Istara production contracts.",
        status=TaskStatus.IN_REVIEW,
        skill_name="pi-replacement-benchmark",
        review_state="in_review",
        consensus_score=0.93,
    )
    db.add(task)
    await db.flush()
    report_gate = await exercise_pi_done_report_gate(
        db,
        project_id=project_id,
        task_id=task.id,
        reviewed_by="pi-production-test",
    )
    memory = await record_pi_memory_governance_fanout(
        db,
        project_id=project_id,
        task_id=task.id,
        agent_id=agent_id,
        skill_name=task.skill_name,
    )
    steering = await exercise_pi_steering_interrupt_probe(
        agent_id=agent_id,
        project_id=project_id,
    )
    await db.commit()
    trace = await build_evidence_graph_traceability(
        db,
        project_id=project_id,
        task_id=task.id,
    )
    await db.commit()
    return {
        "task_id": task.id,
        "done_report_gate": report_gate,
        "memory_governance": memory,
        "steering_interrupt": steering,
        "autoresearch_memory_ids": [],
        "traceability_summary": trace["summary"],
        "production_test_ready": False,
        "production_mutation_allowed": False,
    }
