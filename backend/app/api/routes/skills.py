"""Skills management API — CRUD, versioning, self-improvement, execution, health monitoring."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent import agent
from app.core.improvement_governance import improvement_governance
from app.core.permissions import (
    ProjectRole,
    get_active_project_or_404,
    require_global_admin,
    require_global_role,
    require_project_access,
)
from app.models.database import get_db
from app.skills.registry import registry
from app.skills.skill_manager import skill_manager

router = APIRouter()


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = str(project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _require_skill_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: ProjectRole = "viewer",
) -> str:
    scoped_project_id = _require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def _require_active_skill_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: ProjectRole = "researcher",
) -> str:
    scoped_project_id = _require_project_id(project_id)
    project = await get_active_project_or_404(
        db,
        request,
        scoped_project_id,
        min_role=min_role,
    )
    return project.id


def _bounded_timeout(
    requested: float | None,
    *,
    default_seconds: float,
    max_seconds: float,
) -> float:
    if requested is None:
        value = default_seconds
    else:
        value = requested
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default_seconds
    return max(0.1, min(value, max_seconds))


def _skill_output_research_validity(output) -> dict:
    if hasattr(output, "mark_research_artifacts_candidate"):
        output.mark_research_artifacts_candidate()
    validity = getattr(output, "research_validity", None)
    validity = validity if isinstance(validity, dict) else {}
    return {
        **validity,
        "status": "provisional",
        "artifact_state": "skill_output_candidate",
        "report_allowed": False,
        "promotion_required": "source_grounded_coding_reliability_reconciliation_done_gate",
        "reason": (
            "Skill outputs are candidate Research Spine artifacts until source-grounded "
            "coding, reliability/reconciliation, and Done-task gates accept them."
        ),
    }


class SkillExecuteRequest(BaseModel):
    project_id: str
    files: list[str] = []
    parameters: dict = {}
    user_context: str = ""
    timeout_seconds: float | None = None


class SkillPlanRequest(BaseModel):
    project_id: str
    user_context: str = ""
    timeout_seconds: float | None = None


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
async def get_all_health(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get health scores for all skills."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    return {"skills": skill_manager.get_all_health(project_id=scoped_project_id)}


@router.get("/skills/proposals/pending")
async def get_pending_proposals(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all pending skill improvement proposals."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    proposals = skill_manager.get_pending_proposals(project_id=scoped_project_id)
    return {
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals),
    }


@router.get("/skills/proposals/all")
async def get_all_proposals(
    request: Request,
    limit: int = 50,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all proposals (pending, approved, rejected)."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    return {
        "proposals": [
            p.to_dict()
            for p in skill_manager.get_all_proposals(limit, project_id=scoped_project_id)
        ],
    }


# --- Skill Creation Proposals ---


@router.get("/skills/creation-proposals/pending")
async def get_pending_creation_proposals(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all pending skill creation proposals."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    proposals = skill_manager.get_pending_creation_proposals(project_id=scoped_project_id)
    return {
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals),
    }


@router.get("/skills/creation-proposals/all")
async def get_all_creation_proposals(
    request: Request,
    limit: int = 20,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all skill creation proposals (pending, approved, rejected)."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    proposals = skill_manager.get_all_creation_proposals(
        limit,
        project_id=scoped_project_id,
    )
    return {
        "proposals": [p.to_dict() for p in proposals],
    }


@router.post("/skills/creation-proposals/{proposal_id}/approve")
async def approve_creation_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve a skill creation proposal — writes definition file and registers skill."""
    require_global_role(request, "researcher")
    scoped_project_id = await _require_active_skill_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    proposal = next(
        (
            p
            for p in skill_manager.get_pending_creation_proposals(project_id=scoped_project_id)
            if p.id == proposal_id
        ),
        None,
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")

    if not proposal.test_result:
        verification = await skill_manager.verify_skill_proposal(
            proposal_id,
            project_id=scoped_project_id,
        )
        if not verification.get("passed"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Creation proposal failed verification and was not approved",
                    "verification": verification,
                },
            )

    result = skill_manager.approve_creation_proposal(
        proposal_id,
        project_id=scoped_project_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")

    # Register the new skill in the runtime registry
    try:
        registry.register_from_definition(result["name"])
    except Exception:
        # Skill file was written but runtime registration failed — not fatal
        pass
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_skill_factory",
            source_id=proposal_id,
            project_id=scoped_project_id,
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
            project_id=scoped_project_id,
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
async def verify_creation_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Run the verification gate for a pending skill creation proposal."""
    require_global_role(request, "researcher")
    scoped_project_id = await _require_active_skill_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    result = await skill_manager.verify_skill_proposal(
        proposal_id,
        project_id=scoped_project_id,
    )
    if not result.get("passed") and result.get("issues") == ["Proposal not found or not pending"]:
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")
    return result


@router.post("/skills/creation-proposals/{proposal_id}/reject")
async def reject_creation_proposal(
    proposal_id: str,
    request: Request,
    reason: str = "",
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Reject a skill creation proposal."""
    require_global_role(request, "researcher")
    scoped_project_id = await _require_skill_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    if not skill_manager.reject_creation_proposal(
        proposal_id,
        reason,
        project_id=scoped_project_id,
    ):
        raise HTTPException(status_code=404, detail="Creation proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="memento_skill_factory",
            source_id=proposal_id,
            project_id=scoped_project_id,
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
async def get_skill(
    name: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get a single skill definition with full details."""
    defn = skill_manager.get(name)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    result = defn.to_dict()
    scoped_project_id = None
    if project_id:
        scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    result["health"] = (
        skill_manager.get_skill_health(name, project_id=scoped_project_id)
        if scoped_project_id
        else None
    )
    result["usage"] = (
        skill_manager.get_usage_stats(name, project_id=scoped_project_id)
        if scoped_project_id
        else {}
    )
    return result


@router.post("/skills", status_code=201)
async def create_skill(data: SkillCreateRequest, request: Request):
    """Create a new skill definition."""
    require_global_role(request, "researcher")
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
    require_global_role(request, "researcher")
    defn = skill_manager.toggle_skill(name, enabled)
    return {"name": name, "enabled": defn.enabled, "version": defn.version}


# --- Health & Usage (specific {name} routes) ---


@router.get("/skills/{name}/health")
async def get_skill_health(
    name: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get health score for a specific skill."""
    scoped_project_id = await _require_skill_project_scope(db, request, project_id)
    health = skill_manager.get_skill_health(name, project_id=scoped_project_id)
    if health.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return health


# --- Self-Improvement Proposals ---


@router.post("/skills/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve a skill improvement proposal (applies the change)."""
    require_global_role(request, "researcher")
    scoped_project_id = await _require_active_skill_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    if not skill_manager.approve_proposal(proposal_id, project_id=scoped_project_id):
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="skill_evolution",
            source_id=proposal_id,
            project_id=scoped_project_id,
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
            project_id=scoped_project_id,
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
async def reject_proposal(
    proposal_id: str,
    request: Request,
    reason: str = "",
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Reject a skill improvement proposal."""
    require_global_role(request, "researcher")
    scoped_project_id = await _require_skill_project_scope(
        db,
        request,
        project_id,
        min_role="researcher",
    )
    if not skill_manager.reject_proposal(
        proposal_id,
        reason,
        project_id=scoped_project_id,
    ):
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    try:
        governance = await improvement_governance.get_proposal_by_source(
            source_system="skill_evolution",
            source_id=proposal_id,
            project_id=scoped_project_id,
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
    """Execute a skill on a project and store task-backed findings for review.

    This is the main way to invoke skills — from the UI, chat, or API.
    The agent runs the skill, creates an In Review task, stores Atomic Research
    artifacts, and starts task-linked evidence-unit/coding-run orchestration when
    the output includes nuggets. Done/report gates still enforce the
    research-validity contract before findings become report evidence.
    """
    if not registry.get(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    project_id = await _require_active_skill_project_scope(
        db,
        request,
        data.project_id,
        min_role="researcher",
    )

    timeout_seconds = _bounded_timeout(
        data.timeout_seconds,
        default_seconds=settings.skill_execute_timeout_seconds,
        max_seconds=settings.skill_execute_max_timeout_seconds,
    )
    try:
        output = await asyncio.wait_for(
            agent.execute_skill(
                skill_name=name,
                project_id=project_id,
                files=data.files,
                parameters=data.parameters,
                user_context=data.user_context,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Skill execution timed out after {timeout_seconds:.3g}s",
        )

    schema_budget = None
    for artifact_name, artifact_content in output.artifacts.items():
        if artifact_name.endswith("_schema_budget.json") and isinstance(artifact_content, str):
            try:
                schema_budget = json.loads(artifact_content)
            except Exception:
                schema_budget = {"parse_error": True}
            break

    research_validity = _skill_output_research_validity(output)
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
        "schema_budget": schema_budget,
        "json_success": output.json_success,
        "artifact_state": research_validity["artifact_state"],
        "report_allowed": research_validity["report_allowed"],
        "research_validity": research_validity,
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
    project_id = await _require_active_skill_project_scope(
        db,
        request,
        data.project_id,
        min_role="researcher",
    )

    timeout_seconds = _bounded_timeout(
        data.timeout_seconds,
        default_seconds=settings.skill_plan_timeout_seconds,
        max_seconds=settings.skill_plan_max_timeout_seconds,
    )
    try:
        plan = await asyncio.wait_for(
            agent.plan_skill(
                skill_name=name,
                project_id=project_id,
                user_context=data.user_context,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Skill plan timed out after {timeout_seconds:.3g}s",
        )

    if "error" in plan:
        raise HTTPException(status_code=400, detail=plan["error"])

    return plan
