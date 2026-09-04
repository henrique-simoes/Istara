"""Shared helpers for Istara compute registry routing and model serving."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("app.core.compute_registry")

TRANSIENT_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
TRANSIENT_CHAT_MAX_ATTEMPTS = 5
TRANSIENT_CHAT_BASE_DELAY_S = 0.25
TRANSIENT_CHAT_MAX_DELAY_S = 2.0
LMSTUDIO_MODEL_LOAD_LOCK = asyncio.Lock()
_LOCAL_RESOURCE_SNAPSHOT: dict[str, Any] | None = None
PROVIDER_ALIASES = {
    "openai": "openai_compat",
    "openai-compatible": "openai_compat",
    "openai_compatible": "openai_compat",
    "lm_studio": "lmstudio",
    "lm-studio": "lmstudio",
    "llama.cpp": "llamacpp",
    "llama-cpp": "llamacpp",
    "mlx_lm": "mlx",
    "anthropic-compatible": "anthropic_compat",
    "anthropic_compatible": "anthropic_compat",
}


def normalize_provider_type(provider_type: str | None) -> str:
    requested = (provider_type or "").strip().lower()
    return PROVIDER_ALIASES.get(requested, requested)


def infer_provider_type(provider_type: str | None, host: str | None) -> str:
    """Infer the provider contract from an LLM server URL when the label is ambiguous."""
    requested = normalize_provider_type(provider_type)
    if not host:
        return requested or "openai_compat"
    if requested and requested != "ollama":
        return requested

    parsed = urlparse(host if "://" in host else f"http://{host}")
    path = parsed.path.rstrip("/")
    hostname = parsed.hostname or ""
    port = parsed.port

    if "generativelanguage.googleapis.com" in hostname or path.endswith("/openai"):
        return "gemini_openai"
    if "anthropic.com" in hostname:
        return "anthropic"
    if port == 1234:
        return "lmstudio"
    if path.endswith("/v1"):
        return "openai_compat"
    if port == 11434:
        return "ollama"
    return requested or "openai_compat"


def _normalize_hostname(hostname: str | None) -> str:
    return (hostname or "").strip().lower().rstrip(".")


def _local_machine_aliases() -> set[str]:
    """Return passive hostname/IP aliases for this machine.

    This intentionally uses local OS interface data only. It lets the compute
    pool recognize that ``localhost`` and LAN IP aliases are the same physical
    host without guessing that two remote machines with similar models are one
    machine.
    """
    aliases = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    host_candidates = {
        _normalize_hostname(socket.gethostname()),
        _normalize_hostname(socket.getfqdn()),
    }
    for hostname in list(host_candidates):
        if not hostname:
            continue
        aliases.add(hostname)
        try:
            for info in socket.getaddrinfo(hostname, None):
                aliases.add(_normalize_hostname(info[4][0].split("%", 1)[0]))
        except Exception:
            pass

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        sock.connect(("8.8.8.8", 80))
        aliases.add(_normalize_hostname(sock.getsockname()[0]))
    except Exception:
        pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    try:
        import psutil

        for addresses in psutil.net_if_addrs().values():
            for address in addresses:
                value = _normalize_hostname(getattr(address, "address", "").split("%", 1)[0])
                if value:
                    aliases.add(value)
    except Exception:
        pass

    return aliases


def _canonical_endpoint_hostname(hostname: str | None) -> str:
    normalized = _normalize_hostname(hostname)
    if not normalized:
        return ""
    if normalized in _local_machine_aliases():
        return "local"
    return normalized


def _server_endpoint_identity(
    host: str,
    *,
    source: str | None = None,
) -> tuple[str, str, int | None, str]:
    """Canonicalize an LLM server endpoint enough to catch accidental duplicates."""
    parsed = urlparse(host if "://" in host else f"http://{host}")
    path = parsed.path.rstrip("/")
    if path == "/v1":
        path = ""
    hostname = "local" if source == "local" else _canonical_endpoint_hostname(parsed.hostname)
    return (
        (parsed.scheme or "http").lower(),
        hostname,
        parsed.port,
        path,
    )


def _redacted_endpoint_for_log(host: str | None) -> str:
    """Return an endpoint label safe for logs and benchmark output."""
    if not host:
        return "[no-endpoint]"
    parsed = urlparse(host if "://" in host else f"http://{host}")
    scheme = (parsed.scheme or "http").lower()
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/")
    return f"{scheme}://[redacted-host]{port}{path}"


def _openai_model_ids(data: dict | list) -> list[str]:
    raw_models = data.get("data") if isinstance(data, dict) else data
    if not isinstance(raw_models, list):
        return []
    return [
        model_id
        for model in raw_models
        if isinstance(model, dict)
        for model_id in [model.get("id")]
        if isinstance(model_id, str) and model_id.strip()
    ]


def _ollama_model_names(data: dict) -> list[str]:
    raw_models = data.get("models")
    if not isinstance(raw_models, list):
        return []
    return [
        name
        for model in raw_models
        if isinstance(model, dict)
        for name in [model.get("name")]
        if isinstance(name, str) and name.strip()
    ]


def _unique_model_names(names: list[Any] | tuple[Any, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        text = str(name).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _error_text(error: Exception) -> str:
    parts = [str(error)]
    response = getattr(error, "response", None)
    if response is not None:
        try:
            parts.append(response.text)
        except Exception:
            pass
    return " ".join(part for part in parts if part).lower()


def _looks_like_model_availability_error(error: Exception) -> bool:
    text = _error_text(error)
    return any(
        marker in text
        for marker in (
            "invalid model identifier",
            "model_not_found",
            "model does not exist",
            "no models loaded",
            "no model loaded",
            "please load a model",
            "model is not loaded",
            "model not loaded",
            "not currently loaded",
            "model not found",
        )
    )


def _looks_like_context_length_error(error: Exception) -> bool:
    text = _error_text(error)
    return any(
        marker in text
        for marker in (
            "greater than the context length",
            "context length",
            "context size",
            "context window",
            "context has been exceeded",
            "maximum context",
            "prompt is too long",
            "too many tokens",
            "maximum sequence length",
        )
    )


def _positive_number(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def _hydrate_local_resources(node: ComputeNode) -> None:
    """Fill local-node hardware fields so compute stats do not report 0 GB."""
    global _LOCAL_RESOURCE_SNAPSHOT
    if node.source != "local":
        return
    if node.ram_total_gb and node.ram_available_gb and node.cpu_cores:
        return
    if _LOCAL_RESOURCE_SNAPSHOT:
        if not node.ram_total_gb:
            node.ram_total_gb = _LOCAL_RESOURCE_SNAPSHOT.get("ram_total_gb", 0) or 0
        if not node.ram_available_gb:
            node.ram_available_gb = _LOCAL_RESOURCE_SNAPSHOT.get("ram_available_gb", 0) or 0
        if not node.cpu_cores:
            node.cpu_cores = _LOCAL_RESOURCE_SNAPSHOT.get("cpu_cores", 0) or 0
        if not node.cpu_load_pct:
            node.cpu_load_pct = _LOCAL_RESOURCE_SNAPSHOT.get("cpu_load_pct", 0) or 0
        if not node.gpu_name:
            node.gpu_name = str(_LOCAL_RESOURCE_SNAPSHOT.get("gpu_name", "") or "")
        if not node.gpu_vram_mb:
            node.gpu_vram_mb = int(_LOCAL_RESOURCE_SNAPSHOT.get("gpu_vram_mb", 0) or 0)
        return
    try:
        from app.core.hardware import detect_hardware

        profile = detect_hardware()
        _LOCAL_RESOURCE_SNAPSHOT = {
            "ram_total_gb": profile.total_ram_gb,
            "ram_available_gb": profile.available_ram_gb,
            "cpu_cores": profile.cpu_cores,
            "cpu_load_pct": 0,
            "gpu_name": profile.gpu.name if profile.gpu else "",
            "gpu_vram_mb": profile.gpu.vram_mb if profile.gpu else 0,
        }
        if not node.ram_total_gb:
            node.ram_total_gb = profile.total_ram_gb
        if not node.ram_available_gb:
            node.ram_available_gb = profile.available_ram_gb
        if not node.cpu_cores:
            node.cpu_cores = profile.cpu_cores
        if profile.gpu:
            if not node.gpu_name:
                node.gpu_name = profile.gpu.name
            if not node.gpu_vram_mb:
                node.gpu_vram_mb = profile.gpu.vram_mb
        return
    except Exception:
        pass

    try:
        import os

        import psutil

        mem = psutil.virtual_memory()
        cpu_load_pct = psutil.cpu_percent(interval=0)
        _LOCAL_RESOURCE_SNAPSHOT = {
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_available_gb": round(mem.available / (1024**3), 1),
            "cpu_cores": os.cpu_count() or 1,
            "cpu_load_pct": round(cpu_load_pct, 1),
            "gpu_name": "",
            "gpu_vram_mb": 0,
        }
        if not node.ram_total_gb:
            node.ram_total_gb = _LOCAL_RESOURCE_SNAPSHOT["ram_total_gb"]
        if not node.ram_available_gb:
            node.ram_available_gb = _LOCAL_RESOURCE_SNAPSHOT["ram_available_gb"]
        if not node.cpu_cores:
            node.cpu_cores = _LOCAL_RESOURCE_SNAPSHOT["cpu_cores"]
        if not node.cpu_load_pct:
            node.cpu_load_pct = _LOCAL_RESOURCE_SNAPSHOT["cpu_load_pct"]
    except Exception:
        pass
