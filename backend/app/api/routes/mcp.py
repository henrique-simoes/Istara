"""MCP management API -- server exposure control + client registry.

MCP Server endpoints manage what Istara exposes to external agents.
MCP Client endpoints manage connections TO external MCP servers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.env_persistence import persist_env_value
from app.core.permissions import ProjectRole, require_project_access
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db
from app.models.mcp_server_config import MCPServerConfig

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
    # Backward-compatible UI shape.
    tools: dict | None = None
    resources: dict | None = None
    limits: dict | None = None


class ClientRegisterRequest(BaseModel):
    name: str
    url: str
    transport: str = "http"
    headers: dict | None = None
    project_id: str | None = None


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


async def _require_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: ProjectRole = "viewer",
) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    from app.models.project import Project

    project = await db.get(Project, scoped_project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def _get_project_client_or_404(
    db: AsyncSession,
    request: Request,
    server_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole = "project_admin",
) -> tuple[str, MCPServerConfig]:
    scoped_project_id = await _require_project_scope(
        db, request, project_id, min_role=min_role
    )
    server = await db.get(MCPServerConfig, server_id)
    if not server or server.project_id != scoped_project_id:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return scoped_project_id, server


# ===========================================================================
# MCP SERVER ENDPOINTS (what Istara exposes)
# ===========================================================================


@router.get("/mcp/server/status")
async def get_server_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get current MCP server status and exposure summary."""
    require_admin_from_request(request)
    from app.mcp.server import MCP_AVAILABLE, get_runtime_status
    from app.services.mcp_security import ensure_default_policy, get_exposure_summary

    await ensure_default_policy(db)
    exposure = await get_exposure_summary(db)
    runtime = get_runtime_status()
    return {
        "enabled": settings.mcp_server_enabled,
        "configured_enabled": runtime["configured_enabled"],
        "serving": runtime["serving"],
        "restart_required": runtime["restart_required"],
        "lifecycle_state": runtime["lifecycle_state"],
        "port": settings.mcp_server_port,
        "mcp_library_installed": MCP_AVAILABLE,
        "exposure": exposure,
        "warning": (
            "MCP server is configured as ENABLED, but this API process is not "
            "serving the FastMCP transport yet. Restart/start the MCP entrypoint "
            "for external agents to connect."
        )
        if runtime["restart_required"]
        else (
            "MCP server is ENABLED and serving. External agents can access Istara "
            "data according to the access policy."
        )
        if runtime["serving"]
        else "MCP server is disabled. No external access.",
    }


