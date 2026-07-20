"""Content-free route evidence helpers for compute orchestration."""

from __future__ import annotations

import asyncio
import importlib
import uuid
from typing import Any


_telemetry_tasks: set[asyncio.Task[None]] = set()


def route_evidence_payload(
    node: Any,
    *,
    route_kind: str,
    project_id: str | None,
    model: str | None,
    outcome: str = "served",
) -> dict:
    """Return route evidence without hosts, tokens, prompts, or response text."""
    return {
        "node_id": getattr(node, "node_id", ""),
        "node_source": getattr(node, "source", ""),
        "provider_type": getattr(node, "provider_type", ""),
        "route_kind": route_kind,
        "project_id": project_id or "",
        "model": model or "",
        "outcome": outcome,
        "selected_request_count": getattr(node, "selected_request_count", 0),
        "served_request_count": getattr(node, "served_request_count", 0),
        "failed_request_count": getattr(node, "failed_request_count", 0),
    }


def attach_route_evidence(
    data: dict,
    node: Any,
    *,
    route_kind: str,
    project_id: str | None,
    model: str | None,
) -> dict:
    """Attach content-free route evidence to a provider response."""
    data["_istara_route"] = route_evidence_payload(
        node,
        route_kind=route_kind,
        project_id=project_id,
        model=model,
    )
    return data


def schedule_compute_telemetry_event(
    node: Any,
    *,
    operation: str,
    project_id: str | None,
    route_kind: str = "",
    model: str | None = None,
    status: str = "success",
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    """Schedule content-free donor lifecycle telemetry from sync routing code."""
    scoped_project_id = str(project_id or "").strip()
    if not scoped_project_id or scoped_project_id == "*":
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    donor_id = str(getattr(node, "node_id", "") or getattr(node, "name", "") or "")
    counter = (
        getattr(node, "served_request_count", 0)
        if operation == "donor.served"
        else getattr(node, "failed_request_count", 0)
        if operation == "donor.failed"
        else getattr(node, "selected_request_count", 0)
    )
    route_id = f"{donor_id}:{route_kind or operation}:{counter}"

    async def _emit() -> None:
        try:
            telemetry_module = importlib.import_module("app.core.telemetry")
            telemetry_recorder = telemetry_module.telemetry_recorder

            await telemetry_recorder.record_research_validity_event(
                trace_id=uuid.uuid4().hex[:36],
                operation=operation,
                project_id=scoped_project_id,
                status=status,
                model_name=model or str(getattr(node, "last_selected_model", "") or ""),
                route_id=route_id,
                donor_id=donor_id,
                error_type=error_type,
                error_message=error_message,
                source="production",
            )
        except Exception:
            return

    task = loop.create_task(_emit())
    _telemetry_tasks.add(task)
    task.add_done_callback(_telemetry_tasks.discard)


async def drain_compute_telemetry() -> None:
    """Await owned compute telemetry before a DB engine/event loop is disposed.

    Routing remains synchronous, but its optional telemetry no longer outlives
    the test or application lifecycle that scheduled it.
    """
    while _telemetry_tasks:
        pending = tuple(_telemetry_tasks)
        await asyncio.gather(*pending, return_exceptions=True)
