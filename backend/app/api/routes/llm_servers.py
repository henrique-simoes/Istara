"""LLM Server CRUD routes — manage external LLM endpoints."""

import json
import logging
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.endpoint_security import EndpointPolicy, normalized_service_url, redacted_endpoint_label
from app.core.field_encryption import decrypt_field, encrypt_field
from app.core.permissions import require_global_role
from app.models.database import get_db
from app.models.llm_server import LLMServer

router = APIRouter()
logger = logging.getLogger(__name__)


class LLMServerCreate(BaseModel):
    name: str
    # ollama | lmstudio | openai_compat | vllm | sglang | llamacpp | mlx | anthropic
    provider_type: str = "openai_compat"
    host: str
    api_key: str = ""
    is_local: bool = True
    priority: int = 10


class LLMServerUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    host: str | None = None
    api_key: str | None = None
    priority: int | None = None
    is_local: bool | None = None


def _is_local_host(host: str) -> bool:
    parsed = urlparse(host if "://" in host else f"http://{host}")
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _runtime_entry_for_server(server: LLMServer):
    """Build the live router entry for a persisted LLM server."""
    from app.core.llm_router import LLMServerEntry

    return LLMServerEntry(
        server_id=server.id,
        name=server.name,
        provider_type=server.provider_type,
        host=server.host,
        api_key=decrypt_field(server.api_key) if server.api_key else "",
        priority=server.priority,
        is_local=server.is_local,
    )


async def _register_and_probe_server(server: LLMServer) -> tuple[object, bool]:
    """Refresh a persisted server in the live compute registry and probe it."""
    from app.core.llm_router import llm_router

    llm_router.unregister_server(server.id)
    entry = _runtime_entry_for_server(server)
    llm_router.register_server(entry)

    healthy = await entry.check_health()
    server.is_healthy = healthy
    server.provider_type = entry.provider_type
    server.last_health_check = datetime.now(UTC)
    server.last_latency_ms = entry.last_latency_ms
    server.capabilities = json.dumps(entry.model_capabilities or {})
    return entry, healthy


@router.get("/llm-servers")
async def list_llm_servers(db: AsyncSession = Depends(get_db)):
    """List all registered LLM servers."""
    result = await db.execute(select(LLMServer).order_by(LLMServer.priority))
    servers = result.scalars().all()

    # Also include live router status
    from app.core.llm_router import llm_router

    router_status = llm_router.list_servers()

    # Get live health error from compute registry nodes
    from app.core.compute_registry import compute_registry

    node_errors = {}
    for nid, node in compute_registry._nodes.items():
        if hasattr(node, "health_error") and node.health_error:
            node_errors[nid] = node.health_error

    return {
        "servers": [
            {
                "id": s.id,
                "name": s.name,
                "provider_type": s.provider_type,
                "host": s.host,
                "has_api_key": bool(s.api_key and s.api_key != ""),
                "is_local": s.is_local,
                "is_healthy": s.is_healthy,
                "is_relay": s.is_relay,
                "priority": s.priority,
                "last_latency_ms": s.last_latency_ms,
                "last_health_check": (
                    s.last_health_check.isoformat() if s.last_health_check else None
                ),
                "capabilities": json.loads(s.capabilities) if s.capabilities else {},
                "health_error": node_errors.get(s.id, ""),
            }
            for s in servers
        ],
        "router_live": router_status,
    }


