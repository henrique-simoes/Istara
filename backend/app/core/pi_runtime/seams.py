"""Glue between Istara routes/services and the ``PiExecutionService`` seams.

Every helper here:

* gates on *explicit* Pi selection (never runs when Pi is off/unselected),
* keeps Istara authorization/governance above the seam — the model never sets
  project/agent scope or promotes anything,
* executes tool calls through the real canonical ``execute_tool`` authority, and
* **fails closed**: on a resolver/Keychain miss or any worker failure it returns
  ``None`` / a typed marker rather than silently falling back to another
  transport or a canned response.

This module is the only place the governed A2A / ``pi_local`` / Autoresearch
seams reach the runtime, so no route reinvents runtime semantics (Plan C D-C5).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.pi_replacement import pi_replacement_requested
from app.core.pi_runtime.endpoints import PiEndpointResolutionError
from app.core.pi_runtime.engine import PiExecutionService
from app.skills.system_actions import execute_tool

logger = logging.getLogger(__name__)

_GOVERNANCE_CLAUSE = (
    "You run inside Istara. Pi owns the loop; Istara owns product state, "
    "authorization, and research governance. You may only create source, "
    "candidate, or provisional artifacts. You cannot accept, reconcile, mark "
    "Done, report, or promote anything — those transitions require Istara's "
    "governance services and human review."
)

CHANNEL_SYSTEM_PROMPT = (
    "You are the Istara project assistant answering an inbound channel message. "
    + _GOVERNANCE_CLAUSE
    + " Reply concisely to the participant using only project-scoped tools."
)
DELEGATION_SYSTEM_PROMPT = (
    "You are an Istara agent executing a task delegated to you over A2A. "
    + _GOVERNANCE_CLAUSE
    + " Work the delegated task with project-scoped tools and stop when done."
)
AUTORESEARCH_SYSTEM_PROMPT = (
    "You are proposing a governed Istara autoresearch experiment. "
    + _GOVERNANCE_CLAUSE
    + " Inspect the project read-only and return one hypothesis as text; you may "
    "not mutate any state or start any loop."
)


_service: PiExecutionService | None = None


def get_pi_execution_service() -> PiExecutionService:
    global _service
    if _service is None:
        _service = PiExecutionService()
    return _service


def set_pi_execution_service(service: PiExecutionService | None) -> None:
    """Test seam: inject a service bound to a scripted supervisor/resolver."""
    global _service
    _service = service


async def _authority_tool_executor(
    name: str, params: dict[str, Any], project_id: str, agent_id: str
) -> dict[str, Any]:
    # The authenticated project/agent scope is fixed by the caller; the model
    # cannot alter it. Every call re-validates through canonical Istara authority.
    return await execute_tool(name, params, project_id, agent_id=agent_id)


async def build_pi_channel_reply(
    *,
    message_channel: str,
    channel_id: str,
    instance_id: str,
    project_id: str,
    inbound_message_id: str,
    inbound_text: str,
    metadata: dict[str, Any] | None,
    agent_id: str = "channel-router",
):
    """Return a real ``pi_local`` reply (OutgoingMessage) or ``None``.

    Replaces the old canned ``build_pi_channel_response``: when Pi is selected
    the inbound text drives a real in-process Pi turn; a resolver/worker failure
    fails closed to ``None`` (no auto-reply), never a canned string.
    """
    if not pi_replacement_requested(metadata=metadata):
        return None
    from app.channels.base import OutgoingMessage

    service = get_pi_execution_service()
    session_key = f"pi-channel:{instance_id}:{inbound_message_id}"
    try:
        result = await service.run_channel_turn(
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=CHANNEL_SYSTEM_PROMPT,
            inbound_text=inbound_text or "",
            tool_executor=_authority_tool_executor,
            session_key=session_key,
            idempotency_key=session_key,
        )
    except PiEndpointResolutionError as exc:
        logger.warning("Pi channel turn unavailable (fail-closed): %s", exc)
        return None
    except Exception:  # pragma: no cover - defensive; never crash channel routing
        logger.warning("Pi channel turn failed (fail-closed)", exc_info=True)
        return None

    # Reject a non-success terminal before sending: a turn that errored or was
    # aborted must not produce a reply, even if it streamed partial text (RF3-2).
    if (result or {}).get("status") != "success":
        logger.warning(
            "Pi channel turn non-success (fail-closed): %s", (result or {}).get("status")
        )
        return None
    text = (result or {}).get("text") or ""
    if not text.strip():
        return None
    return OutgoingMessage(
        channel=message_channel,
        channel_id=channel_id,
        text=text,
        instance_id=instance_id,
        metadata={
            "pi_replacement": True,
            "engine": "pi",
            "inbound_message_id": inbound_message_id,
            "endpoint_id": result.get("endpoint_id"),
        },
    )


async def run_pi_delegation(
    *,
    project_id: str,
    task_text: str,
    agent_id: str,
    metadata: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    """Execute an admitted A2A delegation through the real Pi Agent, or ``None``.

    Only runs when the delegation carries explicit Pi selection. Gate chain,
    project scope, persistence, and audit run above this in the A2A route /
    orchestrator dispatch and are unchanged; on failure this fails closed.
    """
    if not pi_replacement_requested(metadata=metadata):
        return None
    service = get_pi_execution_service()
    try:
        result = await service.run_delegation(
            project_id=project_id,
            agent_id=agent_id or "istara-main",
            system_prompt=DELEGATION_SYSTEM_PROMPT,
            task_text=task_text or "",
            tool_executor=_authority_tool_executor,
            history=history or [],
            idempotency_key=(
                idempotency_key
                or str(
                    (metadata or {}).get("message_id")
                    or (metadata or {}).get("idempotency_key")
                    or ""
                )
                or None
            ),
        )
    except PiEndpointResolutionError as exc:
        logger.warning("Pi delegation unavailable (fail-closed): %s", exc)
        return None
    except Exception:  # pragma: no cover - defensive
        logger.warning("Pi delegation failed (fail-closed)", exc_info=True)
        return None
    # Reject a non-success terminal before the caller persists/sends a reply: a
    # turn that errored or was aborted must not surface partial text (RF3-2).
    if (result or {}).get("status") != "success":
        logger.warning("Pi delegation non-success (fail-closed): %s", (result or {}).get("status"))
        return None
    return result


async def run_pi_governed_autoresearch(
    *,
    project_id: str,
    loop_type: str,
    target: str,
    agent_id: str = "autoresearch",
) -> dict[str, Any]:
    """Run one governed Autoresearch turn → candidate proposal (never mutates).

    Fails closed with a typed error so the route never returns a silent success:
    ``PiEndpointResolutionError`` when the endpoint is unavailable, and
    ``PiRuntimeTurnError`` when the turn reaches a non-success terminal
    (``error``/``aborted``) — a failed turn yields no candidate proposal (RF3-2).
    """
    service = get_pi_execution_service()
    objective = (
        f"Propose one governed autoresearch experiment for loop '{loop_type}' "
        f"targeting '{target}'. Inspect the project read-only and return a single "
        "hypothesis. Do not mutate any state."
    )
    return await service.run_autoresearch_turn(
        project_id=project_id,
        agent_id=agent_id,
        system_prompt=AUTORESEARCH_SYSTEM_PROMPT,
        objective=objective,
        tool_executor=_authority_tool_executor,
        loop_type=loop_type,
        target=target,
    )
