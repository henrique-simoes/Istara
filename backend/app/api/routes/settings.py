"""Settings and system info API routes."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.env_persistence import persist_env_value
from app.core.hardware import detect_hardware, recommend_model
from app.core.ollama import ollama
from app.core.permissions import require_global_role, require_project_access
from app.core.runtime_freshness import detect_runtime_freshness
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


class StrictRoutingRequest(BaseModel):
    enabled: bool


class DataIntegrityQuarantineRequest(BaseModel):
    dry_run: bool = True


class FileEncryptionEnableRequest(BaseModel):
    confirm_loss_warning: bool = False


class FileEncryptionRotateRequest(BaseModel):
    confirm_rotation: bool = False


def _persist_env(key: str, value: str) -> None:
    """Backward-compatible wrapper for settings persistence."""
    persist_env_value(key, value)


def _active_model() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_model
    return settings.ollama_model


def _embed_model() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_embed_model
    return settings.ollama_embed_model


def _global_agentic_engine() -> str:
    """Return the public, normalized global agent engine choice."""
    from app.core.pi_replacement import PI_ENGINE_VALUES

    value = str(getattr(settings, "agentic_engine_default", "legacy") or "").strip().lower()
    return "pi" if value in PI_ENGINE_VALUES else "legacy"


async def _pi_catalog_info() -> list[dict]:
    """W8 UX parity: the Pi identity catalog merged into model pickers.

    Read-only identity/capability view (endpoint ids and model names only —
    never URLs or keys). A fresh manager per call keeps the LLMServer
    projection current; any failure degrades to the legacy-only response.
    """
    try:
        from dataclasses import asdict

        from app.core.pi_runtime.model_manager import PiModelManager

        manager = PiModelManager()
        await manager.ensure_db_projection()
        return [asdict(info) for info in manager.catalog()]
    except Exception:
        logger.debug("pi catalog merge skipped", exc_info=True)
        return []


def _cached_llm_readiness() -> tuple[bool, bool]:
    """Return cached reachability/readiness without probing provider endpoints."""
    nodes = getattr(ollama, "_nodes", None)
    if not nodes:
        return False, False

    reachable = False
    chat_ready = False
    for node in nodes.values():
        try:
            snapshot = node.to_dict()
        except Exception:
            continue
        reachable = reachable or bool(snapshot.get("is_reachable"))
        chat_ready = chat_ready or bool(snapshot.get("is_ready"))
    return reachable, chat_ready


@router.get("/settings/hardware")
async def get_hardware_info(request: Request):
    """Get hardware detection results and model recommendation."""
    require_global_role(request, "admin")
    try:
        profile = detect_hardware()
        recommendation = recommend_model(profile)

        return {
            "hardware": {
                "total_ram_gb": profile.total_ram_gb,
                "available_ram_gb": profile.available_ram_gb,
                "istara_ram_budget_gb": profile.istara_ram_budget_gb,
                "cpu_cores": profile.cpu_cores,
                "cpu_arch": profile.cpu_arch,
                "istara_cpu_budget_cores": profile.istara_cpu_budget_cores,
                "gpu": {
                    "vendor": profile.gpu.vendor,
                    "name": profile.gpu.name,
                    "vram_mb": profile.gpu.vram_mb,
                }
                if profile.gpu
                else None,
                "os": f"{profile.os_name} {profile.os_version}",
            },
            "recommendation": {
                "model_name": recommendation.model_name,
                "quantization": recommendation.quantization,
                "context_length": recommendation.context_length,
                "gpu_layers": recommendation.gpu_layers,
                "reason": recommendation.reason,
            },
        }
    except Exception as e:
        return {
            "hardware": None,
            "recommendation": None,
            "error": f"Hardware detection failed: {e}",
        }


@router.get("/settings/file-encryption/status")
async def get_file_encryption_status(request: Request):
    """Return file/content encryption status without exposing key material."""
    require_global_role(request, "admin")
    from app.core.file_encryption import (
        CRYPTO_AVAILABLE,
        is_encrypted_file,
        key_fingerprint,
        managed_upload_files,
        resolve_file_encryption_key,
    )

    files = managed_upload_files()
    encrypted_files = sum(1 for path in files if is_encrypted_file(path))
    key_available = bool(resolve_file_encryption_key(create=False))
    return {
        "enabled": settings.file_encryption_enabled,
        "crypto_available": CRYPTO_AVAILABLE,
        "key_available": key_available,
        "key_storage": (
            "environment" if settings.file_encryption_key else "macos_keychain_or_owner_key_file"
        ),
        "key_fingerprint": key_fingerprint() if key_available else "",
        "managed_file_count": len(files),
        "encrypted_file_count": encrypted_files,
        "backups_encrypted_when_enabled": True,
        "warning": (
            "If the file encryption key is lost, encrypted uploads, document text, "
            "and encrypted backups cannot be decrypted."
        ),
    }


@router.post("/settings/file-encryption/enable")
async def enable_file_encryption(
    data: FileEncryptionEnableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Enable encryption and migrate existing managed uploads/document text."""
    require_global_role(request, "admin")
    if not data.confirm_loss_warning:
        raise HTTPException(
            status_code=400,
            detail="Confirm that the file encryption key must be saved; losing it is destructive.",
        )
    from app.core.file_encryption import CRYPTO_AVAILABLE
    from app.services.file_encryption_migration import encrypt_existing_project_content

    if not CRYPTO_AVAILABLE:
        raise HTTPException(status_code=503, detail="cryptography is required for file encryption")
    settings.file_encryption_enabled = True
    _persist_env("FILE_ENCRYPTION_ENABLED", "true")
    result = await encrypt_existing_project_content(db)
    return {"status": "enabled", **result}


