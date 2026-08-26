"""WebSocket endpoint for real-time agent status updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

PROJECT_BOUND_EVENT_TYPES = frozenset(
    {
        "agent_created",
        "agent_created_from_proposal",
        "a2a_message",
        "agent_status",
        "agent_thinking",
        "agent_idle",
        "channel_message",
        "channel_status",
        "deployment_finding",
        "deployment_progress",
        "deployment_response",
        "document_created",
        "document_deleted",
        "document_updated",
        "file_processed",
        "finding_created",
        "meta_proposal",
        "plan_progress",
        "steering_message",
        "suggestion",
        "task_progress",
        "task_queue_update",
        "autoresearch_complete",
        "autoresearch_progress",
    }
)

GLOBAL_ADMIN_ONLY_EVENT_TYPES = frozenset(
    {
        "backup_completed",
        "backup_failed",
        "backup_started",
        "resource_throttle",
        "update_available",
        "update_failed",
        "update_started",
    }
)


def _clean_project_id(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


async def _can_subscribe_to_project(db: Any, user_context: dict, project_id: str | None) -> bool:
    """Return whether a websocket client may subscribe to a project stream."""
    from app.config import settings

    if not settings.team_mode:
        return True

    user_id = str(user_context.get("id") or "")
    role = str(user_context.get("role") or "")
    if user_id:
        try:
            from app.models.user import User

            user = await db.get(User, user_id)
            if user:
                role = str(getattr(user.role, "value", user.role))
        except Exception:
            pass

    if not project_id:
        return role == "admin"
    if role == "admin":
        return True

    from app.core.permissions import get_project_role, project_role_rank

    project_role = await get_project_role(db, project_id, user_id)
    if project_role is None:
        return False
    return project_role_rank(project_role) >= project_role_rank("viewer")


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[dict[str, Any]] = []
        self._notification_tasks: set[asyncio.Task[None]] = set()

    def _track_notification_task(self, task: asyncio.Task[None]) -> None:
        """Keep fire-and-forget persistence attached to the app lifecycle."""
        self._notification_tasks.add(task)
        task.add_done_callback(self._notification_tasks.discard)

    async def drain_notification_tasks(self) -> None:
        """Wait for notification writes before a loop or app shuts down."""
        pending = tuple(self._notification_tasks)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_context: dict,
        active_project_id: str | None = None,
    ) -> None:
        await websocket.accept()
        self._connections.append(
            {
                "websocket": websocket,
                "user_context": user_context,
                "active_project_id": active_project_id,
            }
        )
        logger.info(f"WebSocket connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections = [
            record for record in self._connections if record.get("websocket") is not websocket
        ]
        logger.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    @staticmethod
    def _project_id_from_data(data: dict) -> str | None:
        value = data.get("project_id") or data.get("projectId")
        if isinstance(value, str) and value.strip():
            return value.strip()
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get("project_id") or metadata.get("projectId")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _explicit_project_claims(data: dict) -> list[tuple[str, str]]:
        claims: list[tuple[str, str]] = []
        for key in ("project_id", "projectId"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                claims.append((key, value.strip()))
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            for key in ("project_id", "projectId"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    claims.append((f"metadata.{key}", value.strip()))
        return claims

    @staticmethod
    def _data_or_metadata_text(data: dict, *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            for key in keys:
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _has_reference_claims(data: dict) -> bool:
        reference_keys = (
            "task_id",
            "taskId",
            "deployment_id",
            "deploymentId",
            "instance_id",
            "instanceId",
            "agent_id",
            "agentId",
            "from_agent_id",
            "fromAgentId",
            "to_agent_id",
            "toAgentId",
        )
        if any(isinstance(data.get(key), str) and data[key].strip() for key in reference_keys):
            return True
        metadata = data.get("metadata")
        return isinstance(metadata, dict) and any(
            isinstance(metadata.get(key), str) and metadata[key].strip()
            for key in reference_keys
        )

    @staticmethod
    def _consistent_project_claim(
        claims: list[tuple[str, str]],
        event_type: str = "event",
    ) -> str | None:
        unique_project_ids = {project_id for _source, project_id in claims}
        if len(unique_project_ids) == 1:
            return next(iter(unique_project_ids))
        if len(unique_project_ids) > 1:
            logger.warning(
                "Dropping %s websocket event with conflicting project claims.",
                event_type,
            )
        return None

    async def _resolve_project_id(self, data: dict) -> str | None:
        claims = self._explicit_project_claims(data)
        if not self._has_reference_claims(data):
            return self._consistent_project_claim(claims, "project-bound")

        try:
            from app.models.database import async_session

            async with async_session() as db:
                task_id = self._data_or_metadata_text(data, "task_id", "taskId")
                if isinstance(task_id, str) and task_id:
                    from app.models.task import Task

                    task = await db.get(Task, task_id)
                    if task and task.project_id:
                        claims.append(("task", str(task.project_id)))

                deployment_id = self._data_or_metadata_text(data, "deployment_id", "deploymentId")
                if isinstance(deployment_id, str) and deployment_id:
                    from app.models.research_deployment import ResearchDeployment

                    deployment = await db.get(ResearchDeployment, deployment_id)
                    if deployment and deployment.project_id:
                        claims.append(("deployment", str(deployment.project_id)))

                instance_id = self._data_or_metadata_text(data, "instance_id", "instanceId")
                if isinstance(instance_id, str) and instance_id:
                    from app.models.channel_instance import ChannelInstance

                    instance = await db.get(ChannelInstance, instance_id)
                    if instance and instance.project_id:
                        claims.append(("channel_instance", str(instance.project_id)))

                from app.models.agent import Agent

                for agent_key in (
                    "agent_id",
                    "agentId",
                    "from_agent_id",
                    "fromAgentId",
                    "to_agent_id",
                    "toAgentId",
                ):
                    agent_id = data.get(agent_key)
                    if not isinstance(agent_id, str) or not agent_id:
                        continue
                    agent = await db.get(Agent, agent_id)
                    agent_project_id = _clean_project_id(agent.project_id if agent else None)
                    if agent and agent.scope == "project" and agent_project_id:
                        claims.append((agent_key, agent_project_id))
        except Exception:
            return None
        return self._consistent_project_claim(claims, "project-bound")

    @staticmethod
    async def _connection_can_receive(
        db: Any,
        record: dict[str, Any],
        project_id: str | None,
    ) -> bool:
        if not project_id:
            return True
        if record.get("active_project_id") != project_id:
            return False
        return await _can_subscribe_to_project(db, record.get("user_context") or {}, project_id)

    @staticmethod
    async def _connection_can_receive_global_admin_event(
        db: Any,
        record: dict[str, Any],
    ) -> bool:
        return await _can_subscribe_to_project(db, record.get("user_context") or {}, None)

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast an event to connected clients authorized for its project."""
        project_id = await self._resolve_project_id(data)
        if project_id and not self._project_id_from_data(data):
            data = {**data, "project_id": project_id}
        elif not project_id and event_type in PROJECT_BOUND_EVENT_TYPES:
            logger.warning(
                "Dropping project-bound websocket event without resolvable project_id: %s",
                event_type,
            )
            return
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        disconnected = []
        if project_id:
            from app.models.database import async_session

            async with async_session() as db:
                for record in list(self._connections):
                    if not await self._connection_can_receive(db, record, project_id):
                        continue
                    connection = record["websocket"]
                    try:
                        await connection.send_text(message)
                    except Exception:
                        disconnected.append(connection)
        elif event_type in GLOBAL_ADMIN_ONLY_EVENT_TYPES:
            from app.models.database import async_session

            async with async_session() as db:
                for record in list(self._connections):
                    if not await self._connection_can_receive_global_admin_event(db, record):
                        continue
                    connection = record["websocket"]
                    try:
                        await connection.send_text(message)
                    except Exception:
                        disconnected.append(connection)
        else:
            for record in list(self._connections):
                connection = record["websocket"]
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

        # Persist notification asynchronously — never block broadcasts. Keep a
        # reference so shutdown/tests can drain the task before closing the DB
        # event loop (otherwise AsyncSession.close may be left unawaited).
        self._track_notification_task(
            asyncio.create_task(self._persist_notification(event_type, data))
        )

    async def _persist_notification(self, event_type: str, data: dict) -> None:
        """Persist a notification record from a broadcast event."""
        try:
            from app.services.notification_service import persist_notification
            await persist_notification(event_type, data)
        except Exception:
            pass  # Never block broadcasts

    async def send_to(self, websocket: WebSocket, event_type: str, data: dict) -> None:
        """Send an event to a specific client."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await websocket.send_text(message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Authentication: JWT required via ?token= query parameter.
    WebSocket connections from browsers cannot send custom headers,
    so the token is passed as a query parameter.

    Events broadcast to clients:
    - agent_status: Agent activity updates (working, idle, etc.)
    - task_progress: Task progress updates (task_id, progress, notes)
    - file_processed: A file was processed and indexed
    - finding_created: New research findings stored (nuggets, insights, recommendations)
    - suggestion: Agent has a suggestion for the user
    - resource_throttle: Agent paused due to hardware constraints
    - task_queue_update: Task queue depth changed (pending, in_progress, completed)
    - document_created: New document registered
    - document_updated: Existing document modified
    - deployment_response: Participant responded to a deployment question
    - deployment_finding: New finding extracted from a deployment response
    - deployment_progress: Deployment analytics/progress update
    """
    # Authenticate BEFORE accepting the connection — unauthenticated clients
    # must never receive broadcast messages, even briefly.
    token = websocket.query_params.get("token", "")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if token:
        from app.core.auth import verify_token
        from app.core.auth_sessions import current_user_context_for_payload, validate_auth_session
        from app.models.database import async_session

        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        async with async_session() as db:
            if not await validate_auth_session(db, payload):
                await websocket.close(
                    code=4001,
                    reason="Invalid or revoked authentication session",
                )
                return
            user_context = await current_user_context_for_payload(db, payload)
            if not user_context:
                await websocket.close(code=4001, reason="Authenticated user no longer exists")
                return
            active_project_id = _clean_project_id(websocket.query_params.get("project_id"))
            if not await _can_subscribe_to_project(db, user_context, active_project_id):
                await websocket.close(code=4003, reason="Project access denied")
                return
    else:
        await websocket.close(code=4001, reason="Authentication required. Pass ?token=<jwt>")
        return

    # Token is valid — now accept and register the connection
    await manager.connect(
        websocket,
        user_context=user_context,
        active_project_id=active_project_id,
    )

    try:
        # Send initial status
        await manager.send_to(websocket, "connected", {
            "message": "Connected to Istara real-time updates.",
        })

        # Keep connection alive, handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong for keepalive
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_to(websocket, "pong", {})
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await manager.send_to(websocket, "ping", {})
                except Exception:
                    break

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper functions for broadcasting events from other modules

