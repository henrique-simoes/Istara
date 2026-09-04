"""Settings and system info API routes."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PiApiEndpoint, settings
from app.core.env_persistence import persist_env_value
from app.core.hardware import detect_hardware, recommend_model
from app.core.ollama import ollama
from app.core.permissions import require_global_role, require_project_access
from app.core.pi_runtime.endpoint_policy import (
    custody_pi_endpoint_credentials,
    pi_endpoint_credential_status,
    prepare_pi_endpoint_payload,
)
from app.core.runtime_freshness import detect_runtime_freshness
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/settings/audio-model")
async def get_audio_model_settings(request: Request):
    """Return the governed audio profile without secrets or provider URLs.

    Fail closed: an unsupported provider or an invalid profile combination is
    a typed 503 (``error.type=audio_profile_invalid``) — never a crash and
    never a silent text-model fallback, mirroring the petals bridge's
    ``PetalsUnavailable`` contract.
    """
    require_global_role(request, "admin")
    from app.core.audio_model_profile import audio_profile_error_reason, configured_audio_profile

    try:
        profile = configured_audio_profile(settings)
    except ValueError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "configured": False,
                "profile": None,
                "fallback": "unavailable",
                "error": {
                    "type": "audio_profile_invalid",
                    "reason": audio_profile_error_reason(exc),
                },
                "research_data_status": "provisional_until_review",
            },
        )
    return {
        "configured": profile is not None,
        "profile": profile.public_dict() if profile else None,
        "fallback": "unavailable",
        "research_data_status": "provisional_until_review",
    }


class StrictRoutingRequest(BaseModel):
    enabled: bool


class DataIntegrityQuarantineRequest(BaseModel):
    dry_run: bool = True


class FileEncryptionEnableRequest(BaseModel):
    confirm_loss_warning: bool = False


class FileEncryptionRotateRequest(BaseModel):
    confirm_rotation: bool = False


def _persist_env(key: str, value: str) -> bool:
    """Persist a runtime setting when storage is writable.

    Read-only deployments are valid (and common for the QA/release image), so
    an OS-level write failure must not turn an otherwise valid in-memory
    settings change into a 500. Unexpected exceptions still propagate so real
    persistence bugs remain visible.
    """
    try:
        persist_env_value(key, value)
    except OSError as exc:
        logger.warning(
            "Runtime setting %s changed in memory but could not be persisted: %s",
            key,
            exc,
        )
        return False
    return True


def _active_model() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_model
    return settings.ollama_model


def _embed_model() -> str:
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    return get_active_embedding_profile().model_id


def _global_agentic_engine() -> str:
    """Return the public, normalized global agent engine choice."""
    from app.core.pi_replacement import PI_ENGINE_VALUES

    value = str(getattr(settings, "agentic_engine_default", "legacy") or "").strip().lower()
    return "pi" if value in PI_ENGINE_VALUES else "legacy"


async def _pi_catalog_info() -> list[dict]:
    """W8 UX parity: the Pi identity catalog merged into model pickers.

    Read-only identity/capability view (endpoint ids and model names only —
    never URLs or keys). A fresh manager per call keeps the LLMServer
    projection current. Pi is the canonical model-management authority, so a
    projection/catalog failure must be explicit rather than degraded into a
    misleading legacy-only response.
    """
    try:
        from dataclasses import asdict

        from app.core.pi_runtime.model_manager import PiModelManager

        manager = PiModelManager()
        await manager.ensure_db_projection()
        return [asdict(info) for info in manager.catalog()]
    except Exception as exc:
        logger.warning("pi catalog unavailable for settings inventory", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "pi_catalog_unavailable",
                "message": "Pi model catalog is unavailable.",
            },
        ) from exc


def _pi_default_info(catalog: list[dict]) -> tuple[str | None, str | None]:
    """Return the effective credential-ready provider default without secrets."""
    from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID, PiEndpointResolver

    by_id = {str(item.get("endpoint_id") or ""): item for item in catalog}
    configured = {endpoint.endpoint_id: endpoint for endpoint in PiEndpointResolver().configured()}

    def is_ready(item: dict | None) -> bool:
        if item is None:
            return False
        status = str(item.get("credential_status") or "").strip().lower()
        if not status:
            endpoint = configured.get(str(item.get("endpoint_id") or ""))
            if endpoint is None:
                return False
            try:
                status = pi_endpoint_credential_status(endpoint)
            except Exception:
                logger.warning(
                    "pi default credential state unavailable for %s",
                    endpoint.endpoint_id,
                    exc_info=True,
                )
                return False
        return status in {"ready", "stored"}

    requested = str(getattr(settings, "pi_default_endpoint_id", "") or "").strip()
    if requested and requested in by_id:
        item = by_id[requested]
        if not (settings.llm_provider_contract_stub and item.get("kind") == "local") and is_ready(
            item
        ):
            return requested, str(item.get("model") or "") or None
    for endpoint in settings.pi_api_endpoints:
        item = by_id.get(endpoint.endpoint_id)
        if (
            item is not None
            and not (settings.llm_provider_contract_stub and item.get("kind") == "local")
            and is_ready(item)
        ):
            return endpoint.endpoint_id, str(item.get("model") or "") or None
    fallback = by_id.get(DEFAULT_ENDPOINT_ID)
    if (
        fallback is not None
        and not (settings.llm_provider_contract_stub and fallback.get("kind") == "local")
        and is_ready(fallback)
    ):
        return DEFAULT_ENDPOINT_ID, str(fallback.get("model") or "") or None
    return None, None


def _pi_model_management_required() -> JSONResponse:
    """Fail closed for retired classical model-management writes.

    The routes remain as explicit compatibility adapters so old clients get a
    stable, actionable response instead of a 404. They intentionally perform
    no discovery, pulling, provider reconstruction, settings mutation, or
    persistence. Local serving and donated-compute lifecycle APIs remain
    separate transport infrastructure; canonical model/provider writes live
    under ``/settings/pi-endpoints``.
    """
    replacement = "/api/settings/pi-endpoints"
    return JSONResponse(
        status_code=410,
        headers={
            "Deprecation": "true",
            "Link": f'<{replacement}>; rel="successor-version"',
        },
        content={
            "error": "pi_model_management_required",
            "replacement": replacement,
            "message": "Model and provider writes are managed by Pi Model Management.",
        },
    )


def _guard_pi_endpoint_mutation(endpoint_id: str) -> None:
    """Keep reserved Pi identities outside user-managed CRUD.

    POST already rejects these names, but PUT/DELETE must protect the same
    namespace when a malformed or legacy settings payload contains one.  The
    built-in resolver endpoint is likewise not a user-owned row.
    """
    from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID
    from app.core.pi_runtime.model_manager import is_reserved_petals_endpoint_id

    normalized = str(endpoint_id or "").strip()
    if is_reserved_petals_endpoint_id(normalized):
        raise HTTPException(
            status_code=400,
            detail="pi-petals-* endpoint IDs are reserved for consented Petals donors",
        )
    if normalized == DEFAULT_ENDPOINT_ID:
        raise HTTPException(status_code=400, detail=f"{DEFAULT_ENDPOINT_ID} is built in")


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
    if settings.llm_provider_contract_stub:
        # The deterministic QA transport validates wiring and embeddings only.
        # It is deliberately invisible to every chat/model-source resolver and
        # must not become user-visible chat readiness through cached node state.
        chat_ready = False
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
        pi_catalog = await _pi_catalog_info()
        default_endpoint_id, default_model = _pi_default_info(pi_catalog)
        return {
            "status": "offline",
            "provider": settings.llm_provider,
            "models": [],
            "active_model": _active_model(),
            "embed_model": _embed_model(),
            "agentic_engine_default": _global_agentic_engine(),
            "pi_catalog": pi_catalog,
            "default_endpoint_id": default_endpoint_id,
            "default_model": default_model,
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

    pi_catalog = await _pi_catalog_info()
    default_endpoint_id, default_model = _pi_default_info(pi_catalog)
    return {
        "status": "online",
        "provider": settings.llm_provider,
        "models": enriched,
        "active_model": active,
        "embed_model": _embed_model(),
        "agentic_engine_default": _global_agentic_engine(),
        "pi_catalog": pi_catalog,
        "default_endpoint_id": default_endpoint_id,
        "default_model": default_model,
    }


@router.post("/settings/model")
async def switch_model(model_name: str, request: Request):
    """Deprecated compatibility write; Pi Model Management is authoritative."""
    require_global_role(request, "admin")
    return _pi_model_management_required()


@router.post("/settings/provider")
async def switch_provider(provider: str, request: Request):
    """Deprecated compatibility write; Pi Model Management is authoritative."""
    require_global_role(request, "admin")
    return _pi_model_management_required()


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
        persisted = _persist_env("STRICT_AUTO_ROUTING", str(enabled).lower())
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
        # Engine identity is a safe routing label, not provider/model/secret
        # configuration; expose it so non-admins can understand the read-only
        # Agentic Core section without receiving admin model inventory.
        "agentic_engine_default": _global_agentic_engine(),
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


@router.get("/settings/security-integrity")
async def security_integrity(request: Request):
    """Return admin-only, value-free runtime security integrity signals."""
    require_global_role(request, "admin")
    from app.core.field_encryption import encryption_health_snapshot
    from app.core.telemetry import telemetry_recorder

    return {
        "field_encryption": encryption_health_snapshot(),
        "telemetry_writes": telemetry_recorder.write_health_snapshot(),
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
    persisted = _persist_env("TELEMETRY_ENABLED", str(enabled).lower())
    message = f"Telemetry {'enabled' if enabled else 'disabled'}."
    if not persisted:
        message += " The runtime value is active for this process; persistence is unavailable."
    return {
        "telemetry_enabled": enabled,
        "message": message,
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


class PiOAuthStartRequest(BaseModel):
    provider: str
    # Pi's OpenAI Codex loader exposes two choices: browser PKCE or headless
    # device-code. Other providers use the method advertised by the catalog.
    method: str = "device_code"


class PiOAuthPollRequest(BaseModel):
    provider: str
    flow_id: str | None = None


class PiOAuthManualCodeRequest(BaseModel):
    provider: str
    flow_id: str | None = None
    authorization_input: str = Field(..., min_length=1, max_length=4096)


class PiOAuthPKCECallbackRequest(BaseModel):
    code: str
    state: str | None = None


class PiEndpointRequest(BaseModel):
    endpoint_id: str
    provider_kind: str = "openai_compat"
    base_url: str = ""
    model: str = ""
    keychain_service: str = ""  # required: every Pi endpoint resolves its secret via Keychain
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
    # Catalog-driven setup (DEC-3): select a Pi provider + model id instead of
    # typing an endpoint URL. The backend fills base_url/costs/capabilities
    # from the canonical Pi catalog.
    pi_provider: str = ""
    pi_model: str = ""
    api_key: str = ""  # optional: written to Keychain custody when provided
    supports_vision: bool = False
    supports_reasoning: bool | None = None
    auth_provider: str = ""
    auth_method: str = "api_key"
    oauth_flow_id: str = ""


class PiDefaultEndpointRequest(BaseModel):
    endpoint_id: str


class PiResearchEnsembleRequest(BaseModel):
    endpoint_ids: list[str] = Field(default_factory=list)


def _persist_pi_endpoints() -> None:
    import json as _json

    payload = [endpoint.model_dump() for endpoint in settings.pi_api_endpoints]
    _persist_env("PI_API_ENDPOINTS", _json.dumps(payload))


def _persist_pi_default_endpoint() -> None:
    _persist_env("PI_DEFAULT_ENDPOINT_ID", settings.pi_default_endpoint_id)


def _persist_pi_research_endpoints() -> None:
    import json as _json

    _persist_env("PI_RESEARCH_ENDPOINT_IDS", _json.dumps(settings.pi_research_endpoint_ids))


def _validated_research_endpoint_ids(endpoint_ids: list[str]) -> list[str]:
    normalized = [str(endpoint_id).strip() for endpoint_id in endpoint_ids]
    if any(not endpoint_id for endpoint_id in normalized):
        raise HTTPException(status_code=400, detail="empty_research_endpoint_id")
    if len(set(normalized)) != len(normalized):
        raise HTTPException(status_code=400, detail="duplicate_research_endpoint_id")

    configured = {endpoint.endpoint_id: endpoint for endpoint in settings.pi_api_endpoints}
    seen_models: set[str] = set()
    for endpoint_id in normalized:
        endpoint = configured.get(endpoint_id)
        if endpoint is None:
            raise HTTPException(status_code=400, detail="unknown_research_endpoint_id")
        if pi_endpoint_credential_status(endpoint) == "missing":
            raise HTTPException(status_code=400, detail="research_endpoint_credential_missing")
        model_identity = endpoint.model.strip().casefold()
        if model_identity in seen_models:
            raise HTTPException(status_code=400, detail="duplicate_research_model_identity")
        seen_models.add(model_identity)
    return normalized


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
        persisted = _persist_env("AGENTIC_ENGINE_DEFAULT", value)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist AGENTIC_ENGINE_DEFAULT: %s", exc)
        persisted = False
    return {"status": "switched", "agentic_engine_default": value, "persisted": persisted}


@router.get("/settings/pi-catalog")
async def get_pi_catalog(request: Request):
    """Full Pi provider/model catalog for the settings UI (no secrets).

    Includes every provider and model the standalone Pi supports, with login
    methods (api_key/oauth), env vars and OAuth flow hints so the UI can offer
    a selectable list + autocomplete with zero manual endpoint typing.
    """
    require_global_role(request, "admin")
    try:
        from app.core.pi_runtime.catalog import pi_catalog_json

        catalog = pi_catalog_json()
        return {"providers": catalog, "total_models": sum(len(p["models"]) for p in catalog)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("pi catalog failed")
        raise HTTPException(status_code=500, detail=f"catalog_unavailable:{exc}") from exc


@router.get("/settings/pi-oauth/flows")
async def list_oauth_flows(request: Request):
    """Status of active Pi OAuth login flows (device-code / PKCE)."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import oauth_status

    return {"flows": oauth_status()}