@router.post("/mcp/server/toggle")
async def toggle_server(
    data: ServerToggleRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Enable or disable the MCP server. Admin only.

    NOTE: This updates the in-memory setting. A full restart may be
    required for the transport layer to actually start/stop listening.
    """
    require_admin_from_request(request)
    from app.mcp.server import MCP_AVAILABLE, get_runtime_status
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
    try:
        persist_env_value("MCP_SERVER_ENABLED", str(data.enabled).lower())
        persisted = True
    except Exception:
        persisted = False

    # Ensure a default policy exists
    if data.enabled:
        await ensure_default_policy(db)
    runtime = get_runtime_status()
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="mcp_integrations_and_aura_research",
            source_system="mcp_server",
            source_id=f"toggle:{str(data.enabled).lower()}",
            agent_id="mcp-server",
            summary="MCP server exposure setting changed.",
            evidence={
                "passed": True,
                "enabled": data.enabled,
                "serving": runtime["serving"],
                "restart_required": runtime["restart_required"],
                "persisted": persisted,
            },
            metrics_after={"enabled": data.enabled, "serving": runtime["serving"]},
            db=db,
        )
    except Exception:
        pass

    return {
        "enabled": settings.mcp_server_enabled,
        "configured_enabled": runtime["configured_enabled"],
        "serving": runtime["serving"],
        "restart_required": runtime["restart_required"],
        "lifecycle_state": runtime["lifecycle_state"],
        "port": settings.mcp_server_port,
        "persisted": persisted,
        "warning": (
            "MCP server configuration enabled. Start or restart the FastMCP "
            f"transport on port {settings.mcp_server_port} before external agents can connect."
        )
        if data.enabled
        else "MCP server disabled. External access revoked.",
    }


@router.get("/mcp/server/policy")
async def get_policy(request: Request, db: AsyncSession = Depends(get_db)):
    """Get the current MCP access policy."""
    require_admin_from_request(request)
    from app.services.mcp_security import ensure_default_policy

    policy = await ensure_default_policy(db)
    return policy.to_dict()


@router.patch("/mcp/server/policy")
async def update_policy(
    data: PolicyUpdateRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Update the MCP access policy. Admin only.

    Only provided fields are changed. SENSITIVE and HIGH-risk changes
    include warning messages in the response.
    """
    require_admin_from_request(request)
    import json

    from app.services.mcp_security import ensure_default_policy

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

    # Accept the grouped frontend shape in addition to explicit backend fields.
    tool_name_to_field = {
        "list_skills": "allow_list_skills",
        "list_projects": "allow_list_projects",
        "get_deployment_status": "allow_get_deployment_status",
        "get_findings": "allow_get_findings",
        "search_memory": "allow_search_memory",
        "execute_skill": "allow_execute_skill",
        "create_project": "allow_create_project",
        "deploy_research": "allow_deploy_research",
    }
    for tool_name, config in (updates.pop("tools", None) or {}).items():
        field_name = tool_name_to_field.get(tool_name)
        if field_name and isinstance(config, dict) and "allowed" in config:
            updates[field_name] = bool(config["allowed"])

    resource_name_to_field = {
        "project": "allow_project_resource",
        "findings": "allow_findings_resource",
        "skills": "allow_skills_resource",
    }
    for resource_name, config in (updates.pop("resources", None) or {}).items():
        field_name = resource_name_to_field.get(resource_name)
        if field_name and isinstance(config, dict) and "allowed" in config:
            updates[field_name] = bool(config["allowed"])

    limits = updates.pop("limits", None) or {}
    if isinstance(limits, dict):
        for key in (
            "allowed_project_ids",
            "max_findings_per_request",
            "max_skill_executions_per_hour",
        ):
            if key in limits:
                updates[key] = limits[key]

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

    if (
        "max_skill_executions_per_hour" in updates
        and updates["max_skill_executions_per_hour"] is not None
    ):
        policy.max_skill_executions_per_hour = updates["max_skill_executions_per_hour"]

    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="mcp_integrations_and_aura_research",
            source_system="mcp_policy",
            source_id="policy_update",
            agent_id="mcp-server",
            summary="MCP access policy was updated.",
            evidence={
                "passed": True,
                "updates": updates,
                "warnings": warnings,
            },
            metrics_after={"warning_count": len(warnings)},
            db=db,
        )
    except Exception:
        pass
    await db.commit()
    await db.refresh(policy)

    result = policy.to_dict()
    if warnings:
        result["warnings"] = warnings
    return result