async def broadcast_agent_status(status: str, details: str = "", project_id: str | None = None) -> None:
    """Broadcast agent status update."""
    data = {"status": status, "details": details}
    if project_id:
        data["project_id"] = project_id
    await manager.broadcast("agent_status", data)


async def broadcast_task_progress(task_id: str, progress: float, notes: str = "") -> None:
    """Broadcast task progress update."""
    await manager.broadcast("task_progress", {
        "task_id": task_id,
        "progress": progress,
        "notes": notes,
    })


async def broadcast_agent_thinking(agent_id: str, step: int, thought: str, total_steps: int = 0) -> None:
    """Broadcast agent thinking/reasoning progress for real-time UI updates."""
    await manager.broadcast("agent_thinking", {
        "agent_id": agent_id,
        "step": step,
        "total_steps": total_steps,
        "thought": thought,
    })


async def broadcast_plan_progress(task_id: str, plan_step: int, total_steps: int, step_desc: str, step_status: str) -> None:
    """Broadcast research plan step execution progress."""
    await manager.broadcast("plan_progress", {
        "task_id": task_id,
        "plan_step": plan_step,
        "total_steps": total_steps,
        "step_description": step_desc,
        "step_status": step_status,
    })


async def broadcast_file_processed(filename: str, chunks: int, project_id: str) -> None:
    """Broadcast file processing completion."""
    await manager.broadcast("file_processed", {
        "filename": filename,
        "chunks": chunks,
        "project_id": project_id,
    })


