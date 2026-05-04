"""Skills management API — CRUD, versioning, self-improvement, execution, health monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent import agent
from app.core.improvement_governance import improvement_governance
from app.core.permissions import require_global_admin, require_project_access
from app.models.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.skills.skill_manager import skill_manager
from app.skills.registry import registry

router = APIRouter()


class SkillExecuteRequest(BaseModel):
    project_id: str
    files: list[str] = []
    parameters: dict = {}
    user_context: str = ""


class SkillPlanRequest(BaseModel):
    project_id: str
    user_context: str = ""


class SkillCreateRequest(BaseModel):
    name: str
    display_name: str
    description: str
    phase: str
    skill_type: str
    plan_prompt: str = ""
    execute_prompt: str = ""
    output_schema: str = ""


class SkillUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    plan_prompt: str | None = None
    execute_prompt: str | None = None
    output_schema: str | None = None
    enabled: bool | None = None
    changelog_entry: str = ""


# --- Skill CRUD ---

@router.get("/skills")
async def list_skills(phase: str | None = None):
    """List all skill definitions with optional phase filter."""
    if phase:
        skills = skill_manager.list_by_phase(phase)
    else:
        skills = skill_manager.list_all()

    return {
        "skills": [s.to_dict() for s in skills],
        "count": len(skills),
        "by_phase": {
            p: len(skill_manager.list_by_phase(p))
            for p in ["discover", "define", "develop", "deliver"]
        },
    }


# --- Routes with fixed paths MUST come before {name} parameterized routes ---

@router.get("/skills/health/all")
async def get_all_health():
    """Get health scores for all skills."""
    return {"skills": skill_manager.get_all_health()}


@router.get("/skills/proposals/pending")
async def get_pending_proposals():
    """Get all pending skill improvement proposals."""
    return {
        "proposals": [p.to_dict() for p in skill_manager.get_pending_proposals()],
        "count": len(skill_manager.get_pending_proposals()),
    }


@router.get("/skills/proposals/all")
async def get_all_proposals(limit: int = 50):
    """Get all proposals (pending, approved, rejected)."""
    return {
        "proposals": [p.to_dict() for p in skill_manager.get_all_proposals(limit)],
    }


# --- Skill Creation Proposals ---

@router.get("/skills/creation-proposals/pending")
async def get_pending_creation_proposals():
    """Get all pending skill creation proposals."""
    proposals = skill_manager.get_pending_creation_proposals()
    return {
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals),
    }


@router.get("/skills/creation-proposals/all")
async def get_all_creation_proposals(limit: int = 20):
    """Get all skill creation proposals (pending, approved, rejected)."""
    proposals = skill_manager.get_all_creation_proposals(limit)
    return {
        "proposals": [p.to_dict() for p in proposals],
    }


@router.post("/skills/creation-proposals/{proposal_id}/approve")
async def approve_creation_proposal(proposal_id: str, request: Request):
    """Approve a skill creation proposal — writes definition file and registers skill."""
    require_global_admin(request)
    proposal = next(
        (p for p in skill_manager.get_pending_creation_proposals() if p.id == proposal_id),
        None,
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")

    if not proposal.test_result:
        verification = await skill_manager.verify_skill_proposal(proposal_id)
        if not verification.get("passed"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Creation proposal failed verification and was not approved",
                    "verification": verification,
                },
            )

    result = skill_manager.approve_creation_proposal(proposal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")

    # Register the new skill in the runtime registry
    try:
        registry.register_from_definition(result["name"])
    except Exception as e:
        # Skill file was written but runtime registration failed — not fatal
        pass
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_skill_factory",
            source_id=proposal_id,
        )
        if governance and governance.status in {"draft", "proposed"}:
            await improvement_governance.approve_proposal(
                governance.id,
                reviewer_id="skills-ui",
                note="Approved via Skill Creation UI",
            )
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_skill_factory",
            source_id=proposal_id,
        )
        if governance and governance.status == "approved":
            await improvement_governance.apply_proposal(
                governance.id,
                actor_id="skills-ui",
                evidence={"skill_name": result["name"]},
            )
    except Exception:
        pass

    return {"status": "approved", "proposal_id": proposal_id, "skill_name": result["name"]}


@router.post("/skills/creation-proposals/{proposal_id}/verify")
async def verify_creation_proposal(proposal_id: str, request: Request):
    """Run the verification gate for a pending skill creation proposal."""
    require_global_admin(request)
    result = await skill_manager.verify_skill_proposal(proposal_id)
    if not result.get("passed") and result.get("issues") == ["Proposal not found or not pending"]:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")
    return result


@router.post("/skills/creation-proposals/{proposal_id}/reject")
async def reject_creation_proposal(proposal_id: str, request: Request, reason: str = ""):
    """Reject a skill creation proposal."""
    require_global_admin(request)
    if not skill_manager.reject_creation_proposal(proposal_id, reason):
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_skill_factory",
            source_id=proposal_id,
        )
        if governance and governance.status in {"draft", "proposed", "approved"}:
            await improvement_governance.reject_proposal(
                governance.id,
                reviewer_id="skills-ui",
                reason=reason,
            )
    except Exception:
        pass
    return {"status": "rejected", "proposal_id": proposal_id}


# --- Parameterized routes ---

@router.get("/skills/{name}")
async def get_skill(name: str):
    """Get a single skill definition with full details."""
    defn = skill_manager.get(name)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    result = defn.to_dict()
    result["health"] = skill_manager.get_skill_health(name)
    result["usage"] = skill_manager.get_usage_stats(name)
    return result


@router.post("/skills", status_code=201)
async def create_skill(data: SkillCreateRequest, request: Request):
    """Create a new skill definition."""
    require_global_admin(request)
    if skill_manager.get(data.name):
        raise HTTPException(status_code=409, detail=f"Skill already exists: {data.name}")

    defn = skill_manager.create_skill(data.model_dump())
    return defn.to_dict()


@router.patch("/skills/{name}")
async def update_skill(name: str, data: SkillUpdateRequest, request: Request):
    """Update a skill definition (auto-increments version)."""
    require_global_admin(request)
    if not skill_manager.get(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    updates = data.model_dump(exclude_unset=True, exclude={"changelog_entry"})
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    defn = skill_manager.update_skill(name, updates, data.changelog_entry)
    return defn.to_dict()


@router.delete("/skills/{name}", status_code=204)
async def delete_skill(name: str, request: Request):
    """Delete a skill (backed up, recoverable)."""
    require_global_admin(request)
    if not skill_manager.delete_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")


@router.post("/skills/{name}/toggle")
async def toggle_skill(name: str, request: Request, enabled: bool = True):
    """Enable or disable a skill."""
    require_global_admin(request)
    defn = skill_manager.toggle_skill(name, enabled)
    return {"name": name, "enabled": defn.enabled, "version": defn.version}


# --- Health & Usage (specific {name} routes) ---

@router.get("/skills/{name}/health")
async def get_skill_health(name: str):
    """Get health score for a specific skill."""
    health = skill_manager.get_skill_health(name)
    if health.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return health


# --- Self-Improvement Proposals ---

@router.post("/skills/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str, request: Request):
    """Approve a skill improvement proposal (applies the change)."""
    require_global_admin(request)
    if not skill_manager.approve_proposal(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="skill_evolution",
            source_id=proposal_id,
        )
        if governance and governance.status in {"draft", "proposed"}:
            await improvement_governance.approve_proposal(
                governance.id,
                reviewer_id="skills-ui",
                note="Approved via Skill Evolution UI",
            )
        governance = await improvement_governance.get_proposal_by_source(
            source_system="skill_evolution",
            source_id=proposal_id,
        )
        if governance and governance.status == "approved":
            await improvement_governance.apply_proposal(
                governance.id,
                actor_id="skills-ui",
                evidence={"skill_proposal_id": proposal_id},
            )
    except Exception:
        pass
    return {"status": "approved", "proposal_id": proposal_id}


@router.post("/skills/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, request: Request, reason: str = ""):
    """Reject a skill improvement proposal."""
    require_global_admin(request)
    if not skill_manager.reject_proposal(proposal_id, reason):
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="skill_evolution",
            source_id=proposal_id,
        )
        if governance and governance.status in {"draft", "proposed", "approved"}:
            await improvement_governance.reject_proposal(
                governance.id,
                reviewer_id="skills-ui",
                reason=reason,
            )
    except Exception:
        pass
    return {"status": "rejected", "proposal_id": proposal_id}


# --- Skill Execution ---

@router.post("/skills/{name}/execute")
async def execute_skill(
    name: str,
    data: SkillExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Execute a skill on a project. Stores findings automatically.

    This is the main way to invoke skills — from the UI, chat, or API.
    The agent runs the skill, stores nuggets/facts/insights/recommendations,
    and returns the output.
    """
    if not registry.get(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    await require_project_access(db, request, data.project_id, min_role="researcher")

    output = await agent.execute_skill(
        skill_name=name,
        project_id=data.project_id,
        files=data.files,
        parameters=data.parameters,
        user_context=data.user_context,
    )

    return {
        "success": output.success,
        "summary": output.summary,
        "nuggets_count": len(output.nuggets),
        "facts_count": len(output.facts),
        "insights_count": len(output.insights),
        "recommendations_count": len(output.recommendations),
        "suggestions": output.suggestions,
        "errors": output.errors,
        "artifacts": list(output.artifacts.keys()),
    }


@router.post("/skills/{name}/plan")
async def plan_skill(
    name: str,
    data: SkillPlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a research plan using a skill.

    Returns a plan with steps, methods, and recommendations
    without actually executing the skill.
    """
    if not registry.get(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    await require_project_access(db, request, data.project_id, min_role="researcher")

    plan = await agent.plan_skill(
        skill_name=name,
        project_id=data.project_id,
        user_context=data.user_context,
    )

    if "error" in plan:
        raise HTTPException(status_code=400, detail=plan["error"])

    return plan
