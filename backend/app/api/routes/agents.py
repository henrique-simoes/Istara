"""Agent management, A2A messaging, and orchestrator API routes."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path


def _get_version() -> str:
    try:
        vf = Path(__file__).resolve().parents[3] / "VERSION"
        return vf.read_text().strip() if vf.exists() else "dev"
    except Exception:
        return "dev"

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import meta_orchestrator
from app.agents.ux_eval_agent import ux_eval_agent
from app.agents.user_sim_agent import user_sim_agent
from app.config import settings
from app.core.improvement_governance import improvement_governance
from app.core.permissions import get_active_project_or_404, require_project_access
from app.core.security_middleware import require_admin_from_request
from app.api.agent_project_scope import (
    agent_project_id,
    clean_project_id,
    filter_agent_dicts_for_project,
    filter_work_log,
    is_team_non_admin,
    redact_global_agent_state_for_project_view,
    require_agent_by_id,
    require_agent_collection_scope,
    require_project_owned_agent,
)
from app.models.database import get_db
from app.services import agent_service, a2a

logger = logging.getLogger(__name__)

router = APIRouter()

AVATAR_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_SAFE_AVATAR_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _avatar_filename(agent_id: str, ext: str) -> str:
    safe_id = _SAFE_AVATAR_ID_RE.sub("_", agent_id).strip("_")[:80] or "agent"
    digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()[:12]
    return f"{safe_id}-{digest}{ext}"


async def _read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Avatar exceeds maximum size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="Avatar file is empty")
    return b"".join(chunks)


def _resolve_avatar_path(avatar_path: str) -> Path:
    root = Path(settings.agent_avatars_dir).resolve()
    candidate = Path(avatar_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Avatar path is outside avatar storage")
    return resolved


# ───── Agent CRUD ─────


class CreateAgentRequest(BaseModel):
    name: str
    role: str = "custom"
    system_prompt: str = ""
    capabilities: list[str] | None = None
    heartbeat_interval: int = 60
    project_id: str | None = None


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    capabilities: list[str] | None = None
    heartbeat_interval: int | None = None
    state: str | None = None
    is_active: bool | None = None


@router.get("/agents")
async def list_agents(
    request: Request,
    include_system: bool = True,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List agents — universal agents are always included, project-scoped
    agents are filtered to the given project_id."""
    scoped_project_id = await require_agent_collection_scope(db, request, project_id)
    agents = await agent_service.list_agents(db, include_system)
    return {"agents": filter_agent_dicts_for_project(agents, scoped_project_id, request)}


@router.get("/agents/capacity")
async def check_capacity():
    """Check hardware capacity for creating another agent."""
    return await agent_service.check_capacity()