async def broadcast_suggestion(message: str, project_id: str, action: str = "") -> None:
    """Broadcast a suggestion to the user."""
    await manager.broadcast("suggestion", {
        "message": message,
        "project_id": project_id,
        "action": action,
    })


async def broadcast_finding_created(
    finding_type: str, count: int, project_id: str, task_title: str = ""
) -> None:
    """Broadcast when new findings are stored after skill execution."""
    await manager.broadcast("finding_created", {
        "message": f"{count} {finding_type}(s) from: {task_title}" if task_title else f"{count} new {finding_type}(s) created",
        "finding_type": finding_type,
        "count": count,
        "project_id": project_id,
    })


async def broadcast_resource_throttle(reason: str, resources: Optional[dict] = None) -> None:
    """Broadcast a resource throttle event (agent paused due to hardware)."""
    await manager.broadcast("resource_throttle", {
        "reason": reason,
        "resources": resources or {},
    })


async def broadcast_task_queue_update(
    project_id: str, pending: int, in_progress: int, completed: int
) -> None:
    """Broadcast task queue depth so users see progress."""
    await manager.broadcast("task_queue_update", {
        "project_id": project_id,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
    })


async def broadcast_document_event(event: str, document_id: str, title: str, project_id: str) -> None:
    """Broadcast document created/updated/deleted event."""
    await manager.broadcast(event, {
        "document_id": document_id,
        "title": title,
        "project_id": project_id,
    })


