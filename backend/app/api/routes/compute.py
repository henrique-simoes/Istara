"""Compute pool API routes and relay WebSocket endpoint."""

import json
import logging
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.compute_registry import ComputeNode, compute_registry, infer_provider_type
from app.core.connection_string import decode_connection_string, hash_connection_string
from app.core.permissions import get_visible_project_or_404, require_global_role
from app.models.connection_string import ConnectionString
from app.models.database import get_db
from app.models.project_member import ProjectMember

router = APIRouter()
logger = logging.getLogger(__name__)


def _infer_relay_provider_type(provider_host: str, requested_provider: str | None) -> str:
    """Infer the safest provider contract for a relay donor's advertised host."""
    return infer_provider_type(requested_provider, provider_host)


def _normalize_project_scope(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        project_id = str(value or "").strip()
        if project_id and project_id not in normalized:
            normalized.append(project_id)
    return normalized


def _clean_project_id(project_id: str | None) -> str | None:
    cleaned = (project_id or "").strip()
    return cleaned or None


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = _clean_project_id(project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


def _parse_connection_scope(conn: ConnectionString | None, payload: dict) -> list[str]:
    from_db: list[str] = []
    if conn is not None:
        try:
            from_db = _normalize_project_scope(json.loads(conn.allowed_project_ids_json or "[]"))
        except Exception:
            from_db = []
    from_payload = _normalize_project_scope(payload.get("allowed_project_ids"))
    return from_db or from_payload


def _is_connection_expired(conn: ConnectionString) -> bool:
    expires_at = conn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < datetime.now(UTC)


async def _scope_from_connection_string(
    db,
    connection_string: str,
) -> tuple[list[str], str]:
    payload = decode_connection_string(connection_string)
    if not payload:
        return [], "invalid"
    if payload.get("kind") != "compute_donation":
        return [], "wrong_type"
    if payload.get("network_token") != settings.network_access_token:
        return [], "token_mismatch"

    result = await db.execute(
        select(ConnectionString).where(
            ConnectionString.connection_string_hash == hash_connection_string(connection_string)
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        return [], "missing"
    if conn.token_type != "compute_donation":
        return [], "wrong_type"
    if not conn.is_active or conn.is_redeemed or _is_connection_expired(conn):
        return [], "inactive"

    conn.last_validated_at = datetime.now(UTC)
    await db.commit()
    scope = _parse_connection_scope(conn, payload)
    if settings.team_mode and "*" in scope:
        return [], "wildcard_scope"
    return scope, "ok"


async def _scope_from_user(db, user_id: str, role: str) -> list[str]:
    if not user_id:
        return []
    if role == "admin":
        return ["*"]
    result = await db.execute(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    )
    return _normalize_project_scope(list(result.scalars().all()))


def _combine_project_scopes(
    first: list[str] | None,
    second: list[str] | None,
) -> list[str]:
    scopes = [scope for scope in (first, second) if scope is not None]
    if not scopes:
        return []
    if len(scopes) == 1:
        return scopes[0]

    left, right = scopes
    if "*" in left:
        return right
    if "*" in right:
        return left
    right_set = set(right)
    return [project_id for project_id in left if project_id in right_set]


async def _require_compute_pool_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
) -> str:
    """Authorize regular Compute Pool visibility for one active project."""
    require_global_role(request, "researcher")
    scoped_project_id = _require_project_id(project_id)
    await get_visible_project_or_404(db, request, scoped_project_id, min_role="viewer")
    return scoped_project_id


@router.get("/compute/nodes")
async def list_compute_nodes(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List compute nodes visible to one authorized active project."""
    scoped_project_id = await _require_compute_pool_scope(db, request, project_id)
    stats = compute_registry.get_stats(project_id=scoped_project_id)
    return {
        "total_nodes": stats["total_nodes"],
        "alive_nodes": stats["alive_nodes"],
        "nodes": stats["nodes"],
    }


@router.get("/compute/stats")
async def compute_stats(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Unified compute stats for one authorized active project."""
    scoped_project_id = await _require_compute_pool_scope(db, request, project_id)
    return compute_registry.get_stats(project_id=scoped_project_id)


@router.get("/compute/model-warnings")
async def model_warnings(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Check visible models for capability limitations relevant to Istara."""
    scoped_project_id = await _require_compute_pool_scope(db, request, project_id)
    return {"warnings": compute_registry.get_warnings(project_id=scoped_project_id)}


@router.websocket("/ws/relay")
async def relay_websocket(ws: WebSocket):
    """WebSocket endpoint for relay node connections.

    Protocol:
    - Client sends: {"type": "register", "hostname": "...", "user_id": "...", ...}
    - Client sends: {"type": "heartbeat", "stats": {...}}
    - Server sends: {"type": "llm_request", "request_id": "...", ...}
    - Client sends: {"type": "llm_response", "request_id": "...", ...}

    Authentication (always enforced):
    - If NETWORK_ACCESS_TOKEN is set and valid: connection allowed
    - Otherwise: JWT required via Authorization header or ?token= query param
    - No unauthenticated relay connections permitted
    """
    # Always authenticate relay connections — regardless of team_mode or localhost.
    # A relay/browser node can provide either the network access token from an
    # invite string or a valid user JWT from an authenticated browser session.
    from app.core.auth import verify_token
    from app.core.auth_sessions import validate_auth_session
    from app.models.database import async_session

    network_token = ws.headers.get("x-access-token", "") or ws.query_params.get("access_token", "")
    connection_string = (
        ws.headers.get("x-istara-connection-string", "")
        or ws.query_params.get("connection_string", "")
    )
    auth_header = ws.headers.get("authorization", "")
    jwt_token = (
        auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    )
    if not jwt_token:
        jwt_token = ws.query_params.get("token", "")

    has_valid_network_token = bool(
        settings.network_access_token and network_token == settings.network_access_token
    )
    jwt_payload = verify_token(jwt_token) if jwt_token else None
    if jwt_payload is not None:
        async with async_session() as db:
            if not await validate_auth_session(db, jwt_payload):
                jwt_payload = None
    if not has_valid_network_token and jwt_payload is None:
        await ws.close(code=4001, reason="Authentication required for relay connections")
        return
    authenticated_user_id = str(jwt_payload.get("sub", "")) if jwt_payload else ""
    authenticated_role = str(jwt_payload.get("role", "")) if jwt_payload else ""
    connection_scope: list[str] | None = None
    user_scope: list[str] | None = None
    async with async_session() as db:
        if connection_string:
            connection_scope, reason = await _scope_from_connection_string(db, connection_string)
            if reason != "ok":
                await ws.close(code=4001, reason="Invalid compute donation connection string")
                return
        if jwt_payload is not None:
            user_scope = await _scope_from_user(db, authenticated_user_id, authenticated_role)
    allowed_project_ids = _combine_project_scopes(user_scope, connection_scope)

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
                # Resolve provider_host for optional provider metadata probes.
                # Chat execution itself uses the relay WebSocket so remote
                # donors do not need inbound provider ports.
                provider_host = msg.get("provider_host", "")
                ip_addr = msg.get("ip_address", "") or (ws.client.host if ws.client else "")
                resolved_host = provider_host
                if ip_addr and provider_host:
                    parsed = urlparse(provider_host)
                    if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                        netloc = f"{ip_addr}:{parsed.port}" if parsed.port else ip_addr
                        resolved_host = urlunparse(parsed._replace(netloc=netloc))
                        logger.info(f"Relay host resolved: {provider_host} -> {resolved_host}")
                provider_type = _infer_relay_provider_type(
                    resolved_host or provider_host,
                    msg.get("provider_type"),
                )

                node = ComputeNode(
                    node_id=node_id,
                    name=f"Relay: {msg.get('hostname', 'unknown')}",
                    host=resolved_host,
                    source="browser" if msg.get("user_id") == "browser" else "relay",
                    provider_type=provider_type,
                    is_relay=True,
                    is_healthy=True,
                    health_state="ready",
                    priority=20,
                    websocket=ws,
                    user_id=authenticated_user_id or msg.get("user_id", "anonymous"),
                    ip_address=ip_addr,
                    provider_host=provider_host,
                    allowed_project_ids=allowed_project_ids,
                    ram_total_gb=msg.get("ram_total_gb", 0),
                    ram_available_gb=msg.get("ram_available_gb", 0),
                    cpu_cores=msg.get("cpu_cores", 0),
                    cpu_load_pct=msg.get("cpu_load_pct", 0),
                    gpu_name=msg.get("gpu_name", ""),
                    gpu_vram_mb=msg.get("gpu_vram_mb", 0),
                    loaded_models=msg.get("loaded_models", []),
                    model_capabilities=msg.get("model_capabilities", {}),
                )
                if msg.get("health_error"):
                    node.health_error = str(msg["health_error"])[:200]
                    node.health_state = "no_model_server" if not node.loaded_models else "degraded"
                compute_registry.register_node(node)

                # Deduplicate: remove network-discovered nodes that
                # point to the same provider, since the relay connection
                # is the preferred path.
                compute_registry.remove_duplicate_network_nodes(node)

                # Immediately detect model capabilities so the relay is
                # usable for streaming without waiting for the 60s health loop.
                if resolved_host and not node.model_capabilities:
                    try:
                        from app.core.model_capabilities import (
                            detect_capabilities_generic,
                        )

                        caps = await detect_capabilities_generic(
                            resolved_host,
                            provider_type=provider_type,
                            active_probe=False,
                        )
                        node.model_capabilities = {k: v.to_dict() for k, v in caps.items()}
                        logger.info(
                            f"Relay capabilities detected immediately: "
                            f"{len(node.model_capabilities)} models"
                        )
                    except Exception as e:
                        logger.debug(f"Relay immediate capability detection failed: {e}")

                await ws.send_json(
                    {
                        "type": "registered",
                        "node_id": node_id,
                        "authorized_project_count": (
                            "all"
                            if "*" in allowed_project_ids
                            else len(allowed_project_ids)
                        ),
                    }
                )
                logger.info(f"Relay node registered: {node.name} ({node_id})")

            elif msg_type == "heartbeat" and node:
                stats = msg.get("stats", {})
                compute_registry.update_heartbeat(node_id, stats)

            elif msg_type in ("llm_response", "embed_response", "load_model_response"):
                # Response to a forwarded donor request — dispatch to waiting handler
                request_id = msg.get("request_id", "")
                if node and request_id:
                    future = node.pending_requests.pop(request_id, None)
                    if future and not future.done():
                        future.set_result(msg)

    except WebSocketDisconnect:
        if node:
            node.fail_pending_requests("Relay disconnected before responding")
            compute_registry.remove_node(node_id)
            logger.info(f"Relay node disconnected: {node.name}")
    except Exception as e:
        logger.error(f"Relay WebSocket error: {e}")
        if node:
            node.fail_pending_requests(f"Relay websocket error: {e}")
            compute_registry.remove_node(node_id)
