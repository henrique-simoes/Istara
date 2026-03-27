"""MCP management API -- server exposure control + client registry.

MCP Server endpoints manage what ReClaw exposes to external agents.
MCP Client endpoints manage connections TO external MCP servers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ServerToggleRequest(BaseModel):
    enabled: bool


class PolicyUpdateRequest(BaseModel):
    # Low-risk
    allow_list_skills: bool | None = None
    allow_list_projects: bool | None = None
    allow_get_deployment_status: bool | None = None
    # Sensitive
    allow_get_findings: bool | None = None
    allow_search_memory: bool | None = None
    # High-risk
    allow_execute_skill: bool | None = None
    allow_create_project: bool | None = None
    allow_deploy_research: bool | None = None
    # Resources
    allow_project_resource: bool | None = None
    allow_findings_resource: bool | None = None
    allow_skills_resource: bool | None = None
    # Limits
    allowed_project_ids: list[str] | None = None
    max_findings_per_request: int | None = None
    max_skill_executions_per_hour: int | None = None


class ClientRegisterRequest(BaseModel):
    name: str
    url: str
    transport: str = "http"
    headers: dict | None = None


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


# ===========================================================================
# MCP SERVER ENDPOINTS (what ReClaw exposes)
# ===========================================================================


@router.get("/mcp/server/status")
async def get_server_status(db: AsyncSession = Depends(get_db)):
    """Get current MCP server status and exposure summary."""
    from app.mcp.server import MCP_AVAILABLE
    from app.services.mcp_security import ensure_default_policy, get_exposure_summary

    policy = await ensure_default_policy(db)
    exposure = await get_exposure_summary(db)

    return {
        "enabled": settings.mcp_server_enabled,
        "port": settings.mcp_server_port,
        "mcp_library_installed": MCP_AVAILABLE,
        "exposure": exposure,
        "warning": (
            "MCP server is ENABLED. External agents can access ReClaw data "
            "according to the access policy."
        )
        if settings.mcp_server_enabled
        else "MCP server is disabled. No external access.",
    }


@router.post("/mcp/server/toggle")
async def toggle_server(data: ServerToggleRequest, db: AsyncSession = Depends(get_db)):
    """Enable or disable the MCP server.

    NOTE: This updates the in-memory setting. A full restart may be
    required for the transport layer to actually start/stop listening.
    """
    from app.mcp.server import MCP_AVAILABLE
    from app.services.mcp_security import ensure_default_policy

    if data.enabled and not MCP_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot enable MCP server: fastmcp library is not installed. "
                "Run: pip install fastmcp"
            ),
        )

    settings.mcp_server_enabled = data.enabled

    # Ensure a default policy exists
    if data.enabled:
        await ensure_default_policy(db)

    return {
        "enabled": settings.mcp_server_enabled,
        "port": settings.mcp_server_port,
        "warning": (
            "MCP server enabled. External agents can now connect to "
            f"port {settings.mcp_server_port}. Review the access policy."
        )
        if data.enabled
        else "MCP server disabled. External access revoked.",
    }


@router.get("/mcp/server/policy")
async def get_policy(db: AsyncSession = Depends(get_db)):
    """Get the current MCP access policy."""
    from app.services.mcp_security import ensure_default_policy

    policy = await ensure_default_policy(db)
    return policy.to_dict()


@router.patch("/mcp/server/policy")
async def update_policy(data: PolicyUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update the MCP access policy.

    Only provided fields are changed. SENSITIVE and HIGH-risk changes
    include warning messages in the response.
    """
    import json

    from app.services.mcp_security import TOOL_RISK_LEVELS, ensure_default_policy

    policy = await ensure_default_policy(db)
    warnings: list[str] = []

    # Apply updates for boolean fields
    field_risk_map = {
        "allow_list_skills": "low",
        "allow_list_projects": "low",
        "allow_get_deployment_status": "low",
        "allow_get_findings": "sensitive",
        "allow_search_memory": "sensitive",
        "allow_execute_skill": "high",
        "allow_create_project": "high",
        "allow_deploy_research": "high",
        "allow_project_resource": "sensitive",
        "allow_findings_resource": "sensitive",
        "allow_skills_resource": "low",
    }

    updates = data.model_dump(exclude_unset=True)

    for field_name, risk in field_risk_map.items():
        if field_name in updates:
            new_val = updates[field_name]
            setattr(policy, field_name, new_val)
            if new_val and risk in ("sensitive", "high"):
                tool_display = field_name.removeprefix("allow_")
                warnings.append(
                    f"WARNING: Enabled {risk.upper()}-risk permission '{tool_display}'. "
                    f"External agents can now access this capability."
                )

    # Limits
    if "allowed_project_ids" in updates and updates["allowed_project_ids"] is not None:
        policy.allowed_project_ids_json = json.dumps(updates["allowed_project_ids"])

    if "max_findings_per_request" in updates and updates["max_findings_per_request"] is not None:
        policy.max_findings_per_request = updates["max_findings_per_request"]

    if "max_skill_executions_per_hour" in updates and updates["max_skill_executions_per_hour"] is not None:
        policy.max_skill_executions_per_hour = updates["max_skill_executions_per_hour"]

    await db.commit()
    await db.refresh(policy)

    result = policy.to_dict()
    if warnings:
        result["warnings"] = warnings
    return result