@router.get("/agents/heartbeat/status")
async def heartbeat_status(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get heartbeat status for agents visible in one project, or all for admins."""
    scoped_project_id = await require_agent_collection_scope(db, request, project_id)
    agents = await agent_service.list_agents(db)
    agents = filter_agent_dicts_for_project(agents, scoped_project_id, request)
    return {
        "agents": [
            {
                "id": a["id"],
                "name": a["name"],
                "heartbeat_status": a["heartbeat_status"],
                "last_heartbeat_at": a["last_heartbeat_at"],
                "state": a["state"],
            }
            for a in agents
        ]
    }


@router.get("/agents/a2a/log")
async def get_a2a_log(
    request: Request,
    limit: int = 100,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get the A2A message log for one authorized project."""
    await require_project_access(db, request, project_id, min_role="viewer")
    messages = await a2a.get_full_log(db, limit, project_id=project_id)
    return {"messages": messages}


@router.get("/agents/status")
async def get_orchestrator_status(request: Request):
    """Get full orchestrator status."""
    require_admin_from_request(request)
    return meta_orchestrator.get_status()


@router.get("/agents/log/recent")
async def get_agent_log(
    request: Request,
    agent_id: str | None = None,
    limit: int = 50,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    scoped_project_id = await require_agent_collection_scope(db, request, project_id)
    if agent_id and (scoped_project_id or is_team_non_admin(request)):
        await require_agent_by_id(db, request, agent_id, project_id=scoped_project_id)
    log = meta_orchestrator.get_work_log(limit=limit)
    return {
        "log": filter_work_log(
            log,
            project_id=scoped_project_id,
            agent_id=agent_id,
            limit=limit,
        )
    }


@router.post("/agents", status_code=201)
async def create_agent(
    data: CreateAgentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user agent with full persona file support."""
    scoped_project_id = clean_project_id(data.project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role="project_admin")
    agent = await agent_service.create_agent(
        db,
        name=data.name,
        role=data.role,
        system_prompt=data.system_prompt,
        capabilities=data.capabilities,
        heartbeat_interval=data.heartbeat_interval,
        scope="project",
        project_id=scoped_project_id,
    )

    # Auto-create persona MD files for the custom agent so it can
    # participate in the self-evolution pipeline (same as system agents)
    try:
        from app.core.self_evolution import self_evolution
        await self_evolution.create_persona_for_custom_agent(
            agent["id"], data.name, data.system_prompt
        )
    except Exception:
        pass  # Non-critical — agent still works via DB system_prompt

    # Auto-scaffold persona files for the new agent
    try:
        from app.core.agent_identity import scaffold_persona
        scaffold_persona(
            agent_id=agent["id"],
            name=data.name,
            role=data.role or "custom",
            system_prompt=data.system_prompt or "",
            capabilities=data.capabilities or [],
        )
    except Exception as e:
        logger.warning(f"Persona scaffold failed: {e}")

    try:
        from app.api.websocket import manager as ws_manager
        await ws_manager.broadcast("agent_created", {**agent, "project_id": scoped_project_id})
    except Exception:
        pass
    # Start the custom agent's work loop
    try:
        from app.agents.custom_worker import start_custom_agent
        await start_custom_agent(agent["id"], agent["name"])
    except Exception:
        pass
    return agent


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific agent's full details."""
    agent = await require_agent_by_id(db, request, agent_id, project_id=project_id)
    return redact_global_agent_state_for_project_view(agent.to_dict(), request)


@router.patch("/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    data: UpdateAgentRequest,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent's configuration."""
    await require_project_owned_agent(db, request, agent_id, project_id)
    updates = data.model_dump(exclude_unset=True)
    if "heartbeat_interval" in updates:
        updates["heartbeat_interval_seconds"] = updates.pop("heartbeat_interval")
    agent = await agent_service.update_agent(db, agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Soft-delete a project-owned agent from the active project."""
    await require_project_owned_agent(db, request, agent_id, project_id)
    # Stop custom agent worker if running
    try:
        from app.agents.custom_worker import stop_custom_agent
        await stop_custom_agent(agent_id)
    except Exception:
        pass
    if not await agent_service.delete_agent(db, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found or is a system agent")


@router.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    await require_project_owned_agent(db, request, agent_id, project_id)
    from app.models.agent import AgentState
    if not await agent_service.set_agent_state(db, agent_id, AgentState.PAUSED):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "paused"}


@router.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    await require_project_owned_agent(db, request, agent_id, project_id)
    from app.models.agent import AgentState
    if not await agent_service.set_agent_state(db, agent_id, AgentState.IDLE):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "resumed"}


@router.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Reset an agent from ERROR state back to IDLE, clearing error counters."""
    await require_project_owned_agent(db, request, agent_id, project_id)
    from app.models.agent import AgentState, HeartbeatStatus
    from app.models.agent import Agent

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.state = AgentState.IDLE
    agent.heartbeat_status = HeartbeatStatus.HEALTHY
    agent.error_count = 0
    if hasattr(agent, "consecutive_failures"):
        agent.consecutive_failures = 0
    await db.commit()
    return {"status": "restarted", "agent_id": agent_id}


# ───── Scope & Promotion ─────


@router.post("/agents/{agent_id}/set-scope")
async def set_agent_scope(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Set an agent's scope to 'universal' or 'project'.
    Promoting to universal requires admin role in team mode."""
    require_admin_from_request(request)
    from app.models.agent import Agent

    body = await request.json()
    new_scope = str(body.get("scope") or "")
    project_id = str(body.get("project_id") or "")

    if new_scope not in {"universal", "project"}:
        raise HTTPException(status_code=422, detail="scope must be 'universal' or 'project'")
    if new_scope == "project" and not project_id:
        raise HTTPException(status_code=422, detail="project_id is required for project-scoped agents")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # System agents are always universal
    if agent.is_system:
        raise HTTPException(status_code=400, detail="System agents are always universal")

    agent.scope = new_scope
    agent.project_id = project_id if new_scope == "project" else ""
    await db.commit()
    return {"agent_id": agent_id, "scope": new_scope, "project_id": agent.project_id}


@router.post("/agents/{agent_id}/request-promotion")
async def request_promotion(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Submit a request to promote a project-scoped agent to universal.
    Creates a notification for admins to review."""
    agent = await require_agent_by_id(
        db, request, agent_id, project_id=project_id, min_role="researcher"
    )

    if agent.scope == "universal":
        return {"status": "already_universal"}

    # Create a notification for admins
    from app.models.notification import Notification
    import uuid
    notif = Notification(
        id=str(uuid.uuid4()),
        type="agent_promotion_request",
        title=f"Agent Promotion Request: {agent.name}",
        message=f"A user has requested that agent '{agent.name}' be promoted from project scope to universal scope.",
        category="agent_promotion",
        severity="info",
        agent_id=agent_id,
        action_type="review_agent_promotion",
        action_target=agent_id,
    )
    db.add(notif)
    await db.commit()
    return {"status": "requested", "agent_id": agent_id}


# ───── Avatar ─────


@router.post("/agents/{agent_id}/avatar")
async def upload_avatar(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an avatar image for an agent."""
    await require_project_owned_agent(db, request, agent_id, project_id)

    ext = AVATAR_CONTENT_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Avatar must be PNG, JPEG, WebP, or GIF")

    content = await _read_upload_with_limit(file, settings.avatar_max_bytes)
    filename = _avatar_filename(agent_id, ext)
    avatar_dir = Path(settings.agent_avatars_dir).resolve()
    avatar_dir.mkdir(parents=True, exist_ok=True)
    dest = avatar_dir / filename
    dest.write_bytes(content)

    await agent_service.update_agent(db, agent_id, {"avatar_path": str(dest)})
    return {"avatar_path": str(dest)}


@router.get("/agents/{agent_id}/avatar")
async def get_avatar(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Serve an agent's avatar image."""
    agent = await require_agent_by_id(db, request, agent_id, project_id=project_id)
    serialized = agent.to_dict()
    if not serialized.get("avatar_path"):
        raise HTTPException(status_code=404, detail="No avatar found")
    path = _resolve_avatar_path(serialized["avatar_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Avatar file missing")
    return FileResponse(path)


# ───── Agent Identity (Persona MD Files) ─────


@router.get("/agents/{agent_id}/identity")
async def get_identity(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get an agent's full identity from its persona MD files."""
    from app.core.agent_identity import (
        load_agent_identity,
        get_agent_display_name,
        IDENTITY_FILES,
        persona_file_path,
    )

    await require_agent_by_id(db, request, agent_id, project_id=project_id)

    display_name = get_agent_display_name(agent_id)
    identity = load_agent_identity(agent_id)

    # Load individual files for display
    files = {}
    for filename in IDENTITY_FILES:
        filepath = persona_file_path(agent_id, filename)
        if filepath.exists():
            files[filename] = filepath.read_text(encoding="utf-8")

    return {
        "agent_id": agent_id,
        "display_name": display_name,
        "has_persona": bool(identity),
        "identity_length": len(identity),
        "files": files,
    }


@router.put("/agents/{agent_id}/identity")
async def update_identity(agent_id: str, data: dict, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Update an agent's local persona overlay files."""
    await require_project_owned_agent(db, request, agent_id, project_id)
    from app.core.agent_identity import (
        IDENTITY_FILES,
        load_agent_identity,
        persona_file_path,
        writeable_persona_path,
    )

    files = data.get("files", {})
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file names
    for filename in files:
        if filename not in IDENTITY_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file: {filename}. Allowed: {IDENTITY_FILES}",
            )

    source_write = bool(data.get("source", False))

    for filename, content in files.items():
        try:
            filepath = writeable_persona_path(agent_id, filename, source=source_write)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

    # Clear cache so changes take effect immediately
    try:
        load_agent_identity.cache_clear()
    except Exception:
        pass

    # Reload and return updated identity
    identity = load_agent_identity(agent_id)
    updated_files = {}
    for filename in IDENTITY_FILES:
        filepath = persona_file_path(agent_id, filename)
        if filepath.exists():
            updated_files[filename] = filepath.read_text(encoding="utf-8")

    return {
        "agent_id": agent_id,
        "write_scope": "source" if source_write else "runtime_overlay",
        "has_persona": bool(identity),
        "identity_length": len(identity),
        "files": updated_files,
    }


@router.get("/agents/personas/list")
async def list_personas(request: Request):
    """List all agents that have persona directories."""
    require_admin_from_request(request)
    from app.core.agent_identity import list_agent_personas, get_agent_display_name
    personas = list_agent_personas()
    return {
        "personas": [
            {"agent_id": p, "display_name": get_agent_display_name(p) or p}
            for p in personas
        ]
    }


# ───── Agent Learnings ─────


@router.get("/agents/{agent_id}/learnings")
async def get_learnings(
    agent_id: str,
    request: Request,
    category: str | None = None,
    limit: int = 20,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get an agent's structured learnings."""
    from app.core.agent_learning import agent_learning
    scoped_project_id = clean_project_id(project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    agent = await require_agent_by_id(
        db,
        request,
        agent_id,
        project_id=scoped_project_id,
    )
    if is_team_non_admin(request) and not agent_project_id(agent):
        return {"agent_id": agent_id, "learnings": []}
    learnings = await agent_learning.get_relevant_learnings(
        agent_id,
        category=category,
        limit=limit,
        project_id=scoped_project_id,
    )
    return {"agent_id": agent_id, "project_id": scoped_project_id, "learnings": learnings}


# ───── Self-Evolution ─────


async def _require_self_evolution_project_scope(
    db: AsyncSession, request: Request, project_id: str | None, *, min_role: str = "project_admin",
) -> str:
    require_admin_from_request(request)
    scoped_project_id = clean_project_id(project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    project = await get_active_project_or_404(
        db,
        request,
        scoped_project_id,
        min_role=min_role,
    )
    return project.id


@router.get("/agents/{agent_id}/evolution/candidates")
async def get_evolution_candidates(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Scan an agent's learnings for patterns ready for promotion."""
    scoped_project_id = await _require_self_evolution_project_scope(db, request, project_id)
    await require_agent_by_id(db, request, agent_id, project_id=scoped_project_id)
    from app.core.self_evolution import self_evolution
    candidates = await self_evolution.scan_for_promotions(agent_id, project_id=scoped_project_id)
    return {"agent_id": agent_id, "project_id": scoped_project_id, "candidates": candidates, "count": len(candidates)}


@router.post("/agents/{agent_id}/evolution/promote/{learning_id}")
async def promote_learning(
    agent_id: str, learning_id: int, request: Request, target_file: str | None = None,
    project_id: str | None = None, db: AsyncSession = Depends(get_db),
):
    """Promote a specific learning into the agent's persona files."""
    scoped_project_id = await _require_self_evolution_project_scope(db, request, project_id)
    await require_agent_by_id(db, request, agent_id, project_id=scoped_project_id)
    from app.core.self_evolution import self_evolution
    result = await self_evolution.promote_learning(agent_id, learning_id, target_file, project_id=scoped_project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Promotion failed"))
    try:
        await improvement_governance.register_self_evolution_promotion(result, applied=True)
    except Exception:
        pass
    return result


@router.post("/agents/{agent_id}/evolution/auto")
async def auto_evolve(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Run the full self-evolution cycle (auto-promote mature patterns)."""
    scoped_project_id = await _require_self_evolution_project_scope(db, request, project_id)
    await require_agent_by_id(db, request, agent_id, project_id=scoped_project_id)
    from app.core.self_evolution import self_evolution
    promotions = await self_evolution.auto_evolve(agent_id, project_id=scoped_project_id)
    for promotion in promotions:
        try:
            await improvement_governance.register_self_evolution_promotion(promotion, applied=True)
        except Exception:
            pass
    return {
        "agent_id": agent_id,
        "project_id": scoped_project_id,
        "promotions_applied": len(promotions),
        "promotions": promotions,
    }


@router.get("/agents/evolution/scan")
async def scan_all_evolution(request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Scan all agents for promotable learnings."""
    scoped_project_id = await _require_self_evolution_project_scope(db, request, project_id)
    from app.core.self_evolution import self_evolution
    results = await self_evolution.scan_all_agents(project_id=scoped_project_id)
    total = sum(len(v) for v in results.values())
    return {"project_id": scoped_project_id, "agents_with_candidates": len(results), "total_candidates": total, "results": results}


# ───── Agent Creation Proposals (Memento-Skills) ─────


class RejectProposalRequest(BaseModel):
    reason: str = ""


async def _require_agent_proposal_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: str = "project_admin",
) -> str:
    scoped_project_id = clean_project_id(project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


@router.get("/agents/creation-proposals/pending")
async def get_pending_proposals(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all pending agent creation proposals."""
    scoped_project_id = await _require_agent_proposal_project_scope(db, request, project_id)
    from app.core.agent_factory import AgentFactory

    factory = AgentFactory()
    proposals = factory.get_pending_proposals(project_id=scoped_project_id)
    return {"proposals": proposals, "count": len(proposals)}


@router.get("/agents/creation-proposals/all")
async def get_all_proposals(
    request: Request,
    limit: int = 20,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all agent creation proposals (any status)."""
    scoped_project_id = await _require_agent_proposal_project_scope(db, request, project_id)
    from app.core.agent_factory import AgentFactory

    factory = AgentFactory()
    proposals = factory.get_all_proposals(limit, project_id=scoped_project_id)
    return {"proposals": proposals, "count": len(proposals)}


@router.post("/agents/creation-proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve a proposal — creates the agent in DB, scaffolds persona, starts worker."""
    scoped_project_id = await _require_agent_proposal_project_scope(
        db,
        request,
        project_id,
    )
    from app.core.agent_factory import AgentFactory

    factory = AgentFactory()
    proposal = factory.approve_proposal(proposal_id, project_id=scoped_project_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")

    # Create the agent in the database
    agent = await agent_service.create_agent(
        db,
        name=proposal["proposed_name"],
        role="custom",
        system_prompt=proposal["proposed_system_prompt"],
        capabilities=None,
        heartbeat_interval=60,
        scope="project",
        project_id=scoped_project_id,
        specialties=proposal["proposed_specialties"],
    )

    # Scaffold persona MD files from the proposal's CORE.md
    try:
        from app.core.self_evolution import self_evolution

        await self_evolution.create_persona_for_custom_agent(
            agent["id"],
            proposal["proposed_name"],
            proposal["proposed_system_prompt"],
        )
    except Exception:
        pass

    try:
        from app.core.agent_identity import scaffold_persona

        scaffold_persona(
            agent_id=agent["id"],
            name=proposal["proposed_name"],
            role="custom",
            system_prompt=proposal["proposed_system_prompt"],
            capabilities=[],
        )
    except Exception as e:
        logger.warning(f"Persona scaffold failed for proposal {proposal_id}: {e}")

    # Start the custom agent's work loop
    try:
        from app.agents.custom_worker import start_custom_agent

        await start_custom_agent(agent["id"], agent["name"])
    except Exception:
        pass

    # Broadcast
    try:
        from app.api.websocket import manager as ws_manager

        await ws_manager.broadcast(
            "agent_created_from_proposal",
            {"proposal_id": proposal_id, "project_id": scoped_project_id, "agent": agent},
        )
    except Exception:
        pass

    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_agent_factory",
            source_id=proposal_id,
            project_id=scoped_project_id,
        )
        if governance and governance.status in {"draft", "proposed"}:
            await improvement_governance.approve_proposal(
                governance.id,
                reviewer_id="agents-ui",
                note="Approved via Agent Creation UI",
            )
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_agent_factory",
            source_id=proposal_id,
            project_id=scoped_project_id,
        )
        if governance and governance.status == "approved":
            await improvement_governance.apply_proposal(
                governance.id,
                actor_id="agents-ui",
                evidence={
                    "agent_id": agent.get("id"),
                    "agent_name": agent.get("name"),
                    "project_id": scoped_project_id,
                },
            )
    except Exception:
        pass

    return {
        "status": "approved",
        "proposal": proposal,
        "agent": agent,
    }


@router.post("/agents/creation-proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    request: Request,
    data: RejectProposalRequest | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending agent creation proposal."""
    scoped_project_id = await _require_agent_proposal_project_scope(
        db,
        request,
        project_id,
    )
    from app.core.agent_factory import AgentFactory

    factory = AgentFactory()
    reason = data.reason if data else ""
    proposal = factory.reject_proposal(
        proposal_id,
        reason,
        project_id=scoped_project_id,
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")

    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_agent_factory",
            source_id=proposal_id,
            project_id=scoped_project_id,
        )
        if governance and governance.status in {"draft", "proposed", "approved"}:
            await improvement_governance.reject_proposal(
                governance.id,
                reviewer_id="agents-ui",
                reason=reason,
            )
    except Exception:
        pass

    return {"status": "rejected", "proposal": proposal}


# ───── Prompt Compression ─────


@router.get("/agents/{agent_id}/prompt/stats")
async def get_prompt_stats(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get compression stats for an agent's system prompt."""
    from app.core.agent_identity import load_agent_identity, _estimate_tokens
    from app.core.prompt_compressor import compress_prompt

    await require_agent_by_id(db, request, agent_id, project_id=project_id)

    full = load_agent_identity(agent_id)
    if not full:
        raise HTTPException(status_code=404, detail="No persona files found")

    compressed = compress_prompt(full, max_tokens=2048)
    return {
        "agent_id": agent_id,
        "full_chars": len(full),
        "full_tokens": _estimate_tokens(full),
        "compressed_chars": len(compressed),
        "compressed_tokens": _estimate_tokens(compressed),
        "compression_ratio": round(len(compressed) / len(full), 3) if full else 0,
    }


class PromptComposeRequest(BaseModel):
    query: str
    max_tokens: int | None = None
    use_embeddings: bool = False  # Default to keyword for fast testing
    top_k: int = 8


@router.post("/agents/{agent_id}/prompt/compose")
async def compose_prompt_for_query(
    agent_id: str,
    data: PromptComposeRequest,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Compose a query-aware prompt via Prompt RAG and return diagnostic info.

    This endpoint reveals which persona sections are selected for a given
    query — critical for verifying that small models receive relevant
    context rather than the entire persona.
    """
    from app.core.prompt_rag import (
        compose_dynamic_prompt,
        index_agent_sections,
        _extract_identity_anchor,
        _tokenize,
        _keyword_similarity,
    )
    from app.core.agent_identity import load_agent_identity, _estimate_tokens

    await require_agent_by_id(db, request, agent_id, project_id=project_id)

    full_identity = load_agent_identity(agent_id)
    if not full_identity:
        raise HTTPException(status_code=404, detail="No persona files found")

    # Compose the dynamic prompt
    composed = await compose_dynamic_prompt(
        agent_id,
        query=data.query,
        max_tokens=data.max_tokens,
        use_embeddings=data.use_embeddings,
        top_k=data.top_k,
    )

    # Get section-level details for diagnostics
    all_sections = index_agent_sections(agent_id)
    query_tokens = _tokenize(data.query)
    section_scores = []
    for section in all_sections:
        score = _keyword_similarity(query_tokens, section)
        section_scores.append({
            "header": section.header,
            "filename": section.filename,
            "score": round(score, 4),
            "tokens": section.token_estimate,
            "included": section.header in composed or section.content[:80] in composed,
        })

    section_scores.sort(key=lambda x: x["score"], reverse=True)

    anchor = _extract_identity_anchor(agent_id)

    return {
        "agent_id": agent_id,
        "query": data.query,
        "full_tokens": _estimate_tokens(full_identity),
        "composed_tokens": _estimate_tokens(composed),
        "anchor_tokens": _estimate_tokens(anchor),
        "savings_percent": round(
            (1 - len(composed) / len(full_identity)) * 100, 1
        ) if full_identity else 0,
        "total_sections": len(all_sections),
        "sections_included": sum(1 for s in section_scores if s["included"]),
        "section_scores": section_scores[:20],  # Top 20 for diagnostics
        "composed_prompt_preview": composed[:500] + "..." if len(composed) > 500 else composed,
        "identity_preserved": bool(anchor and anchor[:100] in composed[:200]),
    }


# ───── Agent Memory ─────


@router.get("/agents/{agent_id}/memory")
async def get_memory(
    agent_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    agent = await require_agent_by_id(db, request, agent_id, project_id=project_id)
    if is_team_non_admin(request) and not agent_project_id(agent):
        return {"agent_id": agent_id, "memory": {}}
    memory = await agent_service.get_agent_memory(db, agent_id)
    return {"agent_id": agent_id, "memory": memory}


@router.patch("/agents/{agent_id}/memory")
async def update_memory(agent_id: str, updates: dict, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    await require_project_owned_agent(db, request, agent_id, project_id)
    memory = await agent_service.update_agent_memory(db, agent_id, updates)
    return {"agent_id": agent_id, "memory": memory}


# ───── A2A Messaging ─────


class A2AMessageRequest(BaseModel):
    to_agent_id: str | None = None
    message_type: str = "consult"
    content: str
    project_id: str | None = None
    metadata: dict | None = None


@router.get("/agents/{agent_id}/messages")
async def get_messages(
    agent_id: str,
    request: Request,
    limit: int = 50,
    unread_only: bool = False,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await require_project_access(db, request, project_id, min_role="viewer")
    await require_agent_by_id(db, request, agent_id, project_id=project_id)
    messages = await a2a.get_messages(db, agent_id, limit, unread_only, project_id=project_id)
    return {"messages": messages}


@router.post("/agents/{agent_id}/messages")
async def send_message(
    agent_id: str,
    data: A2AMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_admin_from_request(request)
    metadata = dict(data.metadata or {})
    project_id = data.project_id or metadata.get("project_id") or metadata.get("projectId")
    if not isinstance(project_id, str) or not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")
    project_id = project_id.strip()
    await require_project_access(db, request, project_id, min_role="researcher")
    await require_agent_by_id(db, request, agent_id, project_id=project_id)
    if data.to_agent_id:
        await require_agent_by_id(db, request, data.to_agent_id, project_id=project_id)
    metadata["project_id"] = project_id
    try:
        msg = await a2a.send_message(
            db,
            from_agent_id=agent_id,
            to_agent_id=data.to_agent_id,
            message_type=data.message_type,
            content=data.content,
            metadata=metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return msg


# ───── Audit Agents ─────


@router.get("/audit/ux/latest")
async def get_ux_eval(request: Request):
    require_admin_from_request(request)
    report = ux_eval_agent.get_latest_report()
    if not report:
        return {"status": "no_reports", "message": "No UX evaluation has run yet."}
    return report


@router.post("/audit/ux/run")
async def trigger_ux_eval(request: Request):
    require_admin_from_request(request)
    return await ux_eval_agent.run_evaluation()


@router.get("/audit/sim/latest")
async def get_sim_report(request: Request):
    require_admin_from_request(request)
    report = user_sim_agent.get_latest_report()
    if not report:
        return {"status": "no_reports", "message": "No simulation has run yet."}
    return report


@router.post("/audit/sim/run")
async def trigger_simulation(request: Request):
    require_admin_from_request(request)
    return await user_sim_agent.run_simulation()


# ───── Agent Export / Transfer ─────


class AgentExportData(BaseModel):
    name: str
    role: str
    system_prompt: str
    capabilities: list[str]
    heartbeat_interval: int
    memory: dict
    project_id: str | None = None


@router.get("/agents/{agent_id}/export")
async def export_agent(agent_id: str, request: Request, project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Export an agent's configuration as a portable JSON config."""
    agent = await require_project_owned_agent(db, request, agent_id, project_id)
    serialized = agent.to_dict()
    return {
        "istara_version": _get_version(),
        "type": "agent_config",
        "agent": {
            "name": serialized["name"],
            "role": serialized["role"],
            "system_prompt": serialized["system_prompt"],
            "capabilities": serialized["capabilities"],
            "heartbeat_interval": serialized["heartbeat_interval_seconds"],
            "memory": serialized["memory"],
        },
    }


@router.post("/agents/import")
async def import_agent(data: AgentExportData, request: Request, db: AsyncSession = Depends(get_db)):
    """Import an agent from an exported config."""
    scoped_project_id = clean_project_id(data.project_id)
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role="project_admin")
    agent = await agent_service.create_agent(
        db,
        name=data.name,
        role=data.role,
        system_prompt=data.system_prompt,
        capabilities=data.capabilities,
        heartbeat_interval=data.heartbeat_interval,
        scope="project",
        project_id=scoped_project_id,
    )
    # Apply memory if provided
    if data.memory:
        await agent_service.update_agent_memory(db, agent["id"], data.memory)
        agent = await agent_service.get_agent(db, agent["id"])
    return agent
