"""Model capability detection -- determines what each advertised model can do.

Detects capabilities from:
1. Provider-native metadata (LM Studio /api/v1/models, Ollama /api/show)
2. OpenAI-compatible /v1/models metadata from vLLM, SGLang, llama.cpp, MLX, etc.
3. Anthropic /v1/models metadata
4. Heuristic fallback: parse model name for parameter count, modality, tool support
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_PROVIDERS = {"anthropic", "anthropic_compat"}
OPENAI_COMPATIBLE_PROVIDER_TYPES = {
    "openai_compat",
    "gemini_openai",
    "lmstudio",
    "vllm",
    "sglang",
    "llamacpp",
    "mlx",
    "ollama_openai",
}


@dataclass
class ModelCapability:
    """Capabilities of a single loaded model."""

    name: str
    parameter_count: str = "unknown"  # "0.8B", "1B", "4B", "12B", "27B", "70B"
    context_length: int = 4096
    supports_tools: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    supports_json: bool = False
    quantization: str = ""
    source: str = ""
    is_loaded: bool | None = None
    trained_context_length: int | None = None
    loaded_context_length: int | None = None
    loadable: bool | None = None
    endpoint_family: str = "openai"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parameter_count": self.parameter_count,
            "context_length": self.context_length,
            "supports_tools": self.supports_tools,
            "supports_vision": self.supports_vision,
            "supports_audio": self.supports_audio,
            "supports_json": self.supports_json,
            "quantization": self.quantization,
            "is_loaded": self.is_loaded,
            "source": self.source,
            "trained_context_length": self.trained_context_length,
            "loaded_context_length": self.loaded_context_length,
            "loadable": self.loadable,
            "endpoint_family": self.endpoint_family,
            "modalities": {
                "text": True,
                "vision": self.supports_vision,
                "audio": self.supports_audio,
            },
        }


def provider_auth_headers(provider_type: str, api_key: str = "") -> dict[str, str]:
    """Return provider-specific auth headers for model discovery/inference."""
    if not api_key:
        return {}
    if provider_type in ANTHROPIC_PROVIDERS:
        return {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
    return {"Authorization": f"Bearer {api_key}"}


def detect_from_name(model_name: str) -> ModelCapability:
    """Heuristic detection from model name string."""
    name_lower = model_name.lower()
    cap = ModelCapability(name=model_name)

    # Parameter count from name
    param_match = re.search(r"(\d+\.?\d*)\s*[bB]", model_name)
    if param_match:
        cap.parameter_count = f"{param_match.group(1)}B"

    # Parse numeric param count for decisions
    param_num = 0.0
    if param_match:
        try:
            param_num = float(param_match.group(1))
        except ValueError:
            pass

    # Tool support: models 4B+ generally support tools
    # Known good tool families: qwen, llama-3.1+, mistral, gemma-3
    tool_families = [
        "qwen",
        "llama-3",
        "llama-4",
        "mistral",
        "gemma-3",
        "nemotron",
        "gpt",
        "claude",
    ]
    if param_num >= 4 and any(f in name_lower for f in tool_families):
        cap.supports_tools = True
    elif param_num >= 7:
        cap.supports_tools = True  # Most 7B+ models handle tools

    # Vision support. Provider metadata is preferred, but known VLM families
    # help when a compatible server only exposes OpenAI's sparse /v1/models list.
    if any(
        v in name_lower
        for v in [
            "vl",
            "vision",
            "visual",
            "multimodal",
            "llava",
            "moondream",
            "minicpm-v",
            "pixtral",
            "qwen3.6",
            "claude-3",
            "claude-sonnet",
            "claude-opus",
            "claude-haiku",
        ]
    ):
        cap.supports_vision = True

    if any(a in name_lower for a in ["audio", "omni", "whisper", "ultravox"]):
        cap.supports_audio = True

    if cap.supports_tools or any(j in name_lower for j in ["json", "instruct", "gpt", "claude"]):
        cap.supports_json = True

    # Context length heuristic
    if "claude" in name_lower:
        cap.context_length = 200000
    elif param_num <= 1:
        cap.context_length = 2048
    elif param_num <= 4:
        cap.context_length = 4096
    elif param_num <= 12:
        cap.context_length = 8192
    else:
        cap.context_length = 32768

    # Quantization from name
    quant_match = re.search(
        r"(Q\d+_\w+|q\d+|GGUF|MLX|F16|FP16|INT8|INT4)",
        model_name,
        re.IGNORECASE,
    )
    if quant_match:
        cap.quantization = quant_match.group(1).upper()
    elif "mlx" in name_lower:
        cap.quantization = "MLX"

    cap.trained_context_length = cap.context_length
    return cap


def _first_string(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_context_length(value: object, default: int = 4096) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _context_from_mapping(mapping: object) -> int | None:
    if not isinstance(mapping, dict):
        return None
    exact_keys = {
        "context_length",
        "max_context_length",
        "max_model_len",
        "max_seq_len",
        "max_sequence_length",
        "context_window",
        "n_ctx",
        "num_ctx",
        "ctx_size",
    }
    for key, value in mapping.items():
        normalized = str(key).lower()
        if normalized in exact_keys or normalized.endswith(".context_length"):
            parsed = _coerce_context_length(value, 0)
            if parsed:
                return parsed
    return None


def _context_from_parameter_text(parameters: object) -> int | None:
    if not isinstance(parameters, str):
        return None
    match = re.search(r"(?:num_ctx|n_ctx|ctx_size)\s+(\d+)", parameters)
    if not match:
        return None
    return _coerce_context_length(match.group(1), 0) or None


def _apply_context(
    cap: ModelCapability,
    value: object,
    *,
    loaded: bool = False,
    trained: bool = False,
) -> None:
    parsed = _coerce_context_length(value, 0)
    if not parsed:
        return
    cap.context_length = parsed
    if loaded:
        cap.loaded_context_length = parsed
    if trained or not loaded:
        cap.trained_context_length = parsed


def _apply_capability_metadata(cap: ModelCapability, metadata: object) -> None:
    if isinstance(metadata, dict):
        cap.supports_vision = bool(
            metadata.get("vision")
            or metadata.get("image")
            or metadata.get("images")
            or metadata.get("multimodal")
            or cap.supports_vision
        )
        cap.supports_audio = bool(
            metadata.get("audio")
            or metadata.get("input_audio")
            or metadata.get("audio_input")
            or cap.supports_audio
        )
        cap.supports_tools = bool(
            metadata.get("trained_for_tool_use")
            or metadata.get("tool_use")
            or metadata.get("tools")
            or metadata.get("function_calling")
            or cap.supports_tools
        )
        cap.supports_json = bool(
            metadata.get("json")
            or metadata.get("json_mode")
            or metadata.get("structured_outputs")
            or metadata.get("response_format")
            or cap.supports_json
        )
        return
    if isinstance(metadata, list):
        normalized = {str(item).lower() for item in metadata}
        cap.supports_tools = cap.supports_tools or bool(
            normalized.intersection({"tool", "tools", "tool_use", "function_calling"})
        )
        cap.supports_vision = cap.supports_vision or bool(
            normalized.intersection({"vision", "image", "images", "multimodal"})
        )
        cap.supports_audio = cap.supports_audio or bool(
            normalized.intersection({"audio", "input_audio", "audio_input"})
        )
        cap.supports_json = cap.supports_json or bool(
            normalized.intersection({"json", "json_mode", "structured_outputs"})
        )


def _capability_from_lmstudio_model(model: dict) -> ModelCapability | None:
    model_id = _first_string(model.get("key"), model.get("id"), model.get("name"))
    if not model_id:
        return None

    cap = detect_from_name(model_id)
    cap.source = "lmstudio"
    cap.name = model_id
    cap.endpoint_family = "openai"
    cap.loadable = True

    _apply_context(
        cap,
        model.get("max_context_length") or model.get("context_length"),
        trained=True,
    )

    loaded_instances = model.get("loaded_instances")
    if isinstance(loaded_instances, list):
        cap.is_loaded = len(loaded_instances) > 0
        for instance in loaded_instances:
            if not isinstance(instance, dict):
                continue
            config = instance.get("config")
            if isinstance(config, dict) and config.get("context_length"):
                _apply_context(
                    cap,
                    config.get("context_length"),
                    loaded=True,
                )
                break

    _apply_capability_metadata(cap, model.get("capabilities"))

    model_type = str(model.get("type") or "").lower()
    if model_type == "vlm":
        cap.supports_vision = True
    if model_type == "audio":
        cap.supports_audio = True

    quant = model.get("quantization")
    if isinstance(quant, dict):
        cap.quantization = _first_string(quant.get("name")) or cap.quantization
    elif isinstance(quant, str):
        cap.quantization = quant

    return cap


def _capability_from_openai_model(model: dict, provider_type: str) -> ModelCapability | None:
    model_id = _first_string(model.get("id"), model.get("name"), model.get("model"))
    if not model_id:
        return None

    cap = detect_from_name(model_id)
    cap.source = provider_type
    cap.endpoint_family = "openai"
    cap.loadable = provider_type == "lmstudio"
    _apply_context(
        cap,
        model.get("max_model_len")
        or model.get("max_context_length")
        or model.get("max_tokens")
        or model.get("context_length")
        or model.get("context_window")
        or model.get("n_ctx"),
        trained=True,
    )
    _apply_context(cap, _context_from_mapping(model.get("metadata")), trained=True)
    _apply_capability_metadata(cap, model.get("capabilities"))
    if isinstance(model.get("metadata"), dict):
        _apply_capability_metadata(cap, model["metadata"].get("capabilities"))
    if model.get("loaded") is not None:
        cap.is_loaded = bool(model.get("loaded"))
    model_type = str(model.get("type") or model.get("object") or "").lower()
    if model_type == "vlm":
        cap.supports_vision = True
    if model_type == "audio":
        cap.supports_audio = True
    return cap


def _capability_from_ollama_model(model: dict) -> ModelCapability | None:
    model_id = _first_string(model.get("name"), model.get("model"))
    if not model_id:
        return None
    cap = detect_from_name(model_id)
    cap.source = "ollama"
    cap.endpoint_family = "ollama"
    cap.loadable = True
    cap.is_loaded = False
    details = model.get("details")
    if isinstance(details, dict):
        cap.parameter_count = _first_string(details.get("parameter_size")) or cap.parameter_count
        cap.quantization = _first_string(details.get("quantization_level")) or cap.quantization
    return cap


def _apply_ollama_show_metadata(cap: ModelCapability, data: dict) -> None:
    _apply_capability_metadata(cap, data.get("capabilities"))
    details = data.get("details")
    if isinstance(details, dict):
        cap.parameter_count = _first_string(details.get("parameter_size")) or cap.parameter_count
        cap.quantization = _first_string(details.get("quantization_level")) or cap.quantization
    _apply_context(cap, _context_from_mapping(data.get("model_info")), trained=True)
    _apply_context(cap, _context_from_parameter_text(data.get("parameters")), loaded=True)


async def _detect_ollama_capabilities(client, host: str) -> dict[str, ModelCapability]:
    """Use Ollama's tags/show/ps metadata for trained and loaded context windows."""
    result: dict[str, ModelCapability] = {}
    loaded_names: set[str] = set()
    loaded_context: dict[str, int] = {}

    try:
        ps_resp = await client.get(f"{host}api/ps")
        if ps_resp.status_code == 200:
            ps_data = ps_resp.json()
            for item in ps_data.get("models", []) if isinstance(ps_data, dict) else []:
                if not isinstance(item, dict):
                    continue
                name = _first_string(item.get("name"), item.get("model"))
                if not name:
                    continue
                loaded_names.add(name)
                context = _context_from_mapping(item) or _context_from_mapping(item.get("details"))
                if context:
                    loaded_context[name] = context
    except Exception as e:
        logger.debug(f"Ollama /api/ps discovery failed for {host}: {e}")

    try:
        tags_resp = await client.get(f"{host}api/tags")
        if tags_resp.status_code != 200:
            return result
        tags_data = tags_resp.json()
        raw_models = tags_data.get("models", []) if isinstance(tags_data, dict) else []
        if not isinstance(raw_models, list):
            return result
        for model in raw_models:
            if not isinstance(model, dict):
                continue
            cap = _capability_from_ollama_model(model)
            if not cap:
                continue
            try:
                show_resp = await client.post(f"{host}api/show", json={"model": cap.name})
                if show_resp.status_code == 200:
                    _apply_ollama_show_metadata(cap, show_resp.json())
            except Exception as e:
                logger.debug(f"Ollama /api/show discovery failed for {cap.name}: {e}")
            if cap.name in loaded_names:
                cap.is_loaded = True
            if cap.name in loaded_context:
                _apply_context(cap, loaded_context[cap.name], loaded=True)
            result[cap.name] = cap
    except Exception as e:
        logger.debug(f"Ollama capability discovery failed for {host}: {e}")
    return result


