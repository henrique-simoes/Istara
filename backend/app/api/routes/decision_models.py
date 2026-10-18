"""Decision-model configuration: endpoints (global admin) and each project's assurance policy.

Endpoints live in the ``DECIDER_ENDPOINTS_JSON`` runtime setting, which never holds a secret. A key
entered here goes to macOS Keychain, or to an endpoint-scoped environment secret where there is no
Keychain (``decider.credentials.store_api_key``), and no response ever returns it.

A project chooses its assurance mode and deciders (project admin). Choosing a hosted decider is
cloud egress of research data, so it also needs the hosted endpoint in the project's egress opt-in
(owner decision DEC-1); the API refuses a hosted decider without it, and never adds it implicitly.
Deciders triage for human review; nothing here lets one accept or promote evidence.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.assurance import (
    LLM_METHODS,
    MAX_ENSEMBLE_JUDGES,
    MIN_ENSEMBLE_JUDGES,
    MODES,
    ProjectAssurance,
)
from app.core.decider.contract import is_alias_model_id
from app.core.decider.credentials import (
    custody_fields,
    delete_api_key,
    resolve_api_key,
    store_api_key,
)
from app.core.decider.registry import DeciderEndpoint, configured_endpoints
from app.core.env_persistence import persist_env_value
from app.core.permissions import require_global_role, require_project_access
from app.models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Starting points shown in Settings. The hosted preset pins a versioned model: aliases such as
# ``jev-latest`` change under a calibrated scope and are recorded as aliases (research doc §4).
PRESETS: tuple[dict[str, Any], ...] = (
    {
        "preset_id": "typesafe-jev",
        "label": "TypeSafe Jev (hosted)",
        "base_url": "https://api.typesafe.ai",
        "model": "jev-1.14.0",
        "locality": "hosted",
        "needs_api_key": True,
        "docs_url": "https://docs.typesafe.ai/models",
    },
    {
        "preset_id": "local-systemone",
        "label": "Local /v1/systemone server (llama.cpp, Kev, Laya, OpenJev)",
        "base_url": "http://127.0.0.1:8080",
        "model": "",
        "locality": "local",
        "needs_api_key": False,
        "docs_url": "https://github.com/ggml-org/llama.cpp",
    },
)


class DeciderEndpointRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(default="", max_length=4096)
    timeout_s: float = 30.0
    max_retries: int = 2


class ProjectDecisionPolicyRequest(BaseModel):
    mode: str = "auto"
    llm_method: str = "auto"
    llm_judges: int = MIN_ENSEMBLE_JUDGES
    decider_endpoint_ids: list[str] = Field(default_factory=list)
    hosted_egress_endpoint_ids: list[str] = Field(default_factory=list)


def credential_status(endpoint: DeciderEndpoint) -> str:
    """``configured``, ``missing`` (hosted without a key) or ``not_needed`` (local, no key)."""
    key = resolve_api_key(
        keychain_service=endpoint.keychain_service,
        keychain_account=endpoint.keychain_account,
        env_var=endpoint.api_key_env,
    )
    if key:
        return "configured"
    return "missing" if endpoint.is_hosted else "not_needed"


def endpoint_view(endpoint: DeciderEndpoint) -> dict[str, Any]:
    """A secret-free description of an endpoint."""
    return {
        "endpoint_id": endpoint.endpoint_id,
        "base_url": endpoint.base_url,
        "model": endpoint.model,
        "model_is_alias": is_alias_model_id(endpoint.model),
        "locality": endpoint.locality,
        "timeout_s": endpoint.timeout_s,
        "max_retries": endpoint.max_retries,
        "credential_status": credential_status(endpoint),
    }


def _raw_endpoint_list() -> list[dict[str, Any]]:
    raw = getattr(settings, "decider_endpoints_json", "") or ""
    if not raw.strip():
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else []


def _save_endpoint_list(items: list[dict[str, Any]]) -> bool:
    value = json.dumps(items, separators=(",", ":"))
    settings.decider_endpoints_json = value
    try:
        return persist_env_value("DECIDER_ENDPOINTS_JSON", value)
    except OSError as exc:
        logger.warning("Decision-model endpoints changed in memory only: %s", exc)
        return False


def _catalog_or_500() -> dict[str, DeciderEndpoint]:
    try:
        return configured_endpoints()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="decider_configuration_invalid") from exc


@router.get("/settings/decision-models")
async def list_decision_model_endpoints(request: Request):
    """Configured decider endpoints (no secrets) and the setup presets."""
    require_global_role(request, "admin")
    catalog = _catalog_or_500()
    return {
        "endpoints": [endpoint_view(endpoint) for endpoint in catalog.values()],
        "presets": list(PRESETS),
    }


@router.post("/settings/decision-models")
async def add_decision_model_endpoint(data: DeciderEndpointRequest, request: Request):
    """Add an endpoint. A hosted endpoint needs a key; it is stored outside the configuration."""
    require_global_role(request, "admin")
    endpoint_id = data.endpoint_id.strip()
    catalog = _catalog_or_500()
    if endpoint_id in catalog:
        raise HTTPException(status_code=409, detail="decider_endpoint_exists")
    item = {
        "endpoint_id": endpoint_id,
        "base_url": data.base_url.strip(),
        "model": data.model.strip(),
        "timeout_s": data.timeout_s,
        "max_retries": data.max_retries,
        **custody_fields(endpoint_id),
    }
    try:
        endpoint = DeciderEndpoint(**item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    api_key = data.api_key.strip()
    if endpoint.is_hosted and not api_key:
        raise HTTPException(status_code=400, detail="decider_api_key_required")
    if api_key:
        try:
            store_api_key(endpoint_id, api_key)
        except Exception as exc:
            logger.warning("Decision-model key custody failed for %s", endpoint_id)
            raise HTTPException(status_code=503, detail="decider_api_key_custody_failed") from exc
    item["base_url"] = endpoint.base_url
    persisted = _save_endpoint_list([*_raw_endpoint_list(), item])
    return {"status": "added", "endpoint": endpoint_view(endpoint), "persisted": persisted}


@router.delete("/settings/decision-models/{endpoint_id}")
async def delete_decision_model_endpoint(endpoint_id: str, request: Request):
    """Remove an endpoint and its stored key. Projects that named it fall back to no decider."""
    require_global_role(request, "admin")
    items = _raw_endpoint_list()
    remaining = [item for item in items if item.get("endpoint_id") != endpoint_id]
    if len(remaining) == len(items):
        raise HTTPException(status_code=404, detail="decider_endpoint_not_found")
    persisted = _save_endpoint_list(remaining)
    delete_api_key(endpoint_id)
    return {"status": "deleted", "endpoint_id": endpoint_id, "persisted": persisted}


@router.post("/settings/decision-models/{endpoint_id}/check")
async def check_decision_model_endpoint(endpoint_id: str, request: Request):
    """Send one fixed question with no research data and report what the server answered.

    It reaches the endpoint directly (admin action), so it carries only a constant probe text.
    """
    require_global_role(request, "admin")
    endpoint = _catalog_or_500().get(endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="decider_endpoint_not_found")
    from app.core.decider.client import SystemOneClient
    from app.core.decider.contract import Choice

    api_key = resolve_api_key(
        keychain_service=endpoint.keychain_service,
        keychain_account=endpoint.keychain_account,
        env_var=endpoint.api_key_env,
    )
    if endpoint.is_hosted and not api_key:
        return {"ok": False, "reason": "missing_api_key"}
    client = SystemOneClient(endpoint, api_key=api_key)
    question = Choice(
        "Is the `state` a connectivity check?",
        {"yes": "The state says it is a connectivity check.", "no": "It says something else."},
    )
    outcome = await client.decide("This is a connectivity check from Istara.", {"probe": question})
    return {
        "ok": bool(outcome.ok),
        "reason": None if outcome.ok else outcome.reason,
        "served_model": getattr(outcome, "served_model", None),
        "requested_model": endpoint.model,
    }


def _policy_view(
    assurance: ProjectAssurance,
    hosted_egress: list[str],
    catalog: dict[str, DeciderEndpoint],
) -> dict[str, Any]:
    return {
        "mode": assurance.mode,
        "llm_method": assurance.llm_method,
        "llm_judges": assurance.llm_judges,
        "decider_endpoint_ids": list(assurance.decider_endpoint_ids),
        "hosted_egress_endpoint_ids": hosted_egress,
        "available_endpoints": [
            {
                "endpoint_id": endpoint.endpoint_id,
                "model": endpoint.model,
                "locality": endpoint.locality,
                "model_is_alias": is_alias_model_id(endpoint.model),
            }
            for endpoint in catalog.values()
        ],
        "unknown_endpoint_ids": sorted(
            {
                endpoint_id
                for endpoint_id in [*assurance.decider_endpoint_ids, *hosted_egress]
                if endpoint_id not in catalog
            }
        ),
        "choices": {
            "modes": list(MODES),
            "llm_methods": ["auto", *LLM_METHODS],
            "llm_judges": [MIN_ENSEMBLE_JUDGES, MAX_ENSEMBLE_JUDGES],
        },
    }


async def _stored_policy(db: AsyncSession, project_id: str) -> tuple[ProjectAssurance, list[str]]:
    from app.models.assurance_policy import ProjectAssurancePolicy
    from app.models.decision_policy import DecisionModelProjectPolicy

    row = await db.get(ProjectAssurancePolicy, project_id)
    assurance = (
        ProjectAssurance(
            mode=row.mode,
            llm_method=row.llm_method,
            llm_judges=row.llm_judges,
            decider_endpoint_ids=tuple(row.decider_endpoint_ids()),
        )
        if row is not None
        else ProjectAssurance()
    )
    egress = await db.get(DecisionModelProjectPolicy, project_id)
    return assurance, egress.hosted_egress_endpoint_ids() if egress is not None else []


@router.get("/projects/{project_id}/decision-models")
async def get_project_decision_policy(
    project_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """The project's assurance mode, deciders, hosted-egress opt-in and trust status."""
    await require_project_access(db, request, project_id, min_role="viewer")
    assurance, hosted_egress = await _stored_policy(db, project_id)
    view = _policy_view(assurance, hosted_egress, _catalog_or_500())
    view["trust"] = await _trust_summary(db, project_id)
    view["can_edit"] = await _can_edit(db, request, project_id)
    return view


