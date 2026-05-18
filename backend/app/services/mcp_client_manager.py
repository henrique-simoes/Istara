"""MCP Client Registry -- connect to external MCP servers and invoke their tools.

Follows the same MCP client pattern as ``stitch_service.py``:
short-lived sessions via ``mcp.client.streamable_http``.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_guard import ContentGuard
from app.core.endpoint_security import EndpointPolicy, normalized_service_url, redacted_endpoint_label
from app.core.field_encryption import decrypt_field, encrypt_field
from app.models.mcp_server_config import MCPServerConfig

logger = logging.getLogger(__name__)
SUPPORTED_TRANSPORTS = {"http"}
_guard = ContentGuard()
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
MAX_MCP_TOOL_DESCRIPTION_CHARS = 1000
MAX_MCP_TOOL_SCHEMA_BYTES = 16 * 1024

# ---------------------------------------------------------------------------
# Conditional import of MCP client libraries
# ---------------------------------------------------------------------------

try:
    from mcp.client.streamable_http import streamablehttp_client  # type: ignore[import-untyped]
    from mcp import ClientSession  # type: ignore[import-untyped]
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False
    logger.info("mcp client library not installed -- MCP client registry unavailable")


# ---------------------------------------------------------------------------
# Server registration
# ---------------------------------------------------------------------------


async def register_server(
    db: AsyncSession,
    name: str,
    url: str,
    transport: str = "http",
    headers: dict | None = None,
) -> MCPServerConfig:
    """Register a new external MCP server.

    Args:
        db: Database session.
        name: Human-readable server name.
        url: MCP server endpoint URL.
        transport: Transport type (http, stdio, websocket).
        headers: Optional auth / custom headers.

    Returns:
        The newly created MCPServerConfig row.
    """
    transport = transport.strip().lower()
    if transport not in SUPPORTED_TRANSPORTS:
        raise ValueError(
            "Only HTTP MCP client transport is currently supported by Istara. "
            "Start stdio or WebSocket servers behind an HTTP MCP bridge before registering them."
        )
    if "://" not in (url or ""):
        raise ValueError("MCP server URL must be an absolute http(s) URL")
    normalized_url = normalized_service_url(
        url,
        EndpointPolicy(service_name="MCP server"),
    )
    safe_headers = _validate_headers(headers or {})

    existing_result = await db.execute(
        select(MCPServerConfig)
        .where(
            MCPServerConfig.url == normalized_url,
            MCPServerConfig.transport == transport,
            MCPServerConfig.is_active.is_(True),
        )
        .order_by(MCPServerConfig.updated_at.desc())
    )
    existing = existing_result.scalars().first()
    if existing:
        existing.name = name
        existing.headers_json = encrypt_field(json.dumps(safe_headers))
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        logger.info(
            "Reused MCP server '%s' at %s",
            name,
            redacted_endpoint_label(normalized_url),
        )
        return existing

    config = MCPServerConfig(
        id=str(uuid.uuid4()),
        name=name,
        url=normalized_url,
        transport=transport,
        headers_json=encrypt_field(json.dumps(safe_headers)),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    logger.info("Registered MCP server '%s' at %s", name, redacted_endpoint_label(normalized_url))
    return config


def _validate_headers(headers: dict) -> dict[str, str]:
    """Validate MCP outbound headers before encrypting them at rest."""
    safe: dict[str, str] = {}
    for key, value in headers.items():
        key_str = str(key).strip()
        value_str = str(value)
        if not key_str:
            continue
        if any(ch in key_str or ch in value_str for ch in ("\r", "\n")):
            raise ValueError("MCP headers cannot contain newlines")
        if len(key_str) > 128 or len(value_str) > 4096:
            raise ValueError("MCP header key or value is too long")
        safe[key_str] = value_str
    return safe


def _safe_tool_descriptor(tool) -> dict | None:
    """Return a bounded, prompt-safe MCP tool descriptor."""
    name = str(getattr(tool, "name", "") or "").strip()
    if not _TOOL_NAME_RE.match(name):
        logger.warning("Dropping MCP tool with invalid name: %r", name[:80])
        return None

    description = str(getattr(tool, "description", "") or "")
    scan = _guard.scan_text(description)
    safe_description = scan.cleaned_text[:MAX_MCP_TOOL_DESCRIPTION_CHARS]
    warnings: list[str] = []
    if scan.threat_level in ("medium", "high"):
        warnings.append("description_prompt_injection_indicators")
        safe_description = (
            "[Istara security: tool description contained instruction-like content "
            "and was sanitized.] "
            + safe_description
        )[:MAX_MCP_TOOL_DESCRIPTION_CHARS]

    input_schema = getattr(tool, "inputSchema", None) or {}
    if not isinstance(input_schema, dict):
        input_schema = {}
        warnings.append("invalid_input_schema")
    encoded_schema = json.dumps(input_schema, sort_keys=True, default=str).encode("utf-8")
    if len(encoded_schema) > MAX_MCP_TOOL_SCHEMA_BYTES:
        input_schema = {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
            "x-istara-warning": "Original MCP tool schema exceeded Istara's cache limit.",
        }
        warnings.append("input_schema_truncated")

    return {
        "name": name,
        "description": safe_description,
        "input_schema": input_schema,
        "risk_warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------


async def discover_tools(db: AsyncSession, server_id: str) -> list[dict]:
    """Connect to an MCP server, list its tools, and cache the result.

    Returns:
        List of tool descriptors ``[{"name", "description", "input_schema"}, ...]``.
    """
    server = await db.get(MCPServerConfig, server_id)
    if not server:
        return []

    if not MCP_CLIENT_AVAILABLE:
        logger.warning("MCP client library not installed -- cannot discover tools")
        server.health_status = "unavailable"
        await db.commit()
        return []

    raw_headers = decrypt_field(server.headers_json) if server.headers_json else "{}"
    headers = json.loads(raw_headers)

    try:
        async with streamablehttp_client(server.url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = [
                    descriptor
                    for t in result.tools
                    for descriptor in [_safe_tool_descriptor(t)]
                    if descriptor is not None
                ]
                server.tools_json = json.dumps(tools)
                server.last_discovery_at = datetime.now(timezone.utc)
                server.health_status = "healthy"
                await db.commit()
                logger.info(
                    "Discovered %d tools from MCP server '%s'", len(tools), server.name
                )
                return tools
    except Exception as exc:
        logger.warning("Tool discovery failed for '%s': %s", server.name, exc)
        server.health_status = "unhealthy"
        await db.commit()
        return []


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------


async def call_tool(
    db: AsyncSession,
    server_id: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Call a tool on an external MCP server.

    Opens a short-lived MCP session, invokes the tool, and returns the
    parsed result.
    """
    server = await db.get(MCPServerConfig, server_id)
    if not server:
        return {"error": "Server not found"}

    if not server.is_active:
        return {"error": f"Server '{server.name}' is inactive"}

    if not MCP_CLIENT_AVAILABLE:
        return {"error": "MCP client library not installed"}

    raw_headers = decrypt_field(server.headers_json) if server.headers_json else "{}"
    headers = json.loads(raw_headers)

    try:
        async with streamablehttp_client(server.url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                # Parse first text content block as JSON if possible
                for content in result.content:
                    if hasattr(content, "text") and content.text:
                        try:
                            return json.loads(content.text)
                        except (json.JSONDecodeError, ValueError):
                            return {"text": content.text}
                    if hasattr(content, "data") and content.data:
                        return {
                            "data": content.data,
                            "mime_type": getattr(content, "mimeType", "application/octet-stream"),
                        }
                return {"result": "empty_response"}
    except Exception as exc:
        logger.warning(
            "Tool call '%s' on server '%s' failed: %s", tool_name, server.name, exc
        )
        server.health_status = "unhealthy"
        await db.commit()
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def health_check(db: AsyncSession, server_id: str) -> dict:
    """Check connectivity to an MCP server by attempting tool discovery."""
    server = await db.get(MCPServerConfig, server_id)
    if not server:
        return {"healthy": False, "error": "Server not found"}

    if not MCP_CLIENT_AVAILABLE:
        return {"healthy": False, "error": "MCP client library not installed"}

    raw_headers = decrypt_field(server.headers_json) if server.headers_json else "{}"
    headers = json.loads(raw_headers)

    try:
        async with streamablehttp_client(server.url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.list_tools()
                tool_count = len(result.tools)

        server.health_status = "healthy"
        await db.commit()
        return {"healthy": True, "tool_count": tool_count, "server": server.name}
    except Exception as exc:
        server.health_status = "unhealthy"
        await db.commit()
        return {"healthy": False, "error": str(exc), "server": server.name}


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------


async def unregister_server(db: AsyncSession, server_id: str) -> bool:
    """Remove an MCP server from the registry."""
    server = await db.get(MCPServerConfig, server_id)
    if not server:
        return False
    await db.delete(server)
    await db.commit()
    logger.info("Unregistered MCP server '%s'", server.name)
    return True


async def list_servers(db: AsyncSession, active_only: bool = False) -> list[dict]:
    """List all registered MCP servers."""
    query = select(MCPServerConfig).order_by(
        MCPServerConfig.updated_at.desc(),
        MCPServerConfig.created_at.desc(),
    )
    if active_only:
        query = query.where(MCPServerConfig.is_active.is_(True))
    result = await db.execute(query)
    servers = result.scalars().all()
    deduped: dict[tuple[str, str], dict] = {}
    for server in servers:
        key = (server.transport, server.url)
        if key not in deduped:
            row = server.to_dict()
            row["duplicate_count"] = 1
            deduped[key] = row
        else:
            deduped[key]["duplicate_count"] += 1
    return list(deduped.values())


async def list_all_tools(db: AsyncSession) -> list[dict]:
    """Aggregate cached tools from all active servers.

    Returns a flat list of tool descriptors, each annotated with the
    server_id and server_name they belong to.
    """
    result = await db.execute(
        select(MCPServerConfig).where(MCPServerConfig.is_active.is_(True))
    )
    servers = result.scalars().all()

    all_tools: list[dict] = []
    seen_servers: set[tuple[str, str]] = set()
    for server in servers:
        key = (server.transport, server.url)
        if key in seen_servers:
            continue
        seen_servers.add(key)
        tools = json.loads(server.tools_json) if server.tools_json else []
        for tool in tools:
            all_tools.append({
                **tool,
                "server_id": server.id,
                "server_name": server.name,
            })

    return all_tools