async def _detect_lmstudio_capabilities(client, host: str) -> dict[str, ModelCapability]:
    """Use LM Studio's richer native REST metadata when available."""
    result: dict[str, ModelCapability] = {}
    try:
        resp = await client.get(f"{host}api/v1/models")
        if resp.status_code != 200:
            return result
        data = resp.json()
        raw_models = data.get("models", []) if isinstance(data, dict) else []
        if not isinstance(raw_models, list):
            return result
        for model in raw_models:
            if not isinstance(model, dict):
                continue
            cap = _capability_from_lmstudio_model(model)
            if cap:
                result[cap.name] = cap
    except Exception as e:
        logger.debug(f"LM Studio native capability discovery failed for {host}: {e}")
    return result


def _openai_endpoint(host: str, provider_type: str, suffix: str) -> str:
    from urllib.parse import urlparse

    clean_suffix = suffix.lstrip("/")
    parsed = urlparse(host)
    base_path = parsed.path.rstrip("/")
    if (
        provider_type == "gemini_openai"
        or "generativelanguage.googleapis.com" in (parsed.hostname or "")
        or base_path.endswith("/openai")
        or base_path.endswith("/v1")
    ):
        return clean_suffix
    return f"v1/{clean_suffix}"


async def detect_capabilities_generic(
    host: str | None,
    api_key: str = "",
    provider_type: str = "openai_compat",
    active_probe: bool | None = None,
) -> dict[str, ModelCapability]:
    """Empirically detect model capabilities from any OpenAI-compatible API.

    Follows Berkeley Function Calling Leaderboard (BFCL) patterns:
    1. Metadata discovery (GET /v1/models)
    2. Dynamic probing (test chat completion with dummy tool)
    """
    if not host:
        return {}

    import httpx

    from app.config import settings

    result: dict[str, ModelCapability] = {}
    if active_probe is None:
        active_probe = settings.llm_capability_active_probe_enabled

    # RFC 3986 Normalization for detection client
    if not host.endswith("/"):
        host += "/"

    provider_type = (provider_type or "openai_compat").strip().lower()
    headers = provider_auth_headers(provider_type, api_key)

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        if provider_type == "lmstudio":
            result.update(await _detect_lmstudio_capabilities(client, host))
        if provider_type == "ollama":
            result.update(await _detect_ollama_capabilities(client, host))

        # 1. Metadata Discovery
        try:
            models_path = (
                "api/tags"
                if provider_type == "ollama"
                else _openai_endpoint(host, provider_type, "models")
            )
            resp = await client.get(f"{host}{models_path}")
            if resp.status_code == 200:
                data = resp.json()
                if provider_type == "ollama" and isinstance(data, dict):
                    models = data.get("models", [])
                elif isinstance(data, dict):
                    models = data.get("data", [])
                elif isinstance(data, list):
                    models = data
                else:
                    models = []

                for m in models:
                    if not isinstance(m, dict):
                        continue
                    if provider_type == "ollama":
                        cap = _capability_from_ollama_model(m)
                        if not cap:
                            continue
                        model_id = cap.name
                    else:
                        cap = _capability_from_openai_model(m, provider_type)
                        if not cap:
                            continue
                        model_id = cap.name

                    if model_id not in result:
                        result[model_id] = cap
        except Exception as e:
            logger.debug(f"Metadata discovery failed for {host}: {e}")

        # 2. Dynamic Probing (Active Verification)
        if not active_probe:
            return result
        if provider_type in ANTHROPIC_PROVIDERS:
            return result
        # Select the most likely primary model to probe
        if not result:
            return result

        probe_model = list(result.keys())[0]
        try:
            # Standardized probe payload for tool support verification
            probe_payload = {
                "model": probe_model,
                "messages": [{"role": "user", "content": "Respond 'ok'."}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "probe_tool",
                            "description": "A dummy tool to verify tool-calling support.",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    }
                ],
                "max_tokens": 5,
            }

            chat_path = (
                "api/chat"
                if provider_type == "ollama"
                else _openai_endpoint(host, provider_type, "chat/completions")
            )
            probe_resp = await client.post(f"{host}{chat_path}", json=probe_payload)

            # If the server accepts the tools parameter without error, mark tool support
            if probe_resp.status_code == 200:
                for cap in result.values():
                    cap.supports_tools = True

        except Exception as e:
            logger.debug(f"Dynamic tool probe failed for {host}: {e}")

    return result


async def detect_capabilities_lmstudio(
    host: str | None,
    api_key: str = "",
    active_probe: bool | None = None,
) -> dict[str, ModelCapability]:
    """Detect capabilities from an LM Studio/OpenAI-compatible server."""
    return await detect_capabilities_generic(
        host,
        api_key,
        provider_type="lmstudio",
        active_probe=active_probe,
    )


async def detect_capabilities_ollama(
    host: str | None,
    api_key: str = "",
    active_probe: bool | None = None,
) -> dict[str, ModelCapability]:
    """Detect capabilities from an Ollama server."""
    return await detect_capabilities_generic(
        host,
        api_key,
        provider_type="ollama",
        active_probe=active_probe,
    )