@router.post("/settings/pi-oauth/start")
async def start_oauth_flow(data: PiOAuthStartRequest, request: Request):
    """Start one of the login methods exposed by the standalone Pi loader."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import (
        start_anthropic_browser_flow,
        start_device_flow,
        start_openai_browser_flow,
        start_pkce_flow,
    )

    provider = data.provider.strip().lower()
    method = data.method.strip().lower() or "device_code"
    try:
        if provider in {"openai", "openai-codex"}:
            if method == "browser":
                # Pi's registered browser redirect is localhost:1455. The web
                # UI also exposes Pi's manual paste fallback when no local Pi
                # callback listener is present.
                flow = start_openai_browser_flow("http://localhost:1455/auth/callback")
            elif method in {"device_code", "headless"}:
                flow = start_device_flow("openai-codex")
            else:
                raise ValueError("unsupported_openai_oauth_method")
        elif provider == "openrouter":
            if method not in {"browser", "pkce", "device_code"}:
                raise ValueError("unsupported_openrouter_oauth_method")
            flow = start_pkce_flow("http://localhost:8090/callback")
        elif provider == "anthropic":
            if method != "browser":
                raise ValueError("provider_supports_browser_only")
            flow = start_anthropic_browser_flow("http://localhost:53692/callback")
        else:
            if method != "device_code":
                raise ValueError("provider_supports_device_code_only")
            flow = start_device_flow(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "flow_id": flow.flow_id,
        "provider": flow.provider,
        "oauth_provider": flow.oauth_provider or flow.provider,
        "method": flow.method,
        "flow_type": flow.flow_type,
        "user_code": flow.user_code,
        "verification_uri": flow.verification_uri,
        "verification_uri_complete": flow.verification_uri_complete,
        "auth_url": flow.auth_url,
        "expires_at": flow.expires_at,
    }


@router.get("/settings/pi-oauth/openai/callback", response_class=HTMLResponse)
async def openai_oauth_callback(
    code: str | None = None, state: str | None = None, error: str | None = None
):
    """Public OAuth redirect; state is the authorization boundary.

    This route intentionally has no bearer-auth dependency because OpenAI's
    browser redirect cannot carry Istara's session token. It can only complete
    the short-lived state generated for an already-admin-authorized flow.
    """
    from app.core.pi_runtime.oauth import browser_callback_page, finish_openai_browser_flow

    if error:
        return HTMLResponse(
            browser_callback_page(False, "The provider did not approve the login."), status_code=400
        )
    if not code or not state:
        return HTMLResponse(
            browser_callback_page(False, "The provider callback was missing its code or state."),
            status_code=400,
        )
    try:
        finish_openai_browser_flow(code, state)
    except ValueError:
        return HTMLResponse(
            browser_callback_page(
                False, "The login could not be verified. Return to Istara and start again."
            ),
            status_code=400,
        )
    return HTMLResponse(
        browser_callback_page(True, "OpenAI Codex is now connected to this Istara server.")
    )


@router.get("/settings/pi-oauth/{provider}/callback", response_class=HTMLResponse)
async def pi_browser_oauth_callback(
    provider: str, code: str | None = None, state: str | None = None, error: str | None = None
):
    """State-verified browser callback for the other Pi PKCE loaders."""
    from app.core.pi_runtime.oauth import browser_callback_page, finish_browser_flow

    if error or not code or not state:
        return HTMLResponse(
            browser_callback_page(False, "The provider did not complete the login."),
            status_code=400,
        )
    try:
        finish_browser_flow(provider.strip().lower(), code, state)
    except ValueError:
        return HTMLResponse(
            browser_callback_page(
                False, "The login could not be verified. Return to Istara and start again."
            ),
            status_code=400,
        )
    return HTMLResponse(
        browser_callback_page(True, "The provider is now connected to this Istara server.")
    )


@router.post("/settings/pi-oauth/manual")
async def complete_manual_oauth(data: PiOAuthManualCodeRequest, request: Request):
    """Complete Pi's browser flow with a pasted code/redirect URL fallback."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import complete_browser_flow, oauth_status

    try:
        flow = complete_browser_flow(
            data.provider.strip().lower(), data.authorization_input, data.flow_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"flows": oauth_status(flow.provider)}


