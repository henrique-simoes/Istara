"""Pi canonical model catalog — the single source for providers/models the
settings UI offers for selection.

The catalog mirrors the standalone Pi package's canonical
``models.generated.js`` (about 39 providers and 1,267 models) and adds
governed custom-provider snapshots when Istara must expose a provider that Pi
loads from ``~/.pi/agent/models.json``.  The current regular DashScope
snapshot contributes 40 Singapore OpenAI-compatible chat models.  The result
is shipped as a static resource so the Istara backend never needs the pi-ai
dependency at runtime.  Auth hints mirror ``docs/providers.md`` of the
standalone Pi CLI:

- OAuth/subscription providers (device-code / PKCE flows as in Pi's ``/login``)
- API-key providers (env var or auth.json credential custody)

Secrets are never stored here — only the provider identity, model capability
metadata, and which login methods the provider supports.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).parent / "data" / "pi_models_catalog.json"


@dataclass(frozen=True)
class PiCatalogModel:
    id: str
    name: str
    api: str
    baseUrl: str = ""
    contextWindow: int = 0
    maxTokens: int = 0
    reasoning: bool = False
    input: list[str] = field(default_factory=list)
    thinkingLevels: list[str] | None = None
    cost: dict | None = None


@dataclass(frozen=True)
class PiCatalogProvider:
    id: str
    display_name: str
    login_methods: list[str]  # "api_key" | "oauth" | "none"
    oauth_flow: str | None  # "openai_codex" | "browser" | "device_code" | "pkce" | None
    env_var: str | None  # canonical env var for API-key providers
    auth_json_key: str | None
    base_url: str | None
    oauth_methods: list[str] = field(default_factory=list)  # browser | device_code
    oauth_provider: str | None = None
    oauth_model_ids: list[str] = field(default_factory=list)
    auth_description: str = ""
    models: list[PiCatalogModel] = field(default_factory=list)


# --- Auth metadata, mirroring the standalone Pi providers.md (2026-08) -------
# OAuth/subscription providers (Pi `/login`):
_OAUTH_PROVIDERS: dict[str, dict[str, Any]] = {
    # These methods mirror the actual loaders in pi-ai/auth/oauth/load.js.
    # OpenAI API and OpenAI Codex are separate Pi providers: only the shared
    # Codex model ids can use ChatGPT subscription OAuth.
    "openai": {
        "flow": "openai_codex",
        "oauth_provider": "openai-codex",
        "oauth_methods": ["browser", "device_code"],
        "display": "OpenAI API",
        "description": "API key for OpenAI Platform. ChatGPT subscription OAuth is available on the shared Codex models below.",
    },
    "openai-codex": {
        "flow": "openai_codex",
        "oauth_provider": "openai-codex",
        "oauth_methods": ["browser", "device_code"],
        "display": "OpenAI Codex — ChatGPT subscription",
        "description": "Use your ChatGPT Plus or Pro subscription through Pi's Codex Responses API.",
    },
    "anthropic": {
        "flow": "browser_pkce",
        "oauth_methods": ["browser"],
        "display": "Anthropic Claude",
        "description": "API key or Claude Pro/Max browser login, when your Pi build exposes the subscription flow.",
    },
    "github-copilot": {
        "flow": "device_code",
        "oauth_methods": ["device_code"],
        "display": "GitHub Copilot",
        "description": "Headless device-code login for a GitHub Copilot subscription.",
    },
    "xai": {
        "flow": "device_code",
        "oauth_methods": ["device_code"],
        "display": "xAI Grok",
        "description": "API key or SuperGrok/X Premium device-code login.",
    },
    "openrouter": {
        "flow": "pkce",
        "oauth_methods": ["browser"],
        "display": "OpenRouter",
        "description": "API key or Pi's browser PKCE authorization flow.",
    },
    "kimi-coding": {
        "flow": "device_code",
        "oauth_methods": ["device_code"],
        "display": "Kimi Code",
        "description": "API key or Kimi Code device-code subscription login.",
    },
    "radius": {
        "flow": "radius",
        "oauth_methods": ["browser", "device_code"],
        "display": "Radius",
        "description": "Dynamic gateway OAuth; gateway discovery is required before use.",
    },
}

# API-key providers: (env var, auth.json key, display)
_API_KEY_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic", "Anthropic"),
    "openai": ("OPENAI_API_KEY", "openai", "OpenAI"),
    "deepseek": ("DEEPSEEK_API_KEY", "deepseek", "DeepSeek"),
    "google": ("GEMINI_API_KEY", "google", "Google Gemini"),
    "nvidia": ("NVIDIA_API_KEY", "nvidia", "NVIDIA NIM"),
    "mistral": ("MISTRAL_API_KEY", "mistral", "Mistral"),
    "groq": ("GROQ_API_KEY", "groq", "Groq"),
    "cerebras": ("CEREBRAS_API_KEY", "cerebras", "Cerebras"),
    "xai": ("XAI_API_KEY", "xai", "xAI"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter", "OpenRouter"),
    "together": ("TOGETHER_API_KEY", "together", "Together AI"),
    "fireworks": ("FIREWORKS_API_KEY", "fireworks", "Fireworks"),
    "baseten": ("BASETEN_API_KEY", "baseten", "Baseten"),
    "huggingface": ("HF_TOKEN", "huggingface", "Hugging Face"),
    "kimi-coding": ("KIMI_API_KEY", "kimi-coding", "Kimi For Coding"),
    # Regular Alibaba DashScope Model Studio uses the OpenAI-compatible
    # endpoint configured in Pi's custom ``models.json``.  Keep this separate
    # from the qwen-token-plan providers: their credentials and base URLs are
    # not interchangeable, and the model manager must preserve that identity.
    "dashscope": ("DASHSCOPE_API_KEY", "dashscope", "Alibaba DashScope"),
    "minimax": ("MINIMAX_API_KEY", "minimax", "MiniMax"),
    "minimax-cn": ("MINIMAX_CN_API_KEY", "minimax-cn", "MiniMax (China)"),
    "moonshotai": ("MOONSHOTAI_API_KEY", "moonshotai", "Moonshot AI"),
    "moonshotai-cn": ("MOONSHOTAI_CN_API_KEY", "moonshotai-cn", "Moonshot AI (China)"),
    "qwen-token-plan": ("QWEN_TOKEN_PLAN_API_KEY", "qwen-token-plan", "Qwen Token Plan"),
    "qwen-token-plan-cn": (
        "QWEN_TOKEN_PLAN_CN_API_KEY",
        "qwen-token-plan-cn",
        "Qwen Token Plan (China)",
    ),
    "qwen-token-plan-individual": (
        "QWEN_TOKEN_PLAN_API_KEY",
        "qwen-token-plan-individual",
        "Qwen Token Plan (Individual)",
    ),
    "xiaomi": ("XIAOMI_API_KEY", "xiaomi", "Xiaomi MiMo"),
    "xiaomi-token-plan-cn": (
        "XIAOMI_TOKEN_PLAN_CN_API_KEY",
        "xiaomi-token-plan-cn",
        "Xiaomi MiMo Token Plan (China)",
    ),
    "xiaomi-token-plan-ams": (
        "XIAOMI_TOKEN_PLAN_AMS_API_KEY",
        "xiaomi-token-plan-ams",
        "Xiaomi MiMo Token Plan (Amsterdam)",
    ),
    "xiaomi-token-plan-sgp": (
        "XIAOMI_TOKEN_PLAN_SGP_API_KEY",
        "xiaomi-token-plan-sgp",
        "Xiaomi MiMo Token Plan (Singapore)",
    ),
    "ant-ling": ("ANT_LING_API_KEY", "ant-ling", "Ant Ling"),
    "azure-openai-responses": (
        "AZURE_OPENAI_API_KEY",
        "azure-openai-responses",
        "Azure OpenAI Responses",
    ),
    "cloudflare-ai-gateway": (
        "CLOUDFLARE_API_KEY",
        "cloudflare-ai-gateway",
        "Cloudflare AI Gateway",
    ),
    "cloudflare-workers-ai": (
        "CLOUDFLARE_API_KEY",
        "cloudflare-workers-ai",
        "Cloudflare Workers AI",
    ),
    "vercel-ai-gateway": ("AI_GATEWAY_API_KEY", "vercel-ai-gateway", "Vercel AI Gateway"),
    "opencode": ("OPENCODE_API_KEY", "opencode", "OpenCode Zen"),
    "opencode-go": ("OPENCODE_API_KEY", "opencode-go", "OpenCode Go"),
    "amazon-bedrock": ("AWS_BEARER_TOKEN_BEDROCK", "amazon-bedrock", "Amazon Bedrock"),
    "google-vertex": (None, "google-vertex", "Google Vertex AI"),
    "github-copilot": (None, "github-copilot", "GitHub Copilot"),
}

# Providers that appear in the catalog but need no key/oauth (open gateways).
_NO_AUTH = {"ant-ling"}


def _login_methods(provider_id: str) -> list[str]:
    methods: list[str] = []
    oauth = _OAUTH_PROVIDERS.get(provider_id)
    if oauth and oauth.get("oauth_methods"):
        methods.append("oauth")
    key_info = _API_KEY_PROVIDERS.get(provider_id)
    if key_info and key_info[0]:
        methods.append("api_key")
    if not methods:
        methods.append("none" if provider_id not in _API_KEY_PROVIDERS else "api_key")
    return methods


def _display_name(provider_id: str) -> str:
    oauth = _OAUTH_PROVIDERS.get(provider_id)
    if oauth:
        return str(oauth["display"])
    key = _API_KEY_PROVIDERS.get(provider_id)
    if key:
        return key[2]
    return provider_id.replace("-", " ").title()


def load_catalog() -> dict[str, list[dict[str, Any]]]:
    """Load the raw shipped catalog (provider -> models)."""
    with open(_CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def pi_catalog_providers() -> list[PiCatalogProvider]:
    """Build the full provider list with auth hints and models (UI-ready)."""
    raw = load_catalog()
    providers: list[PiCatalogProvider] = []
    for provider_id in sorted(raw.keys()):
        oauth = _OAUTH_PROVIDERS.get(provider_id)
        key_info = _API_KEY_PROVIDERS.get(provider_id)
        models = [
            PiCatalogModel(
                **{k: v for k, v in m.items() if k in PiCatalogModel.__dataclass_fields__}
            )
            for m in raw[provider_id]
        ]
        oauth_provider = str(oauth.get("oauth_provider", provider_id)) if oauth else None
        oauth_model_ids: list[str] = []
        if oauth_provider and oauth_provider != provider_id:
            oauth_model_ids = [m["id"] for m in raw.get(oauth_provider, [])]
        elif oauth and oauth_provider == provider_id:
            oauth_model_ids = [m.id for m in models]
        providers.append(
            PiCatalogProvider(
                id=provider_id,
                display_name=_display_name(provider_id),
                login_methods=_login_methods(provider_id),
                oauth_flow=oauth["flow"] if oauth else None,
                env_var=key_info[0] if key_info else None,
                auth_json_key=key_info[1] if key_info else None,
                base_url=models[0].baseUrl if models else None,
                oauth_methods=list(oauth.get("oauth_methods", [])) if oauth else [],
                oauth_provider=oauth_provider,
                oauth_model_ids=oauth_model_ids,
                auth_description=str(oauth.get("description", ""))
                if oauth
                else "API key or configured ambient credentials.",
                models=models,
            )
        )
    return providers


def pi_catalog_json() -> list[dict]:
    """Serializable catalog for the settings API (models included)."""
    return [asdict(p) for p in pi_catalog_providers()]


def provider_summary() -> dict[str, Any]:
    providers = pi_catalog_providers()
    return {
        "provider_count": len(providers),
        "model_count": sum(len(p.models) for p in providers),
        "providers": [
            {
                "id": p.id,
                "display_name": p.display_name,
                "models": len(p.models),
                "login_methods": p.login_methods,
                "oauth_flow": p.oauth_flow,
                "env_var": p.env_var,
            }
            for p in providers
        ],
    }
