"""Compute pool API routes and relay WebSocket endpoint."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.compute_pool import RelayNode, compute_pool

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_unified_nodes() -> tuple[list[dict], dict]:
    """Build a unified node list from relay pool and LLM Router servers.

    Returns ``(all_nodes, pool_stats)`` where *pool_stats* is the raw
    relay-pool stats dict (used for RAM/CPU aggregation).
    """
    from app.core.llm_router import llm_router

    pool_stats = compute_pool.get_stats()

    all_nodes: list[dict] = []
    seen_hosts: set[str] = set()

    # Add relay pool nodes first
    for node in pool_stats.get("nodes", []):
        host = node.get("provider_host", "")
        if host:
            seen_hosts.add(host)
        node["source"] = "relay"
        all_nodes.append(node)

    # Add LLM Router servers (skip if already present as a relay node)
    for server in llm_router._servers.values():
        if server.host in seen_hosts:
            continue
        seen_hosts.add(server.host)
        all_nodes.append({
            "node_id": server.server_id,
            "hostname": server.name,
            "host": server.host,
            "source": "local" if server.is_local else "network",
            "state": "healthy" if server.is_healthy else "unhealthy",
            "loaded_models": server.available_models or [],
            "is_local": server.is_local,
            "priority": server.priority,
            "latency_ms": server.last_latency_ms or 0,
            "alive": server.is_healthy,
            "ram_total_gb": 0,
            "ram_available_gb": 0,
            "cpu_cores": 0,
            "cpu_load_pct": 0,
            "model_capabilities": server.model_capabilities or {},
        })

    return all_nodes, pool_stats


@router.get("/compute/nodes")
async def list_compute_nodes():
    """List all compute nodes — relay pool + LLM Router servers."""
    all_nodes, pool_stats = _build_unified_nodes()
    return {
        "total_nodes": len(all_nodes),
        "alive_nodes": sum(1 for n in all_nodes if n.get("alive", True)),
        "nodes": all_nodes,
    }


@router.get("/compute/stats")
async def compute_stats():
    """Unified compute stats — includes both LLM Router servers and relay nodes."""
    all_nodes, pool_stats = _build_unified_nodes()

    # Aggregate models from all sources
    total_models: set[str] = set()
    for n in all_nodes:
        total_models.update(n.get("loaded_models", []))

    alive_count = sum(1 for n in all_nodes if n.get("alive", True))

    return {
        "total_nodes": len(all_nodes),
        "alive_nodes": alive_count,
        "total_ram_gb": pool_stats.get("total_ram_gb", 0),
        "available_ram_gb": pool_stats.get("available_ram_gb", 0),
        "total_cpu_cores": pool_stats.get("total_cpu_cores", 0),
        "available_models": sorted(total_models),
        "swarm_tier": _compute_swarm_tier(alive_count),
        "nodes": all_nodes,
    }


@router.get("/compute/model-warnings")
async def model_warnings():
    """Check loaded models for capability limitations relevant to ReClaw."""
    from app.core.llm_router import llm_router

    warnings: list[dict] = []
    for server in llm_router._servers.values():
        for model_name, caps in server.model_capabilities.items():
            if "embed" in model_name.lower():
                continue  # Skip embedding models
            if not caps.get("supports_tools", False):
                warnings.append({
                    "model": model_name,
                    "server": server.name,
                    "warning": (
                        f"{model_name} does not support native tool calling. "
                        "Chat will use text-based tools (less reliable)."
                    ),
                    "severity": "medium",
                })
            if caps.get("context_length", 4096) < 4096:
                warnings.append({
                    "model": model_name,
                    "server": server.name,
                    "warning": (
                        f"{model_name} has a small context window "
                        f"({caps.get('context_length')} tokens). "
                        "Complex conversations may be truncated."
                    ),
                    "severity": "high",
                })
            param = caps.get("parameter_count", "")
            small_params = {"0.5B", "0.8B", "1B", "1.5B", "2B"}
            if param and param in small_params:
                warnings.append({
                    "model": model_name,
                    "server": server.name,
                    "warning": (
                        f"{model_name} ({param}) is very small for research tasks. "
                        "Consider using a 4B+ model for better quality."
                    ),
                    "severity": "low",
                })
    return {"warnings": warnings}


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
