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


async def detect_capabilities_generic(host: str | None, api_key: str = "", provider_type: str = "openai_compat") -> dict[str, ModelCapability]:
    """Empirically detect model capabilities from any OpenAI-compatible API.
    
    Follows Berkeley Function Calling Leaderboard (BFCL) patterns:
    1. Metadata discovery (GET /v1/models)
    2. Dynamic probing (test chat completion with dummy tool)
    """
    if not host:
        return {}
        
    import httpx
    result: dict[str, ModelCapability] = {}
    
    # RFC 3986 Normalization for detection client
    if not host.endswith("/"):
        host += "/"
        
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        # 1. Metadata Discovery
        try:
            models_path = "api/tags" if provider_type == "ollama" else "v1/models"
            resp = await client.get(f"{host}{models_path}")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", []) if provider_type == "ollama" else data.get("data", [])
                
                for m in models:
                    model_id = m.get("name" if provider_type == "ollama" else "id", "")
                    if not model_id:
                        continue
                    
                    cap = detect_from_name(model_id)
                    cap.source = provider_type
                    
                    # Metadata context length
                    if m.get("max_tokens"):
                        cap.context_length = m["max_tokens"]
                    
                    result[model_id] = cap
        except Exception as e:
            logger.debug(f"Metadata discovery failed for {host}: {e}")

        # 2. Dynamic Probing (Active Verification)
        # Select the most likely primary model to probe
        if not result:
            return result
            
        probe_model = list(result.keys())[0]
        try:
            # Standardized probe payload for tool support verification
            probe_payload = {
                "model": probe_model,
                "messages": [{"role": "user", "content": "Respond 'ok'."}],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "probe_tool",
                        "description": "A dummy tool to verify tool-calling support.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                }],
                "max_tokens": 5
            }
            
            chat_path = "api/chat" if provider_type == "ollama" else "v1/chat/completions"
            probe_resp = await client.post(f"{host}{chat_path}", json=probe_payload)
            
            # If the server accepts the tools parameter without error, mark tool support
            if probe_resp.status_code == 200:
                for cap in result.values():
                    cap.supports_tools = True
            elif probe_resp.status_code == 400:
                # Most servers return 400 if 'tools' is unknown/unsupported
                for cap in result.values():
                    cap.supports_tools = False
                    
        except Exception as e:
            logger.debug(f"Dynamic tool probe failed for {host}: {e}")
            
    return result