@router.post("/llm-servers")
async def add_llm_server(
    data: LLMServerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Add a new external LLM server."""
    require_global_role(request, "viewer")
    try:
        normalized_host = normalized_service_url(
            data.host,
            EndpointPolicy(service_name="LLM server"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    inferred_is_local = _is_local_host(normalized_host)

    server = LLMServer(
        id=str(uuid.uuid4()),
        name=data.name,
        provider_type=data.provider_type,
        host=normalized_host,
        api_key=encrypt_field(data.api_key) if data.api_key else "",
        is_local=inferred_is_local,
        priority=data.priority,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)

    # Register with the live compute registry and run the initial probe.
    _, healthy = await _register_and_probe_server(server)
    await db.commit()

    logger.info(
        "Added LLM server: %s (%s @ %s) healthy=%s",
        server.name,
        server.provider_type,
        redacted_endpoint_label(server.host),
        healthy,
    )

    return {
        "id": server.id,
        "name": server.name,
        "provider_type": server.provider_type,
        "host": server.host,
        "is_healthy": server.is_healthy,
        "last_latency_ms": server.last_latency_ms,
    }


@router.post("/llm-servers/{server_id}/health-check")
async def health_check_server(server_id: str, db: AsyncSession = Depends(get_db)):
    """Run a health check on a specific LLM server."""
    result = await db.execute(select(LLMServer).where(LLMServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    from app.core.llm_router import llm_router

    # Look up by ID first, then by host URL (discovered servers use different IDs)
    router_server = llm_router._servers.get(server_id)
    if not router_server:
        for entry in llm_router._servers.values():
            if entry.host == server.host:
                router_server = entry
                break

    if not router_server:
        router_server, healthy = await _register_and_probe_server(server)
        await db.commit()

        from app.core.compute_registry import compute_registry

        node = compute_registry._nodes.get(server_id)
        return {
            "server_id": server_id,
            "healthy": healthy,
            "latency_ms": router_server.last_latency_ms,
            "health_error": getattr(node, "health_error", "") if node else "",
        }

    if router_server:
        healthy = await router_server.check_health()
        server.is_healthy = healthy
        server.provider_type = router_server.provider_type
        server.last_health_check = datetime.now(UTC)
        server.last_latency_ms = router_server.last_latency_ms
        server.capabilities = json.dumps(router_server.model_capabilities or {})
        await db.commit()
        # Get health error from the compute node
        from app.core.compute_registry import compute_registry

        node = compute_registry._nodes.get(server_id)
        health_error = getattr(node, "health_error", "") if node else ""
        return {
            "server_id": server_id,
            "healthy": healthy,
            "latency_ms": router_server.last_latency_ms,
            "health_error": health_error,
        }

    return {
        "server_id": server_id,
        "healthy": False,
        "health_error": "Server not registered in router",
    }


@router.patch("/llm-servers/{server_id}")
async def update_llm_server(
    server_id: str, data: LLMServerUpdate, request: Request, db: AsyncSession = Depends(get_db)
):
    """Update an LLM server's configuration."""
    require_global_role(request, "viewer")
    result = await db.execute(select(LLMServer).where(LLMServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = data.model_dump(exclude_unset=True)
    for optional_text_field in ("name", "provider_type", "host"):
        if update_data.get(optional_text_field) is None:
            update_data.pop(optional_text_field, None)
    # Encrypt API key if being updated
    if "api_key" in update_data:
        update_data["api_key"] = (
            encrypt_field(update_data["api_key"]) if update_data["api_key"] else ""
        )
    if "host" in update_data and update_data["host"]:
        try:
            update_data["host"] = normalized_service_url(
                update_data["host"],
                EndpointPolicy(service_name="LLM server"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        update_data["is_local"] = _is_local_host(update_data["host"])
    for field, value in update_data.items():
        setattr(server, field, value)
    await db.commit()
    await db.refresh(server)

    entry, healthy = await _register_and_probe_server(server)
    await db.commit()

    from app.core.compute_registry import compute_registry

    node = compute_registry._nodes.get(server_id)
    return {
        "id": server.id,
        "updated": True,
        "provider_type": server.provider_type,
        "host": server.host,
        "is_healthy": healthy,
        "last_latency_ms": entry.last_latency_ms,
        "health_error": getattr(node, "health_error", "") if node else "",
    }


@router.delete("/llm-servers/{server_id}")
async def delete_llm_server(server_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Remove an LLM server."""
    require_global_role(request, "viewer")
    result = await db.execute(select(LLMServer).where(LLMServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    from app.core.llm_router import llm_router

    llm_router.unregister_server(server_id)

    await db.delete(server)
    await db.commit()

    return {"id": server_id, "deleted": True}


@router.post("/llm-servers/discover")
async def discover_network_llm_servers(request: Request):
    """Scan local network for LLM servers (LM Studio, Ollama, OpenAI-compatible)."""
    require_global_role(request, "viewer")
    from app.core.network_discovery import discover_and_register

    discovered = await discover_and_register()
    return {
        "discovered": len(discovered),
        "servers": discovered,
    }
