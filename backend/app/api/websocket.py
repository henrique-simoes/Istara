"""WebSocket endpoint for real-time agent status updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all connected clients."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        disconnected = []
        for connection in self._connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

        # Persist notification asynchronously — never block broadcasts
        asyncio.create_task(self._persist_notification(event_type, data))

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
    await manager.connect(websocket)

    # Authenticate WebSocket connection
    token = websocket.query_params.get("token", "")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if token:
        from app.core.auth import verify_token
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
    else:
        await websocket.close(code=4001, reason="Authentication required. Pass ?token=<jwt>")
        return

    try:
        # Send initial status
        await manager.send_to(websocket, "connected", {
            "message": "Connected to ReClaw real-time updates.",
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

async def broadcast_agent_status(status: str, details: str = "") -> None:
    """Broadcast agent status update."""
    await manager.broadcast("agent_status", {"status": status, "details": details})


async def broadcast_task_progress(task_id: str, progress: float, notes: str = "") -> None:
    """Broadcast task progress update."""
    await manager.broadcast("task_progress", {
        "task_id": task_id,
        "progress": progress,
        "notes": notes,
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
    proposal_id: str, target_system: str, reason: str
) -> None:
    """Broadcast a meta-hyperagent proposal notification."""
    await manager.broadcast("meta_proposal", {
        "proposal_id": proposal_id,
        "target_system": target_system,
        "reason": reason,
    })


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
