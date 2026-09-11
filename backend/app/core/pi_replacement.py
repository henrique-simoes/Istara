"""Pi replacement candidate hooks for production Istara contracts.

The candidate is deliberately opt-in. It reuses Istara's existing routing,
tool, A2A, channel, research-spine, and telemetry surfaces instead of adding a
parallel app path.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import Request

from app.config import settings
from app.core.pi_runtime.endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolutionError,
    PiEndpointResolver,
)
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
            # Route identity must stay a bounded, joinable identifier. Token,
            # turn, and tool accounting belongs to the dispatcher usage ledger;
            # packing ad-hoc metrics JSON here overflowed varchar(120) in live
            # Postgres and discarded the candidate span.
            route_id="pi-deepseek-candidate",
        )
