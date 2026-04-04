"""Settings and system info API routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.hardware import detect_hardware, recommend_model
from app.core.ollama import ollama
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def _persist_env(key: str, value: str) -> None:
    """Update a key in the .env file so the setting survives restarts.

    Creates the key if it doesn't exist, updates it in-place if it does.
    """
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    lines = env_path.read_text().splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        # Ensure trailing newline before appending
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    env_path.write_text("".join(new_lines))


def _active_model() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_model
    return settings.ollama_model


def _embed_model() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_embed_model
    return settings.ollama_embed_model


@router.get("/settings/hardware")
async def get_hardware_info():
    """Get hardware detection results and model recommendation."""
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


@router.get("/settings/models")
async def get_models():
    """Get available and active models.

    For LM Studio, probes the actually loaded model via a minimal chat request
    since /v1/models returns all downloaded (not just loaded) models.
    """
    healthy = await ollama.health()
    if not healthy:
        return {
            "status": "offline",
            "models": [],
            "active_model": _active_model(),
        }

    models = await ollama.list_models()
    active = _active_model()

    # For LM Studio, detect the actually loaded model
    if settings.llm_provider == "lmstudio":
        from app.core.lmstudio import LMStudioClient

        if isinstance(ollama, LMStudioClient):
            loaded = await ollama.detect_loaded_model()
            if loaded and loaded != active:
                settings.lmstudio_model = loaded
                active = loaded
                # Persist so config stays in sync
                try:
                    _persist_env("LMSTUDIO_MODEL", loaded)
                except Exception:
                    pass

    # Enrich each model with provider info from the router.
    # The LLMRouter.list_models() already attaches _server / _server_id;
    # we promote those to public fields and add provider_type.
    from app.core.llm_router import llm_router

    server_map = {s.server_id: s for s in llm_router._servers.values()}
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
        "models": enriched,
        "active_model": active,
        "embed_model": _embed_model(),
    }


@router.post("/settings/model")
async def switch_model(model_name: str, request: Request):
    """Switch the active model at runtime (pulls if using Ollama and not available). Admin only."""
    require_admin_from_request(request)
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
    """Switch the LLM provider at runtime (ollama or lmstudio). Admin only."""
    require_admin_from_request(request)
    from fastapi import HTTPException

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
    from app.core.resource_governor import governor
    from app.agents.orchestrator import meta_orchestrator

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
    from app.core.resource_governor import governor
    from app.agents.orchestrator import meta_orchestrator

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
async def maintenance_status():
    """Check current maintenance mode status."""
    from app.core.resource_governor import governor

    return {
        "maintenance_mode": governor.maintenance_mode,
        "maintenance_reason": governor._maintenance_reason,
    }


@router.get("/settings/integrations-status")
async def integrations_status():
    """Check configuration status of design integrations (Stitch, Figma)."""
    return {
        "stitch_configured": bool(settings.stitch_api_key),
        "figma_configured": bool(settings.figma_api_token),
    }


@router.get("/settings/vector-health")
async def vector_health():
    """Check embedding dimension consistency across vector stores."""
    from app.core.vector_health import check_embedding_dimensions

    return await check_embedding_dimensions()


# ───── Data Management & Migration ─────


@router.get("/settings/data-integrity")
async def check_data_integrity(db: AsyncSession = Depends(get_db)):
    """Run a data integrity check and return health report."""
    from app.core.data_integrity import run_integrity_check

    report = await run_integrity_check(db)
    return report


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

    Re-probes the active LLM provider on demand so the status is always fresh,
    rather than reading the cached health flag from the 60-second background loop.
    Auto-detects the other provider if the current one is unreachable.
    """
    from app.core.ollama import auto_detect_provider
    import app.core.ollama as ollama_mod

    # Re-probe the active provider so the status is always current
    await ollama.check_all_health()
    llm_healthy = await ollama.health()

    # If current provider is down, try auto-detecting the other
    if not llm_healthy:
        await auto_detect_provider()
        llm_healthy = await ollama_mod.ollama.health()

    active = _active_model()

    # For LM Studio, detect the actually loaded model (not just config)
    if llm_healthy and settings.llm_provider == "lmstudio":
        import app.core.ollama as ollama_mod
        from app.core.lmstudio import LMStudioClient

        client = ollama_mod.ollama
        if isinstance(client, LMStudioClient):
            loaded = await client.detect_loaded_model()
            if loaded and loaded != active:
                settings.lmstudio_model = loaded
                active = loaded
                try:
                    _persist_env("LMSTUDIO_MODEL", loaded)
                except Exception:
                    pass

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "provider": settings.llm_provider,
        "team_mode": settings.team_mode,
        "services": {
            "backend": "running",
            "llm": "connected" if llm_healthy else "disconnected",
        },
        "config": {
            "model": active,
            "embed_model": _embed_model(),
            "rag_chunk_size": settings.rag_chunk_size,
            "rag_top_k": settings.rag_top_k,
        },
    }


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
