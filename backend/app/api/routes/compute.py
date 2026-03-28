"""Compute pool API routes and relay WebSocket endpoint."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.compute_registry import ComputeNode, compute_registry

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/compute/nodes")
async def list_compute_nodes():
    """List all compute nodes from the unified registry."""
    stats = compute_registry.get_stats()
    return {
        "total_nodes": stats["total_nodes"],
        "alive_nodes": stats["alive_nodes"],
        "nodes": stats["nodes"],
    }


@router.get("/compute/stats")
async def compute_stats():
    """Unified compute stats — all nodes from the single registry."""
    return compute_registry.get_stats()


@router.get("/compute/model-warnings")
async def model_warnings():
    """Check loaded models for capability limitations relevant to ReClaw."""
    return {"warnings": compute_registry.get_warnings()}


@router.websocket("/ws/relay")
async def relay_websocket(ws: WebSocket):
    """WebSocket endpoint for relay node connections.

    Protocol:
    - Client sends: {"type": "register", "hostname": "...", "user_id": "...", ...}
    - Client sends: {"type": "heartbeat", "stats": {...}}
    - Server sends: {"type": "llm_request", "request_id": "...", ...}
    - Client sends: {"type": "llm_response", "request_id": "...", ...}

    Authentication:
    - If NETWORK_ACCESS_TOKEN is set: non-localhost connections must provide it
    - If TEAM_MODE is true: JWT required regardless of origin
    - Localhost without token: allowed (backward-compatible)
    """
    # Network security check (access token for non-localhost)
    from app.core.network_security import check_websocket_network_token
    if not check_websocket_network_token(ws):
        await ws.close(code=4001, reason="Network access token required")
        return

    # Team mode: also require JWT
    from app.config import settings as app_settings
    if app_settings.team_mode:
        from app.core.auth import verify_token
        auth_header = ws.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            token = ws.query_params.get("token", "")
        if not token or verify_token(token) is None:
            await ws.close(code=4001, reason="JWT authentication required")
            return

    await ws.accept()
    node_id = str(uuid.uuid4())
    node: ComputeNode | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "register":
                node = ComputeNode(
                    node_id=node_id,
                    name=f"Relay: {msg.get('hostname', 'unknown')}",
                    host=msg.get("provider_host", ""),
                    source="relay",
                    provider_type=msg.get("provider_type", "ollama"),
                    is_relay=True,
                    is_healthy=True,
                    health_state="ready",
                    priority=20,
                    websocket=ws,
                    user_id=msg.get("user_id", "anonymous"),
                    ip_address=msg.get("ip_address", ""),
                    provider_host=msg.get("provider_host", ""),
                    ram_total_gb=msg.get("ram_total_gb", 0),
                    cpu_cores=msg.get("cpu_cores", 0),
                    gpu_name=msg.get("gpu_name", ""),
                    gpu_vram_mb=msg.get("gpu_vram_mb", 0),
                    loaded_models=msg.get("loaded_models", []),
                )
                compute_registry.register_node(node)
                await ws.send_json({"type": "registered", "node_id": node_id})
                logger.info(f"Relay node registered: {node.name} ({node_id})")

            elif msg_type == "heartbeat" and node:
                stats = msg.get("stats", {})
                compute_registry.update_heartbeat(node_id, stats)

            elif msg_type == "llm_response":
                # Response to a forwarded LLM request — dispatch to waiting handler
                pass  # TODO: implement request/response matching for relay LLM calls

    except WebSocketDisconnect:
        if node:
            compute_registry.remove_node(node_id)
            logger.info(f"Relay node disconnected: {node.name}")
    except Exception as e:
        logger.error(f"Relay WebSocket error: {e}")
        if node:
            compute_registry.remove_node(node_id)
