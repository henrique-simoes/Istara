"""Model capability detection -- determines what each loaded model can do.

Detects capabilities from:
1. LM Studio /v1/models endpoint metadata
2. Ollama /api/show/{model} endpoint details
3. Heuristic fallback: parse model name for parameter count, vision, tool support
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelCapability:
    """Capabilities of a single loaded model."""

    name: str
    parameter_count: str = "unknown"  # "0.8B", "1B", "4B", "12B", "27B", "70B"
    context_length: int = 4096
    supports_tools: bool = False
    supports_vision: bool = False
    quantization: str = ""
    source: str = ""  # "lmstudio" or "ollama"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parameter_count": self.parameter_count,
            "context_length": self.context_length,
            "supports_tools": self.supports_tools,
            "supports_vision": self.supports_vision,
            "quantization": self.quantization,
        }


def detect_from_name(model_name: str) -> ModelCapability:
    """Heuristic detection from model name string."""
    name_lower = model_name.lower()
    cap = ModelCapability(name=model_name)

    # Parameter count from name
    param_match = re.search(r'(\d+\.?\d*)\s*[bB]', model_name)
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
    tool_families = ["qwen", "llama-3", "mistral", "gemma-3", "nemotron", "gpt"]
    if param_num >= 4 and any(f in name_lower for f in tool_families):
        cap.supports_tools = True
    elif param_num >= 7:
        cap.supports_tools = True  # Most 7B+ models handle tools

    # Vision support
    if any(v in name_lower for v in ["vl", "vision", "visual", "multimodal"]):
        cap.supports_vision = True

    # Context length heuristic
    if param_num <= 1:
        cap.context_length = 2048
    elif param_num <= 4:
        cap.context_length = 4096
    elif param_num <= 12:
        cap.context_length = 8192
    else:
        cap.context_length = 32768

    # Quantization from name
    quant_match = re.search(
        r'(Q\d+_\w+|q\d+|GGUF|MLX|F16|FP16|INT8|INT4)',
        model_name,
        re.IGNORECASE,
    )
    if quant_match:
        cap.quantization = quant_match.group(1).upper()
    elif "mlx" in name_lower:
        cap.quantization = "MLX"

    return cap


async def detect_capabilities_lmstudio(host: str) -> dict[str, ModelCapability]:
    """Detect model capabilities from LM Studio API."""
    import httpx

    result: dict[str, ModelCapability] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{host}/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    cap = detect_from_name(model_id)
                    cap.source = "lmstudio"
                    # LM Studio may include max_tokens
                    if model.get("max_tokens"):
                        cap.context_length = model["max_tokens"]
                    result[model_id] = cap
    except Exception as e:
        logger.debug(f"LM Studio capability detection failed for {host}: {e}")
    return result


async def detect_capabilities_ollama(host: str) -> dict[str, ModelCapability]:
    """Detect model capabilities from Ollama API."""
    import httpx

    result: dict[str, ModelCapability] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # List models
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code != 200:
                return result
            models = resp.json().get("models", [])

            for model in models:
                name = model.get("name", "")
                cap = detect_from_name(name)
                cap.source = "ollama"

                # Get detailed info from the tags response itself
                details = model.get("details", {})
                if details.get("parameter_size"):
                    cap.parameter_count = details["parameter_size"]
                if details.get("quantization_level"):
                    cap.quantization = details["quantization_level"]

                # Try /api/show for context length
                try:
                    show_resp = await client.post(
                        f"{host}/api/show",
                        json={"name": name},
                        timeout=3.0,
                    )
                    if show_resp.status_code == 200:
                        show_data = show_resp.json()
                        model_info = show_data.get("model_info", {})
                        # Look for context length in various fields
                        for key in model_info:
                            if "context_length" in key.lower():
                                cap.context_length = int(model_info[key])
                                break
                except Exception:
                    pass

                result[name] = cap
    except Exception as e:
        logger.debug(f"Ollama capability detection failed for {host}: {e}")
    return result