@router.get("/mcp/server/audit")
async def get_audit(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get MCP audit log entries."""
    from app.services.mcp_security import get_audit_log

    entries = await get_audit_log(db, limit=limit, offset=offset)
    return {"entries": entries, "count": len(entries), "limit": limit, "offset": offset}


@router.get("/mcp/server/exposure")
async def get_exposure(db: AsyncSession = Depends(get_db)):
    """Get a summary of what is currently exposed via MCP."""
    from app.services.mcp_security import get_exposure_summary

    return await get_exposure_summary(db)


# ===========================================================================
# MCP CLIENT ENDPOINTS (connections to external MCP servers)
# ===========================================================================


@router.get("/mcp/clients")
async def list_clients(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all registered external MCP servers."""
    from app.services.mcp_client_manager import list_servers

    servers = await list_servers(db, active_only=active_only)
    return {"servers": servers, "count": len(servers)}


@router.post("/mcp/clients", status_code=201)
async def register_client(data: ClientRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new external MCP server."""
    from app.services.mcp_client_manager import register_server

    server = await register_server(
        db,
        name=data.name,
        url=data.url,
        transport=data.transport,
        headers=data.headers,
    )
    return server.to_dict()


# --- Fixed-path routes MUST come before {server_id} parameterized routes ---


@router.get("/mcp/clients/tools")
async def list_all_client_tools(db: AsyncSession = Depends(get_db)):
    """Aggregate cached tools from ALL active external MCP servers."""
    from app.services.mcp_client_manager import list_all_tools

    tools = await list_all_tools(db)
    return {"tools": tools, "count": len(tools)}


# --- Parameterized {server_id} routes ---


@router.delete("/mcp/clients/{server_id}", status_code=204)
async def unregister_client(server_id: str, db: AsyncSession = Depends(get_db)):
    """Remove an external MCP server from the registry."""
    from app.services.mcp_client_manager import unregister_server

    removed = await unregister_server(db, server_id)
    if not removed:
        raise HTTPException(status_code=404, detail="MCP server not found")


@router.post("/mcp/clients/{server_id}/discover")
async def discover_client_tools(server_id: str, db: AsyncSession = Depends(get_db)):
    """Connect to an external MCP server and discover its available tools."""
    from app.services.mcp_client_manager import MCP_CLIENT_AVAILABLE, discover_tools

    if not MCP_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="MCP client library not installed. Run: pip install mcp",
        )

    tools = await discover_tools(db, server_id)
    return {"server_id": server_id, "tools": tools, "count": len(tools)}


@router.get("/mcp/clients/{server_id}/tools")
async def get_client_tools(server_id: str, db: AsyncSession = Depends(get_db)):
    """Get cached tools for an external MCP server (from last discovery)."""
    import json

    from app.models.mcp_server_config import MCPServerConfig

    server = await db.get(MCPServerConfig, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    tools = json.loads(server.tools_json) if server.tools_json else []
    return {
        "server_id": server_id,
        "server_name": server.name,
        "tools": tools,
        "count": len(tools),
        "last_discovery_at": (
            server.last_discovery_at.isoformat() if server.last_discovery_at else None
        ),
    }


@router.post("/mcp/clients/{server_id}/call")
async def call_client_tool(
    server_id: str,
    data: ToolCallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Call a tool on an external MCP server."""
    from app.services.mcp_client_manager import MCP_CLIENT_AVAILABLE, call_tool

    if not MCP_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="MCP client library not installed. Run: pip install mcp",
        )

    result = await call_tool(db, server_id, data.tool_name, data.arguments)

    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    return {
        "server_id": server_id,
        "tool_name": data.tool_name,
        "result": result,
    }


@router.get("/mcp/clients/{server_id}/health")
async def check_client_health(server_id: str, db: AsyncSession = Depends(get_db)):
    """Check connectivity to an external MCP server."""
    from app.services.mcp_client_manager import health_check

    result = await health_check(db, server_id)
    return result