@router.post("/settings/pi-oauth/poll")
async def poll_oauth_flow(data: PiOAuthPollRequest, request: Request):
    """Poll an active device flow; returns approved status + masked token when
    the user finished the browser step."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import oauth_status, poll_device_flow

    provider = data.provider.strip().lower()
    try:
        flows = oauth_status(provider, data.flow_id)
        if not flows:
            raise ValueError("no_active_flow")
        active = flows[0]
        if active.get("flow_type") == "device_code":
            poll_device_flow(provider, data.flow_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="no_active_flow")
    flows = oauth_status(provider, data.flow_id)
    return {"flows": flows}


@router.post("/settings/pi-oauth/cancel")
async def cancel_oauth_flow(data: PiOAuthPollRequest, request: Request):
    """Cancel an active flow."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import cancel_flow

    cancel_flow(data.provider.strip().lower(), data.flow_id)
    return {"status": "cancelled", "flow_id": data.flow_id}


@router.post("/settings/pi-oauth/pkce/callback")
async def pkce_callback(data: PiOAuthPKCECallbackRequest, request: Request):
    """Exchange an OpenRouter authorization code (PKCE) for an API key."""
    require_global_role(request, "admin")
    from app.core.pi_runtime.oauth import finish_pkce_flow, oauth_status

    try:
        finish_pkce_flow(data.code, data.state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"flows": oauth_status("openrouter")}