@router.get("/mcp/server/audit")
async def get_audit(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get MCP audit log entries."""
    require_admin_from_request(request)
    from app.services.mcp_security import get_audit_log

    entries = await get_audit_log(db, limit=limit, offset=offset)
    return {"entries": entries, "count": len(entries), "limit": limit, "offset": offset}


@router.get("/mcp/server/exposure")
async def get_exposure(request: Request, db: AsyncSession = Depends(get_db)):
    """Get a summary of what is currently exposed via MCP."""
    require_admin_from_request(request)
    from app.services.mcp_security import get_exposure_summary

    return await get_exposure_summary(db)


# ===========================================================================
# MCP CLIENT ENDPOINTS (connections to external MCP servers)
# ===========================================================================


@router.get("/mcp/clients")
async def list_clients(
    request: Request,
    active_only: bool = False,
    project_id: str | None = Query(None, description="Filter by active project"),
    db: AsyncSession = Depends(get_db),
):
    """List registered external MCP servers for a project, or all for global admins."""
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    from app.services.mcp_client_manager import list_servers

    servers = await list_servers(db, active_only=active_only, project_id=scoped_project_id)
    return {"servers": servers, "count": len(servers)}


@router.post("/mcp/clients", status_code=201)
async def register_client(
    data: ClientRegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Register a new external MCP server."""
    project_id = await _require_project_scope(db, request, data.project_id, min_role="project_admin")
    from app.services.mcp_client_manager import register_server

    try:
        server = await register_server(
            db,
            name=data.name,
            url=data.url,
            transport=data.transport,
            headers=data.headers,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="mcp_integrations_and_aura_research",
            source_system="mcp_client",
            source_id=f"register:{server.id}",
            agent_id="mcp-client",
            summary="External MCP server registered.",
            evidence={
                "passed": True,
                "server_id": server.id,
                "project_id": project_id,
                "name": server.name,
                "transport": server.transport,
            },
        )
    except Exception:
        pass
    return server.to_dict()


# --- Fixed-path routes MUST come before {server_id} parameterized routes ---


@router.get("/mcp/clients/tools")
async def list_all_client_tools(
    request: Request,
    project_id: str | None = Query(None, description="Filter by active project"),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate cached tools from active external MCP servers."""
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    from app.services.mcp_client_manager import list_all_tools

    tools = await list_all_tools(db, project_id=scoped_project_id)
    return {"tools": tools, "count": len(tools)}


# --- Parameterized {server_id} routes ---


@router.delete("/mcp/clients/{server_id}", status_code=204)
async def unregister_client(
    server_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Remove an external MCP server from the registry. Admin only."""
    await _get_project_client_or_404(
        db, request, server_id, project_id, min_role="project_admin"
    )
    from app.services.mcp_client_manager import unregister_server

    removed = await unregister_server(db, server_id)
    if not removed:
        raise HTTPException(status_code=404, detail="MCP server not found")


@router.post("/mcp/clients/{server_id}/discover")
async def discover_client_tools(
    server_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Connect to an external MCP server and discover its available tools."""
    from app.services.mcp_client_manager import MCP_CLIENT_AVAILABLE, discover_tools

    scoped_project_id, server = await _get_project_client_or_404(
        db, request, server_id, project_id, min_role="project_admin"
    )

    if not MCP_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="MCP client library not installed. Run: pip install mcp",
        )

    tools = await discover_tools(db, server_id)
    await db.refresh(server)
    if server.health_status == "unhealthy":
        raise HTTPException(
            status_code=502,
            detail=f"Tool discovery failed for MCP server '{server.name}'",
        )
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="mcp_integrations_and_aura_research",
            source_system="mcp_client",
            source_id=f"discover:{server_id}",
            agent_id="mcp-client",
            summary="External MCP tool discovery completed.",
            evidence={
                "passed": True,
                "server_id": server_id,
                "project_id": scoped_project_id,
                "tool_count": len(tools),
                "health_status": server.health_status,
            },
            metrics_after={"tool_count": len(tools)},
        )
    except Exception:
        pass
    return {"server_id": server_id, "tools": tools, "count": len(tools)}


@router.get("/mcp/clients/{server_id}/tools")
async def get_client_tools(
    server_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Get cached tools for an external MCP server (from last discovery)."""
    server_project_id, server = await _get_project_client_or_404(
        db, request, server_id, project_id, min_role="project_admin"
    )
    import json

    tools = json.loads(server.tools_json) if server.tools_json else []
    return {
        "server_id": server_id,
        "project_id": server_project_id,
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
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Call a tool on an external MCP server."""
    scoped_project_id, _ = await _get_project_client_or_404(
        db, request, server_id, project_id, min_role="project_admin"
    )
    from app.services.mcp_client_manager import MCP_CLIENT_AVAILABLE, call_tool

    if not MCP_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="MCP client library not installed. Run: pip install mcp",
        )

    result = await call_tool(db, server_id, data.tool_name, data.arguments)

    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="mcp_integrations_and_aura_research",
            source_system="mcp_client",
            source_id=f"call:{server_id}:{data.tool_name}",
            agent_id="mcp-client",
            summary="External MCP tool call completed.",
            evidence={
                "passed": True,
                "server_id": server_id,
                "project_id": scoped_project_id,
                "tool_name": data.tool_name,
                "argument_keys": sorted((data.arguments or {}).keys()),
            },
        )
    except Exception:
        pass
    return {
        "server_id": server_id,
        "project_id": scoped_project_id,
        "tool_name": data.tool_name,
        "result": result,
    }


@router.get("/mcp/clients/{server_id}/health")
async def check_client_health(
    server_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Check connectivity to an external MCP server."""
    await _get_project_client_or_404(
        db, request, server_id, project_id, min_role="project_admin"
    )
    from app.services.mcp_client_manager import health_check

    result = await health_check(db, server_id)
    return result


# ---------------------------------------------------------------------------
# Featured MCP Servers — pre-configured servers for one-click connection
# ---------------------------------------------------------------------------


@router.get("/mcp/featured")
async def list_featured_servers(
    request: Request,
    project_id: str | None = Query(None, description="Active project for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List pre-configured MCP servers available for one-click connection."""
    await _require_project_scope(db, request, project_id, min_role="viewer")
    import json
    from pathlib import Path

    featured_file = Path(__file__).parent.parent.parent / "knowledge" / "featured_mcp_servers.json"
    if not featured_file.exists():
        return []
    try:
        data = json.loads(featured_file.read_text())
        return data.get("servers", [])
    except Exception:
        return []


@router.get("/mcp/featured/{server_id}")
async def get_featured_server(
    server_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get details for a featured MCP server."""
    await _require_project_scope(db, request, project_id, min_role="viewer")
    import json
    from pathlib import Path

    featured_file = Path(__file__).parent.parent.parent / "knowledge" / "featured_mcp_servers.json"
    if not featured_file.exists():
        raise HTTPException(status_code=404, detail="Featured servers not found")
    try:
        data = json.loads(featured_file.read_text())
        for server in data.get("servers", []):
            if server["id"] == server_id:
                return server
        raise HTTPException(status_code=404, detail=f"Featured server '{server_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConnectFeaturedRequest(BaseModel):
    env_vars: dict[str, str] = {}  # Optional API keys
    project_id: str | None = None


@router.post("/mcp/featured/{server_id}/connect", status_code=201)
async def connect_featured_server(
    server_id: str,
    body: ConnectFeaturedRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Quick-connect a featured MCP server to Istara's client registry.

    Creates a new MCP client config from the featured server's definition,
    optionally setting environment variables (API keys).
    """
    project_id = await _require_project_scope(db, request, body.project_id, min_role="project_admin")

    import json
    from pathlib import Path

    from app.services.mcp_client_manager import register_server

    featured_file = Path(__file__).parent.parent.parent / "knowledge" / "featured_mcp_servers.json"
    if not featured_file.exists():
        raise HTTPException(status_code=404, detail="Featured servers not found")

    data = json.loads(featured_file.read_text())
    featured = None
    for s in data.get("servers", []):
        if s["id"] == server_id:
            featured = s
            break
    if not featured:
        raise HTTPException(status_code=404, detail=f"Featured server '{server_id}' not found")

    # Register using HTTP URL (preferred for Istara's client manager)
    url = featured.get("http_url", "")
    if not url:
        raise HTTPException(
            status_code=400,
            detail=f"Featured server '{server_id}' has no HTTP URL. "
            f"Install with: pip install {featured.get('package', server_id)} "
            f"and run: {featured.get('http_command', '')}",
        )

    try:
        config = await register_server(
            db=db,
            name=featured["name"],
            url=url,
            transport="http",
            headers={"X-Featured-Server": server_id},
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "message": f"Connected to {featured['name']}",
        "server": config.to_dict()
        if hasattr(config, "to_dict")
        else {"id": str(config.id), "name": config.name},
        "setup_instructions": {
            "install": f"pip install {featured.get('package', server_id)}",
            "run": featured.get("http_command", ""),
            "env_vars": featured.get("env_vars", []),
        },
    }
