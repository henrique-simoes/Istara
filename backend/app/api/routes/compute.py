"""Compute pool API routes and relay WebSocket endpoint."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.compute_pool import RelayNode, compute_pool

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/compute/nodes")
async def list_compute_nodes():
    """List all compute pool nodes and their status."""
    return compute_pool.get_stats()


@router.get("/compute/stats")
async def compute_stats():
    """Get aggregate compute pool statistics."""
    stats = compute_pool.get_stats()
    return {
        "total_nodes": stats["total_nodes"],
        "alive_nodes": stats["alive_nodes"],
        "total_ram_gb": stats["total_ram_gb"],
        "available_ram_gb": stats["available_ram_gb"],
        "total_cpu_cores": stats["total_cpu_cores"],
        "available_models": stats["available_models"],
        "swarm_tier": _compute_swarm_tier(stats["alive_nodes"]),
    }


def _compute_swarm_tier(alive_count: int) -> str:
    """Determine swarm orchestration tier based on available nodes."""
    if alive_count >= 8:
        return "full_swarm"
    elif alive_count >= 4:
        return "standard"
    elif alive_count >= 2:
        return "conservative"
    elif alive_count >= 1:
        return "minimal"
    return "local_only"


@router.websocket("/ws/relay")
async def relay_websocket(ws: WebSocket):
    """WebSocket endpoint for relay node connections.

    Protocol:
    - Client sends: {"type": "register", "hostname": "...", "user_id": "...", ...}
    - Client sends: {"type": "heartbeat", "stats": {...}}
    - Server sends: {"type": "llm_request", "request_id": "...", ...}
    - Client sends: {"type": "llm_response", "request_id": "...", ...}

    In team mode, relay connections require a valid JWT in the Authorization header.
    """
    # Authenticate relay connections in team mode
    from app.config import settings as app_settings
    if app_settings.team_mode:
        from app.core.auth import verify_token
        auth_header = ws.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            token = ws.query_params.get("token", "")
        if not token or verify_token(token) is None:
            await ws.close(code=4001, reason="Authentication required")
            return

    await ws.accept()
    node_id = str(uuid.uuid4())
    node: RelayNode | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "register":
                node = RelayNode(
                    node_id=node_id,
                    user_id=msg.get("user_id", "anonymous"),
                    hostname=msg.get("hostname", "unknown"),
                    ip_address=msg.get("ip_address", ""),
                    ram_total_gb=msg.get("ram_total_gb", 0),
                    cpu_cores=msg.get("cpu_cores", 0),
                    gpu_name=msg.get("gpu_name", ""),
                    gpu_vram_mb=msg.get("gpu_vram_mb", 0),
                    loaded_models=msg.get("loaded_models", []),
                    provider_type=msg.get("provider_type", "ollama"),
                    provider_host=msg.get("provider_host", ""),
                )
                compute_pool.register_node(node)
                await ws.send_json({"type": "registered", "node_id": node_id})
                logger.info(f"Relay node registered: {node.hostname} ({node_id})")

            elif msg_type == "heartbeat" and node:
                stats = msg.get("stats", {})
                compute_pool.update_heartbeat(node_id, stats)

            elif msg_type == "llm_response":
                # Response to a forwarded LLM request — dispatch to waiting handler
                pass  # TODO: implement request/response matching for relay LLM calls

    except WebSocketDisconnect:
        if node:
            compute_pool.unregister_node(node_id)
            logger.info(f"Relay node disconnected: {node.hostname}")
    except Exception as e:
        logger.error(f"Relay WebSocket error: {e}")
        if node:
            compute_pool.unregister_node(node_id)
