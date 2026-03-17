"""Settings and system info API routes."""

from fastapi import APIRouter

from app.config import settings
from app.core.hardware import detect_hardware, recommend_model
from app.core.ollama import ollama

router = APIRouter()


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
                "reclaw_ram_budget_gb": profile.reclaw_ram_budget_gb,
                "cpu_cores": profile.cpu_cores,
                "cpu_arch": profile.cpu_arch,
                "reclaw_cpu_budget_cores": profile.reclaw_cpu_budget_cores,
                "gpu": {
                    "vendor": profile.gpu.vendor,
                    "name": profile.gpu.name,
                    "vram_mb": profile.gpu.vram_mb,
                } if profile.gpu else None,
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
    """Get available and active models."""
    healthy = await ollama.health()
    if not healthy:
        return {
            "status": "offline",
            "models": [],
            "active_model": _active_model(),
        }

    models = await ollama.list_models()
    return {
        "status": "online",
        "models": models,
        "active_model": _active_model(),
        "embed_model": _embed_model(),
    }


@router.post("/settings/model")
async def switch_model(model_name: str):
    """Switch the active model (pulls if using Ollama)."""
    models = await ollama.list_models()
    model_names = [m.get("name", "") for m in models]

    if model_name not in model_names and settings.llm_provider == "ollama":
        try:
            async for _progress in ollama.pull_model(model_name):
                pass
            return {
                "status": "pulled",
                "model": model_name,
                "message": f"Model {model_name} pulled and ready.",
            }
        except Exception as e:
            return {
                "status": "error",
                "model": model_name,
                "message": f"Failed to pull model: {e}",
            }

    env_var = "LMSTUDIO_MODEL" if settings.llm_provider == "lmstudio" else "OLLAMA_MODEL"
    return {
        "status": "switched",
        "model": model_name,
        "message": f"Model {model_name} is available. Update {env_var} in .env to persist across restarts.",
    }


@router.get("/settings/status")
async def system_status():
    """Get overall system status."""
    llm_healthy = await ollama.health()

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "provider": settings.llm_provider,
        "services": {
            "backend": "running",
            "llm": "connected" if llm_healthy else "disconnected",
        },
        "config": {
            "model": _active_model(),
            "embed_model": _embed_model(),
            "rag_chunk_size": settings.rag_chunk_size,
            "rag_top_k": settings.rag_top_k,
        },
    }