@router.post("/settings/file-encryption/rotate")
async def rotate_file_encryption_key(
    data: FileEncryptionRotateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Rotate the file/content encryption key and re-encrypt protected data."""
    require_global_role(request, "admin")
    if not settings.file_encryption_enabled:
        raise HTTPException(status_code=400, detail="File encryption is not enabled.")
    if not data.confirm_rotation:
        raise HTTPException(status_code=400, detail="Confirm key rotation before proceeding.")
    from app.services.file_encryption_migration import rotate_existing_project_content

    result = await rotate_existing_project_content(db)
    return {"status": "rotated", **result}


@router.get("/settings/models")
async def get_models(request: Request):
    """Get available and active models.

    For LM Studio, probes the actually loaded model via a minimal chat request
    since /v1/models returns all downloaded (not just loaded) models.
    """
    require_global_role(request, "admin")
    from app.core.compute_registry import compute_registry

    healthy = await ollama.health()
    registry_models = await compute_registry.list_models()
    if not healthy and not registry_models:
        return {
            "status": "offline",
            "provider": settings.llm_provider,
            "models": [],
            "active_model": _active_model(),
            "embed_model": _embed_model(),
            "agentic_engine_default": _global_agentic_engine(),
            "pi_catalog": await _pi_catalog_info(),
        }

    models = registry_models or await ollama.list_models()
    active = _active_model()

    # For LM Studio, detect the actually loaded model only when the operator
    # has not pinned a concrete model. Managed OpenAI-compatible endpoints may
    # report aliases or broader provider defaults, but explicit config must
    # remain the routing source of truth.
    if settings.llm_provider == "lmstudio":
        from app.core.lmstudio import (
            LMStudioClient,
            configured_lmstudio_model_is_authoritative,
        )

        if isinstance(ollama, LMStudioClient) and not configured_lmstudio_model_is_authoritative():
            loaded = await ollama.detect_loaded_model()
            if loaded and loaded != active:
                settings.lmstudio_model = loaded
                active = loaded
                # Persist so config stays in sync
                try:
                    _persist_env("LMSTUDIO_MODEL", loaded)
                except Exception:
                    pass
        elif not models and configured_lmstudio_model_is_authoritative(active):
            models = [
                {
                    "name": active,
                    "model": active,
                    "size": 0,
                    "details": {"source": "configured"},
                }
            ]

    # Enrich each model with provider info from the router.
    # The LLMRouter.list_models() already attaches _server / _server_id;
    # we promote those to public fields and add provider_type.
    server_map = {s.node_id: s for s in compute_registry._nodes.values()}
    enriched = []
    for m in models:
        server_id = m.pop("_server_id", None)
        server_name = m.pop("_server", None)
        provider_type = ""
        if server_id and server_id in server_map:
            entry = server_map[server_id]
            server_name = entry.name
            provider_type = entry.provider_type
        m["server_name"] = server_name or settings.llm_provider
        m["provider_type"] = provider_type or settings.llm_provider
        enriched.append(m)

    return {
        "status": "online",
        "provider": settings.llm_provider,
        "models": enriched,
        "active_model": active,
        "embed_model": _embed_model(),
        "agentic_engine_default": _global_agentic_engine(),
        "pi_catalog": await _pi_catalog_info(),
    }


@router.post("/settings/model")
async def switch_model(model_name: str, request: Request):
    """Switch the active model at runtime (pulls if using Ollama and not available)."""
    require_global_role(request, "admin")
    models = await ollama.list_models()
    model_names = [m.get("name", "") for m in models]

    if model_name not in model_names and settings.llm_provider == "ollama":
        try:
            async for _progress in ollama.pull_model(model_name):
                pass
        except Exception as e:
            return {
                "status": "error",
                "model": model_name,
                "message": f"Failed to pull model: {e}",
            }

    # Update runtime settings so all subsequent LLM calls use the new model
    if settings.llm_provider == "lmstudio":
        settings.lmstudio_model = model_name
        env_var = "LMSTUDIO_MODEL"
    else:
        settings.ollama_model = model_name
        env_var = "OLLAMA_MODEL"

    # Persist to .env so the choice survives server restarts
    try:
        _persist_env(env_var, model_name)
        logger.info(f"Persisted {env_var}={model_name} to .env")
        persisted = True
    except Exception as e:
        logger.warning(f"Could not persist model to .env: {e}")
        persisted = False

    return {
        "status": "switched",
        "model": model_name,
        "persisted": persisted,
        "message": f"Model switched to {model_name}."
        + ("" if persisted else f" Update {env_var} in .env to persist."),
    }


@router.post("/settings/provider")
async def switch_provider(provider: str, request: Request):
    """Switch the LLM provider at runtime (ollama or lmstudio)."""
    require_global_role(request, "admin")

    if provider not in ("ollama", "lmstudio"):
        raise HTTPException(status_code=400, detail="Provider must be 'ollama' or 'lmstudio'")

    settings.llm_provider = provider

    # Recreate the LLM client singleton for the new provider
    import app.core.ollama as ollama_module

    ollama_module.ollama = ollama_module._create_llm_client()

    # Persist to .env
    try:
        _persist_env("LLM_PROVIDER", provider)
        persisted = True
    except Exception:
        persisted = False

    return {
        "status": "switched",
        "provider": provider,
        "model": _active_model(),
        "persisted": persisted,
        "message": f"Provider switched to {provider}."
        + ("" if persisted else " Update LLM_PROVIDER in .env to persist."),
    }


@router.post("/settings/maintenance/pause")
async def maintenance_pause(reason: str = "testing", request: Request = None):
    """Enter maintenance mode — halts ALL agent work and LLM operations. Admin only.

    Used by the simulation test runner to ensure exclusive model access.
    While paused, no agents will start, no tasks will be picked, and no
    LLM calls will be made by the backend, freeing the model entirely
    for the test runner.
    """
    require_admin_from_request(request)
    from app.agents.orchestrator import meta_orchestrator
    from app.core.resource_governor import governor

    governor.enter_maintenance(reason)

    # Force-pause all managed agents via the orchestrator
    paused_agents = []
    for agent in meta_orchestrator.list_agents():
        if agent.state.value in ("working", "idle"):
            meta_orchestrator.pause_agent(agent.id)
            paused_agents.append(agent.id)

    logger.info(f"Maintenance pause: {len(paused_agents)} agents paused, reason={reason}")

    return {
        "status": "paused",
        "maintenance_mode": True,
        "reason": reason,
        "paused_agents": paused_agents,
        "message": f"All agent operations halted ({reason}). Model is free for exclusive use.",
    }


@router.post("/settings/maintenance/resume")
async def maintenance_resume(request: Request):
    """Exit maintenance mode — resume all agent operations. Admin only.

    Agents that were paused by the maintenance call will be set back to IDLE.
    The ResourceGovernor will allow new agent starts and LLM calls again.
    """
    require_admin_from_request(request)
    from app.agents.orchestrator import meta_orchestrator
    from app.core.resource_governor import governor

    governor.exit_maintenance()

    # Resume all paused agents
    resumed_agents = []
    for agent in meta_orchestrator.list_agents():
        if agent.state.value == "paused":
            meta_orchestrator.resume_agent(agent.id)
            resumed_agents.append(agent.id)

    logger.info(f"Maintenance resume: {len(resumed_agents)} agents resumed")

    return {
        "status": "resumed",
        "maintenance_mode": False,
        "resumed_agents": resumed_agents,
        "message": "Normal operations resumed. Agents are active again.",
    }


@router.get("/settings/maintenance")
async def maintenance_status(request: Request):
    """Check current maintenance mode status."""
    require_global_role(request, "admin")
    from app.core.resource_governor import governor

    return {
        "maintenance_mode": governor.maintenance_mode,
        "maintenance_reason": governor._maintenance_reason,
    }


@router.post("/settings/strict-routing")
async def toggle_strict_routing(data: StrictRoutingRequest, request: Request):
    """Toggle model-aware strict routing for pooled compute. Admin only."""
    require_admin_from_request(request)
    enabled = data.enabled
    settings.strict_auto_routing = enabled
    try:
        _persist_env("STRICT_AUTO_ROUTING", str(enabled).lower())
        persisted = True
    except Exception as exc:
        logger.warning("Could not persist STRICT_AUTO_ROUTING: %s", exc)
        persisted = False

    return {
        "strict_auto_routing": enabled,
        "persisted": persisted,
        "message": "Strict compute routing updated.",
    }


@router.get("/settings/integrations-status")
async def integrations_status(request: Request):
    """Check configuration status of design integrations (Stitch, Figma)."""
    require_global_role(request, "admin")
    return {
        "stitch_configured": bool(settings.stitch_api_key),
        "figma_configured": bool(settings.figma_api_token),
    }


@router.get("/settings/vector-health")
async def vector_health(request: Request):
    """Check embedding dimension consistency across vector stores."""
    require_global_role(request, "admin")
    from app.core.vector_health import check_embedding_dimensions

    return await check_embedding_dimensions()


# ───── Data Management & Migration ─────


@router.get("/settings/data-integrity")
async def check_data_integrity(request: Request, db: AsyncSession = Depends(get_db)):
    """Run a data integrity check and return health report."""
    require_global_role(request, "admin")
    from app.core.data_integrity import run_integrity_check

    report = await run_integrity_check(db)
    return report


@router.post("/settings/data-integrity/quarantine")
async def quarantine_data_integrity(
    data: DataIntegrityQuarantineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Quarantine orphaned runtime artifacts and invalid PDFs. Admin only."""
    require_admin_from_request(request)
    from app.core.data_integrity import quarantine_integrity_issues

    return await quarantine_integrity_issues(db, dry_run=data.dry_run)


@router.post("/settings/export-database")
async def export_database(request: Request, db: AsyncSession = Depends(get_db)):
    """Export the entire database to a portable JSON structure. Admin only."""
    require_admin_from_request(request)
    from app.core.data_migration import export_full_database

    data = await export_full_database(db)
    return data


@router.post("/settings/import-database")
async def import_database(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Import a previously exported database dump. Admin only."""
    require_admin_from_request(request)
    from app.core.data_migration import import_full_database

    summary = await import_full_database(db, data)
    return summary


@router.get("/settings/status")
async def system_status():
    """Get overall system status.

    This endpoint is intentionally public so login, onboarding, and status bars
    can tell whether the backend is alive. Keep it passive and non-sensitive:
    do not probe provider endpoints, do not discover loaded models, and do not
    expose shared provider/model/RAG configuration.
    """
    llm_healthy, llm_ready = _cached_llm_readiness()

    return {
        "status": "healthy" if llm_ready else "degraded",
        "team_mode": settings.team_mode,
        "strict_auto_routing": settings.strict_auto_routing,
        "llm_readiness": {
            "reachable": llm_healthy,
            "chat_ready": llm_ready,
        },
        "services": {
            "backend": "running",
            "llm": "connected" if llm_healthy else "disconnected",
        },
        "runtime": detect_runtime_freshness(),
    }


@router.get("/settings/telemetry/status")
async def telemetry_status(request: Request):
    """Get telemetry configuration and stats."""
    require_admin_from_request(request)
    from sqlalchemy import func, select

    from app.models.database import async_session
    from app.models.model_skill_stats import ModelSkillStats
    from app.models.telemetry_span import TelemetrySpan

    try:
        async with async_session() as session:
            total_spans = await session.scalar(select(func.count(TelemetrySpan.id)))
            total_models = await session.scalar(select(func.count(ModelSkillStats.id)))
            recent_cutoff = datetime.now(UTC) - timedelta(days=1)

            recent_spans = await session.scalar(
                select(func.count(TelemetrySpan.id)).where(
                    TelemetrySpan.created_at >= recent_cutoff
                )
            )
    except Exception:
        total_spans = 0
        total_models = 0
        recent_spans = 0

    return {
        "telemetry_enabled": settings.telemetry_enabled,
        "telemetry_export_dir": settings.telemetry_export_dir,
        "stats": {
            "total_spans": total_spans or 0,
            "total_model_entries": total_models or 0,
            "spans_last_24h": recent_spans or 0,
        },
    }


@router.post("/settings/telemetry/export")
async def export_telemetry_data(
    request: Request,
    project_id: str | None = None,
    days: int = 7,
    include_models: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Export telemetry data to local JSON files. No phone-home."""
    if project_id:
        await require_project_access(db, request, project_id, min_role="viewer")
    else:
        require_admin_from_request(request)
    from app.core.telemetry_export import export_telemetry

    if days < 1 or days > 90:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="days must be between 1 and 90")

    return await export_telemetry(
        project_id=project_id,
        days=days,
        include_models=include_models,
    )


@router.post("/settings/telemetry/toggle")
async def toggle_telemetry(request: Request, enabled: bool):
    """Toggle telemetry recording on/off. Admin only."""
    require_admin_from_request(request)
    settings.telemetry_enabled = enabled
    _persist_env("TELEMETRY_ENABLED", str(enabled).lower())
    return {
        "telemetry_enabled": enabled,
        "message": f"Telemetry {'enabled' if enabled else 'disabled'}.",
    }


@router.get("/settings/telemetry/healing")
async def get_self_healing_evaluation(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Evaluate recent telemetry to detect self-healing rule violations."""
    await require_project_access(db, request, project_id, min_role="viewer")
    from app.core.self_healing_rules import self_healing

    return await self_healing.evaluate_all(project_id)


@router.post("/settings/team-mode")
async def toggle_team_mode(request: Request, db: AsyncSession = Depends(get_db)):
    """Toggle team mode on/off. Requires admin in team mode."""
    body = await request.json()
    enabled = bool(body.get("enabled", False))

    # In team mode, only admins can change this
    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Admin required to change team mode")

    settings.team_mode = enabled
    _persist_env("TEAM_MODE", str(enabled).lower())
    return {
        "team_mode": enabled,
        "message": "Team mode updated. Server restart recommended for full effect.",
    }


# ── Agentic core + Pi endpoint management (CF-SPEC-12) ──────────────────────


class AgenticEngineRequest(BaseModel):
    engine: str  # "pi" | "istara" (UI name) | "legacy" (internal alias)


class PiEndpointRequest(BaseModel):
    endpoint_id: str
    provider_kind: str = "openai_compat"
    base_url: str
    model: str
    keychain_service: str  # required: every Pi endpoint resolves its secret via Keychain
    keychain_account: str = ""
    timeout_ms: int = 30_000
    max_retries: int = 0
    cost_input_per_mtok: float = 0.0
    cost_output_per_mtok: float = 0.0
    cost_cache_read_per_mtok: float = 0.0
    cost_cache_write_per_mtok: float = 0.0
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False


def _persist_pi_endpoints() -> None:
    import json as _json

    payload = [endpoint.model_dump() for endpoint in settings.pi_api_endpoints]
    _persist_env("PI_API_ENDPOINTS", _json.dumps(payload))


@router.post("/settings/agentic-engine")
async def set_agentic_engine(data: AgenticEngineRequest, request: Request):
    """Set the GLOBAL default agentic core: 'pi' or 'istara' (CF-SPEC-12).

    Engine resolution order is unchanged (per-call > header > project > this
    global default). Persisted to .env like every other settings switch.
    """
    require_global_role(request, "admin")
    from app.core.pi_replacement import PI_ENGINE_VALUES

    value = data.engine.strip().lower()
    if value == "istara":
        value = "legacy"
    if value != "pi" and value not in PI_ENGINE_VALUES and value != "legacy":
        raise HTTPException(status_code=400, detail="engine must be 'pi' or 'istara'")
    settings.agentic_engine_default = value
    try:
        _persist_env("AGENTIC_ENGINE_DEFAULT", value)
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist AGENTIC_ENGINE_DEFAULT: %s", exc)
        persisted = False
    return {"status": "switched", "agentic_engine_default": value, "persisted": persisted}


@router.get("/settings/pi-endpoints")
async def list_pi_endpoints(request: Request):
    """List PiModelManager catalog entries (cloud/API endpoints), secrets never included."""
    require_global_role(request, "admin")
    return {
        "endpoints": [endpoint.model_dump() for endpoint in settings.pi_api_endpoints],
        "retirement_note": (
            "Cloud/API endpoints are managed here (Pi model management). The legacy "
            "LLM-server section manages local serving and donated compute only."
        ),
    }


@router.get("/settings/model-management/migration-status")
async def model_management_migration_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Expose secret-free compatibility progress and rollback readiness."""
    require_global_role(request, "admin")
    from sqlalchemy import select

    from app.core.pi_runtime.model_management_compat import plan_migration
    from app.models.llm_server import LLMServer

    result = await db.execute(select(LLMServer).order_by(LLMServer.id))
    return plan_migration(result.scalars().all())


@router.post("/settings/pi-endpoints")
async def add_pi_endpoint(data: PiEndpointRequest, request: Request):
    require_global_role(request, "admin")
    from app.config import PiApiEndpoint

    endpoint_id = data.endpoint_id.strip()
    if not endpoint_id:
        raise HTTPException(status_code=400, detail="endpoint_id is required")
    if endpoint_id == "pi-deepseek-default":
        raise HTTPException(status_code=400, detail="pi-deepseek-default is built in")
    if any(e.endpoint_id == endpoint_id for e in settings.pi_api_endpoints):
        raise HTTPException(status_code=409, detail=f"endpoint {endpoint_id!r} already exists")
    if not data.base_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise HTTPException(status_code=400, detail="base_url must be https (or loopback)")
    if not data.keychain_service.strip():
        raise HTTPException(
            status_code=400,
            detail="keychain_service is required (Pi endpoints resolve secrets via Keychain)",
        )
    try:
        settings.pi_api_endpoints.append(PiApiEndpoint(**data.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        _persist_pi_endpoints()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
        persisted = False
    return {"status": "added", "endpoint_id": endpoint_id, "persisted": persisted}


@router.put("/settings/pi-endpoints/{endpoint_id}")
async def update_pi_endpoint(endpoint_id: str, data: PiEndpointRequest, request: Request):
    require_global_role(request, "admin")
    for index, endpoint in enumerate(settings.pi_api_endpoints):
        if endpoint.endpoint_id == endpoint_id:
            updated = data.model_dump()
            updated["endpoint_id"] = endpoint_id
            from app.config import PiApiEndpoint

            settings.pi_api_endpoints[index] = PiApiEndpoint(**updated)
            try:
                _persist_pi_endpoints()
                persisted = True
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
                persisted = False
            return {"status": "updated", "endpoint_id": endpoint_id, "persisted": persisted}
    raise HTTPException(status_code=404, detail=f"endpoint {endpoint_id!r} not found")


@router.delete("/settings/pi-endpoints/{endpoint_id}")
async def delete_pi_endpoint(endpoint_id: str, request: Request):
    require_global_role(request, "admin")
    before = len(settings.pi_api_endpoints)
    settings.pi_api_endpoints = [
        endpoint for endpoint in settings.pi_api_endpoints if endpoint.endpoint_id != endpoint_id
    ]
    if len(settings.pi_api_endpoints) == before:
        raise HTTPException(status_code=404, detail=f"endpoint {endpoint_id!r} not found")
    try:
        _persist_pi_endpoints()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
        persisted = False
    return {"status": "deleted", "endpoint_id": endpoint_id, "persisted": persisted}