async def _can_edit(db: AsyncSession, request: Request, project_id: str) -> bool:
    from app.core.permissions import can_admin_project

    return await can_admin_project(db, request, project_id)


async def _trust_summary(db: AsyncSession, project_id: str) -> list[dict[str, Any]]:
    """Per scope: ``calibrating`` before its first evaluation, then ``shadow`` or ``trusted``."""
    from app.services.decision_health import scope_summaries

    summary = []
    for scope in await scope_summaries(db, project_id):
        evaluated = scope["reasons"] != ["not_evaluated"]
        status = "trusted" if scope["trusted"] else "shadow" if evaluated else "calibrating"
        summary.append({**scope, "status": status})
    return summary


@router.put("/projects/{project_id}/decision-models")
async def put_project_decision_policy(
    project_id: str,
    data: ProjectDecisionPolicyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Set the project's assurance mode and deciders (project admin).

    A hosted decider must also be in ``hosted_egress_endpoint_ids``: choosing one never opts the
    project in to cloud egress by itself.
    """
    subject = await require_project_access(db, request, project_id, min_role="project_admin")
    catalog = _catalog_or_500()
    deciders = list(dict.fromkeys(item.strip() for item in data.decider_endpoint_ids))
    egress = sorted({item.strip() for item in data.hosted_egress_endpoint_ids if item.strip()})
    try:
        assurance = ProjectAssurance(
            mode=data.mode,
            llm_method=data.llm_method,
            llm_judges=data.llm_judges,
            decider_endpoint_ids=tuple(deciders),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    unknown = [item for item in [*deciders, *egress] if item not in catalog]
    if unknown:
        raise HTTPException(status_code=400, detail="unknown_decider_endpoint")
    if any(not catalog[item].is_hosted for item in egress):
        raise HTTPException(status_code=400, detail="egress_opt_in_is_for_hosted_endpoints")
    if any(catalog[item].is_hosted and item not in egress for item in deciders):
        raise HTTPException(status_code=400, detail="hosted_decider_needs_egress_opt_in")
    if assurance.mode in {"decision_models", "both"} and not deciders:
        raise HTTPException(status_code=400, detail="mode_needs_a_decider")

    from app.models.assurance_policy import ProjectAssurancePolicy
    from app.models.decision_policy import DecisionModelProjectPolicy

    row = await db.get(ProjectAssurancePolicy, project_id)
    if row is None:
        row = ProjectAssurancePolicy(project_id=project_id)
        db.add(row)
    row.mode = assurance.mode
    row.llm_method = assurance.llm_method
    row.llm_judges = assurance.llm_judges
    row.decider_endpoint_ids_json = json.dumps(deciders)
    row.updated_by = subject.id
    egress_row = await db.get(DecisionModelProjectPolicy, project_id)
    if egress_row is None:
        egress_row = DecisionModelProjectPolicy(project_id=project_id)
        db.add(egress_row)
    egress_row.set_hosted_egress_endpoint_ids(egress)
    egress_row.updated_by = subject.id
    await db.commit()
    return _policy_view(assurance, egress, catalog)
