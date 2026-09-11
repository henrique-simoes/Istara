"""Fail-closed durable idempotency for Pi authority mutations.

This is intentionally narrower than transport retry.  A completed authority
outcome is replayable, while a row left in ``started`` state after a crash is
never executed again automatically: an operator must reconcile that mutation
before a new attempt is allowed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.database import async_session
from app.models.pi_tool_execution import PiToolExecution

logger = logging.getLogger(__name__)

# These tools mutate project state or send an external message. Read-only tools
# remain ordinary calls because replaying a read is not a duplicate side effect.
PI_MUTATING_TOOLS = frozenset(
    {
        "create_task",
        "move_task",
        "update_task",
        "attach_document",
        "assign_agent",
        "send_agent_message",
        "sync_project_documents",
    }
)

ToolExecutor = Callable[[str, dict[str, Any], str, str], Awaitable[dict[str, Any]]]


def _args_hash(args: dict[str, Any]) -> str:
    encoded = json.dumps(args or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def make_idempotency_key(
    base_key: str,
    project_id: str,
    tool_name: str,
    args: dict[str, Any],
) -> tuple[str, str]:
    """Return a secret-free digest key and the canonical argument digest."""
    args_digest = _args_hash(args)
    material = "|".join((str(base_key), str(project_id), tool_name, args_digest))
    return hashlib.sha256(material.encode("utf-8")).hexdigest(), args_digest


def _recovery_required() -> dict[str, Any]:
    return {
        "success": False,
        "error": "tool_recovery_required",
        "recovery": (
            "A prior authority mutation did not settle; reconcile its ledger row before retrying."
        ),
    }


def _decode_outcome(row: PiToolExecution) -> dict[str, Any]:
    if row.status not in {"succeeded", "failed"}:
        return _recovery_required()
    try:
        value = json.loads(row.result_json or "")
    except (TypeError, ValueError):
        logger.error("Pi tool execution outcome is not valid JSON: %s", row.id)
        return _recovery_required()
    return value if isinstance(value, dict) else _recovery_required()


async def _existing_or_started(
    *,
    project_id: str,
    key: str,
    row: PiToolExecution,
) -> dict[str, Any] | None:
    """Insert a started row, or return the concurrent/replayed outcome."""
    async with async_session() as db:
        existing = await db.scalar(
            select(PiToolExecution).where(
                PiToolExecution.project_id == project_id,
                PiToolExecution.idempotency_key == key,
            )
        )
        if existing is not None:
            return _decode_outcome(existing)
        db.add(row)
        try:
            await db.commit()
        except IntegrityError:
            # A concurrent worker won the unique race.  Roll back before the
            # lookup; never invoke the authority when ownership is ambiguous.
            await db.rollback()
            existing = await db.scalar(
                select(PiToolExecution).where(
                    PiToolExecution.project_id == project_id,
                    PiToolExecution.idempotency_key == key,
                )
            )
            return _decode_outcome(existing) if existing is not None else _recovery_required()
    return None


async def _settle(
    row_id: str,
    *,
    status: str,
    outcome: dict[str, Any] | None = None,
    error: str = "",
) -> bool:
    """Persist terminal state; false means the row conservatively stays open."""
    try:
        result_json = json.dumps(outcome or {}, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        status = "started"
        result_json = ""
        error = "tool_result_not_serializable"
    async with async_session() as db:
        row = await db.get(PiToolExecution, row_id)
        if row is None:
            return False
        row.status = status
        row.result_json = result_json
        row.error = error[:2000]
        row.updated_at = datetime.now(UTC)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Unable to settle Pi tool execution %s", row_id)
            return False
    return status in {"succeeded", "failed"}


async def execute_with_idempotency(
    *,
    base_key: str | None,
    project_id: str,
    agent_id: str,
    operation: str,
    session_key: str,
    run_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    executor: ToolExecutor,
) -> dict[str, Any]:
    """Execute one authority call with a durable, project-scoped replay key.

    No base key means the caller has not supplied a retry identity; preserving
    existing seam behavior is safer than pretending an ephemeral key protects
    a cross-process replay. Governed chat supplies the persisted user-message
    id, while channel seams use their stable inbound message key.
    """
    if not base_key or tool_name not in PI_MUTATING_TOOLS:
        return await executor(tool_name, args, project_id, agent_id)

    key, args_digest = make_idempotency_key(base_key, project_id, tool_name, args)
    row = PiToolExecution(
        id=str(uuid.uuid4()),
        project_id=project_id,
        idempotency_key=key,
        tool_name=tool_name,
        args_hash=args_digest,
        operation=operation,
        worker_session_key=session_key[:255],
        run_id=run_id[:100],
        tool_call_id=tool_call_id[:160],
        status="started",
        result_json="",
        error="",
        attempt_count=1,
    )
    replay = await _existing_or_started(project_id=project_id, key=key, row=row)
    if replay is not None:
        return replay

    try:
        outcome = await executor(tool_name, args, project_id, agent_id)
    except asyncio.CancelledError:
        # Leave ``started`` as the durable recovery signal; cancellation must
        # never turn an unknown side-effect into an automatic retry.
        raise
    except Exception as exc:  # authority wrappers normally return errors, but be defensive
        outcome = {"success": False, "error": str(exc)}
        settled = await _settle(row.id, status="failed", outcome=outcome, error=str(exc))
        return outcome if settled else _recovery_required()

    if not isinstance(outcome, dict):
        outcome = {"success": True, "result": outcome}
    settled = await _settle(
        row.id,
        status="succeeded" if outcome.get("success", True) else "failed",
        outcome=outcome,
        error=str(outcome.get("error") or ""),
    )
    # If the mutation ran but its terminal state could not be persisted, return
    # an explicit failure and keep the started row as a recovery barrier.
    return outcome if settled else _recovery_required()