@router.get("/settings/pi-endpoints")
async def list_pi_endpoints(request: Request):
    """List Pi endpoint identities; API keys and encrypted OAuth blobs never leave the server."""
    require_global_role(request, "admin")
    public_endpoints = []
    for endpoint in settings.pi_api_endpoints:
        view = endpoint.model_dump()
        view.pop("oauth_credential_encrypted", None)
        view["credential_status"] = pi_endpoint_credential_status(endpoint)
        public_endpoints.append(view)
    default_endpoint_id, default_model = _pi_default_info(public_endpoints)
    return {
        "endpoints": public_endpoints,
        "default_endpoint_id": default_endpoint_id,
        "default_model": default_model,
        "research_endpoint_ids": list(settings.pi_research_endpoint_ids),
        "research_selection_mode": (
            "preferred_then_automatic" if settings.pi_research_endpoint_ids else "automatic"
        ),
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

    endpoint_id = data.endpoint_id.strip()
    if not endpoint_id:
        raise HTTPException(status_code=400, detail="endpoint_id is required")
    from app.core.pi_runtime.model_manager import is_reserved_petals_endpoint_id

    if is_reserved_petals_endpoint_id(endpoint_id):
        raise HTTPException(
            status_code=400,
            detail="pi-petals-* endpoint IDs are reserved for consented Petals donors",
        )
    if endpoint_id == "pi-deepseek-default":
        raise HTTPException(status_code=400, detail="pi-deepseek-default is built in")
    if any(e.endpoint_id == endpoint_id for e in settings.pi_api_endpoints):
        raise HTTPException(status_code=409, detail=f"endpoint {endpoint_id!r} already exists")

    payload = prepare_pi_endpoint_payload(data)
    custody_pi_endpoint_credentials(data, payload)
    existing_default = str(getattr(settings, "pi_default_endpoint_id", "") or "").strip()
    existing_ids = {endpoint.endpoint_id for endpoint in settings.pi_api_endpoints}
    if existing_default not in existing_ids:
        existing_default = (
            settings.pi_api_endpoints[0].endpoint_id if settings.pi_api_endpoints else ""
        )
        if existing_default:
            settings.pi_default_endpoint_id = existing_default

    try:
        settings.pi_api_endpoints.append(PiApiEndpoint(**payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        if not existing_default:
            settings.pi_default_endpoint_id = endpoint_id
        _persist_pi_endpoints()
        _persist_pi_default_endpoint()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
        persisted = False
    from app.core.pi_runtime.model_manager import reset_live_settings_catalogs

    reset_live_settings_catalogs()
    added_endpoint = next(
        endpoint for endpoint in settings.pi_api_endpoints if endpoint.endpoint_id == endpoint_id
    )
    return {
        "status": "added",
        "endpoint_id": endpoint_id,
        "persisted": persisted,
        "auth_method": payload.get("auth_method", "api_key"),
        "credential_status": pi_endpoint_credential_status(added_endpoint),
        "default_endpoint_id": settings.pi_default_endpoint_id or None,
        "default_model": next(
            (
                endpoint.model
                for endpoint in settings.pi_api_endpoints
                if endpoint.endpoint_id == settings.pi_default_endpoint_id
            ),
            None,
        ),
    }


@router.post("/settings/pi-default")
async def set_pi_default_endpoint(data: PiDefaultEndpointRequest, request: Request):
    require_global_role(request, "admin")
    endpoint_id = data.endpoint_id.strip()
    endpoint = next(
        (item for item in settings.pi_api_endpoints if item.endpoint_id == endpoint_id),
        None,
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail=f"endpoint {endpoint_id!r} not found")
    settings.pi_default_endpoint_id = endpoint_id
    try:
        _persist_pi_default_endpoint()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_DEFAULT_ENDPOINT_ID: %s", exc)
        persisted = False
    from app.core.pi_runtime.model_manager import reset_live_settings_catalogs

    reset_live_settings_catalogs()
    return {
        "status": "switched",
        "default_endpoint_id": endpoint_id,
        "default_model": endpoint.model,
        "persisted": persisted,
    }


@router.put("/settings/pi-research-ensemble")
async def set_pi_research_ensemble(data: PiResearchEnsembleRequest, request: Request):
    """Persist ordered coder preferences without replacing healthy donor fallback."""
    require_global_role(request, "admin")
    endpoint_ids = _validated_research_endpoint_ids(data.endpoint_ids)
    settings.pi_research_endpoint_ids = endpoint_ids
    try:
        _persist_pi_research_endpoints()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_RESEARCH_ENDPOINT_IDS: %s", exc)
        persisted = False
    return {
        "status": "updated",
        "endpoint_ids": endpoint_ids,
        "selection_mode": "preferred_then_automatic" if endpoint_ids else "automatic",
        "persisted": persisted,
    }


@router.put("/settings/pi-endpoints/{endpoint_id}")
async def update_pi_endpoint(endpoint_id: str, data: PiEndpointRequest, request: Request):
    require_global_role(request, "admin")
    _guard_pi_endpoint_mutation(endpoint_id)
    for index, endpoint in enumerate(settings.pi_api_endpoints):
        if endpoint.endpoint_id == endpoint_id:
            updated = prepare_pi_endpoint_payload(data, existing=endpoint)
            custody_pi_endpoint_credentials(data, updated, existing=endpoint)
            try:
                replacement = PiApiEndpoint(**updated)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            settings.pi_api_endpoints[index] = replacement
            try:
                _persist_pi_endpoints()
                _persist_pi_default_endpoint()
                persisted = True
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
                persisted = False
            from app.core.pi_runtime.model_manager import reset_live_settings_catalogs

            reset_live_settings_catalogs()
            return {"status": "updated", "endpoint_id": endpoint_id, "persisted": persisted}
    raise HTTPException(status_code=404, detail=f"endpoint {endpoint_id!r} not found")


@router.delete("/settings/pi-endpoints/{endpoint_id}")
async def delete_pi_endpoint(endpoint_id: str, request: Request):
    require_global_role(request, "admin")
    _guard_pi_endpoint_mutation(endpoint_id)
    before = len(settings.pi_api_endpoints)
    settings.pi_api_endpoints = [
        endpoint for endpoint in settings.pi_api_endpoints if endpoint.endpoint_id != endpoint_id
    ]
    if len(settings.pi_api_endpoints) == before:
        raise HTTPException(status_code=404, detail=f"endpoint {endpoint_id!r} not found")
    if getattr(settings, "pi_default_endpoint_id", "") == endpoint_id:
        settings.pi_default_endpoint_id = (
            settings.pi_api_endpoints[0].endpoint_id if settings.pi_api_endpoints else ""
        )
    settings.pi_research_endpoint_ids = [
        item for item in settings.pi_research_endpoint_ids if item != endpoint_id
    ]
    try:
        _persist_pi_endpoints()
        _persist_pi_default_endpoint()
        _persist_pi_research_endpoints()
        persisted = True
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not persist PI_API_ENDPOINTS: %s", exc)
        persisted = False
    from app.core.pi_runtime.model_manager import reset_live_settings_catalogs

    reset_live_settings_catalogs()
    default_endpoint_id, default_model = _pi_default_info(
        [endpoint.model_dump() for endpoint in settings.pi_api_endpoints]
    )
    return {
        "status": "deleted",
        "endpoint_id": endpoint_id,
        "persisted": persisted,
        "default_endpoint_id": default_endpoint_id,
        "default_model": default_model,
        "research_endpoint_ids": list(settings.pi_research_endpoint_ids),
    }
