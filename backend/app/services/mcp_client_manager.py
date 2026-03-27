"""MCP Client Registry -- connect to external MCP servers and invoke their tools.

Follows the same MCP client pattern as ``stitch_service.py``:
short-lived sessions via ``mcp.client.streamable_http``.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server_config import MCPServerConfig

logger = logging.getLogger(__name__)

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
    config = MCPServerConfig(
        id=str(uuid.uuid4()),
        name=name,
        url=url,
        transport=transport,
        headers_json=json.dumps(headers or {}),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    logger.info("Registered MCP server '%s' at %s", name, url)
    return config


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

    headers = json.loads(server.headers_json) if server.headers_json else {}

    try:
        async with streamablehttp_client(server.url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema or {},
                    }
                    for t in result.tools
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

    headers = json.loads(server.headers_json) if server.headers_json else {}

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

    headers = json.loads(server.headers_json) if server.headers_json else {}

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
    query = select(MCPServerConfig).order_by(MCPServerConfig.created_at.desc())
    if active_only:
        query = query.where(MCPServerConfig.is_active.is_(True))
    result = await db.execute(query)
    servers = result.scalars().all()
    return [s.to_dict() for s in servers]


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
    for server in servers:
        tools = json.loads(server.tools_json) if server.tools_json else []
        for tool in tools:
            all_tools.append({
                **tool,
                "server_id": server.id,
                "server_name": server.name,
            })

    return all_tools