async def broadcast_backup_event(event: str, backup_id: str, details: Optional[dict] = None) -> None:
    """Broadcast a backup lifecycle event (started, completed, failed, etc.)."""
    await manager.broadcast(event, {
        "backup_id": backup_id,
        **(details or {}),
    })


async def broadcast_meta_proposal(
    proposal_id: str,
    target_system: str,
    reason: str,
    project_id: str | None = None,
) -> None:
    """Broadcast a meta-hyperagent proposal notification."""
    data = {
        "proposal_id": proposal_id,
        "target_system": target_system,
        "reason": reason,
    }
    if project_id:
        data["project_id"] = project_id
    await manager.broadcast("meta_proposal", data)


async def broadcast_deployment_response(
    deployment_id: str, conversation_id: str, message_data: dict
) -> None:
    """Broadcast when a participant responds to a deployment question."""
    await manager.broadcast("deployment_response", {
        "deployment_id": deployment_id,
        "conversation_id": conversation_id,
        **message_data,
    })


async def broadcast_deployment_finding(
    deployment_id: str, finding_type: str, finding_data: dict
) -> None:
    """Broadcast when a new finding is extracted from a deployment response."""
    await manager.broadcast("deployment_finding", {
        "deployment_id": deployment_id,
        "finding_type": finding_type,
        **finding_data,
    })


async def broadcast_deployment_progress(
    deployment_id: str, stats: dict
) -> None:
    """Broadcast deployment progress/analytics update."""
    await manager.broadcast("deployment_progress", {
        "deployment_id": deployment_id,
        **stats,
    })


async def broadcast(event: dict) -> None:
    """Broadcast a raw event dict (type + data)."""
    event_type = event.get("type", "unknown")
    data = event.get("data", {})
    await manager.broadcast(event_type, data)


async def broadcast_channel_status(instance_id: str, status: str, detail: str = "") -> None:
    """Broadcast a channel instance status change (started, stopped, healthy, unhealthy)."""
    await manager.broadcast("channel_status", {
        "instance_id": instance_id,
        "status": status,
        "detail": detail,
    })


async def broadcast_channel_message(instance_id: str, message_data: dict) -> None:
    """Broadcast a channel message event (inbound or outbound)."""
    await manager.broadcast("channel_message", {
        "instance_id": instance_id,
        **message_data,
    })


async def broadcast_autoresearch_progress(experiment_data: dict) -> None:
    """Broadcast autoresearch experiment progress."""
    await manager.broadcast("autoresearch_progress", experiment_data)


async def broadcast_autoresearch_complete(loop_type: str, summary: dict) -> None:
    """Broadcast autoresearch loop completion."""
    await manager.broadcast("autoresearch_complete", {"loop_type": loop_type, **summary})


# ---------------------------------------------------------------------------
# Steering events — mid-execution message injection
# ---------------------------------------------------------------------------

async def broadcast_steering_message(agent_id: str, message: str, source: str = "user") -> None:
    """Broadcast that a steering message was received and queued."""
    await manager.broadcast("steering_message", {
        "agent_id": agent_id,
        "message": message,
        "source": source,
        "direction": "queued",
    })


async def broadcast_steering_response(agent_id: str, response: str) -> None:
    """Broadcast the agent's response to a steering message."""
    await manager.broadcast("steering_message", {
        "agent_id": agent_id,
        "response": response,
        "direction": "response",
    })


async def broadcast_agent_idle(agent_id: str) -> None:
    """Broadcast that an agent has finished all work (steering + follow-up processed)."""
    await manager.broadcast("agent_idle", {"agent_id": agent_id})
