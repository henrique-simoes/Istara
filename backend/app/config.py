"""Istara application configuration."""

import os
import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_BACKEND_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    str(_BACKEND_DIR / ".env.local"),
)


class PiApiEndpoint(BaseModel):
    """A Pi-only provider target.

    These targets intentionally do not share the LLM-server/compute registry:
    their identity is an authority boundary, not a model preference.
    """

    endpoint_id: str
    provider_kind: Literal["openai_compat", "anthropic_compat", "openai_codex"] = "openai_compat"
    base_url: str
    model: str
    keychain_service: str
    keychain_account: str = ""
    timeout_ms: int = Field(default=30_000, ge=1, le=120_000)
    max_retries: int = Field(default=0, ge=0, le=3)
    # Trustworthy per-endpoint pricing (USD per 1M tokens) resolved from the
    # deployment's contract. The worker feeds these into the pi-ai model rates so
    # a real turn's usage is priced and the per-run ``max_cost_usd`` ceiling can
    # fail closed. An endpoint left unpriced cannot enforce a cost budget: a
    # budgeted run that spends tokens fails closed at the worker rather than
    # silently reporting $0 (see pi-runtime/src/session.mjs).
    cost_input_per_mtok: float = Field(default=0.0, ge=0.0)
    cost_output_per_mtok: float = Field(default=0.0, ge=0.0)
    cost_cache_read_per_mtok: float = Field(default=0.0, ge=0.0)
    cost_cache_write_per_mtok: float = Field(default=0.0, ge=0.0)
    # Static capability advertisement (the parity subset meaningful for exact
    # endpoints). 0/False means "unknown" and fails capability admission closed
    # when a caller explicitly requires that capability (min_context/vision).
    context_window: int = Field(default=0, ge=0)
    max_tokens: int = Field(default=0, ge=0)
    supports_tools: bool = True
    supports_vision: bool = False
    # Provider-auth metadata is non-secret and lets the runtime choose the
    # correct Pi transport (for example Codex Responses adds account headers).
    pi_provider: str = ""
    auth_provider: str = ""
    auth_method: str = "api_key"
    # Fernet-wrapped OAuth credential JSON. Never included in public endpoint views.
    oauth_credential_encrypted: str = ""

    @field_validator("endpoint_id", "base_url", "model", "keychain_service")
    @classmethod
    def required_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Pi endpoint fields must be non-empty")
        return value


def _read_macos_keychain_secret(service: str, account: str = "") -> str:
    """Read a local secret from macOS Keychain without logging its value."""
    if not service or not Path("/usr/bin/security").exists():
        return ""
    command = ["/usr/bin/security", "find-generic-password"]
    if account:
        command.extend(["-a", account])
    command.extend(["-s", service, "-w"])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _write_macos_keychain_secret(service: str, account: str, value: str) -> bool:
    """Write a local secret into macOS Keychain (upsert) without logging it.

    Compatible with ``_read_macos_keychain_secret`` (same service/account
    scheme). Falls back to ``True`` on non-macOS hosts so endpoint config
    still persists via the ``ISTARA_PI_SECRET_*`` env path instead.
    """
    if not service or not value:
        return False
    if not Path("/usr/bin/security").exists():
        return True  # env-based custody on non-macOS
    command = [
        "/usr/bin/security",
        "add-generic-password",
        "-U",  # update if exists
        "-a", account or "default",
        "-s", service,
        "-w", value,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0


def _pi_endpoint_secret_env_name(endpoint_id: str) -> str:
    """Return the env var that supplies a Pi endpoint secret without Keychain."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", endpoint_id).strip("_").upper()
    return f"ISTARA_PI_SECRET_{slug}"


def _read_pi_endpoint_secret(
    endpoint_id: str,
    service: str,
    account: str = "",
    *,
    keychain_reader=None,
) -> str:
    """Read a Pi endpoint secret: ``ISTARA_PI_SECRET_<ID>`` env first, then Keychain.

    Parity with ``resolve_llm_fallback_api_key``: a configured environment value
    wins, so non-macOS hosts (no ``/usr/bin/security``) can still bind endpoints.
    *keychain_reader* lets the caller keep its own import seam; the secret value
    is never logged.
    """
    env_value = os.environ.get(_pi_endpoint_secret_env_name(endpoint_id), "").strip()
    if env_value:
        return env_value
    reader = keychain_reader or _read_macos_keychain_secret
    return reader(service, account)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider: "ollama" or "lmstudio"
    llm_provider: str = "lmstudio"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:latest"
    ollama_embed_model: str = "nomic-embed-text"

    # LM Studio (OpenAI-compatible API)
    lmstudio_host: str = "http://localhost:1234"
    lmstudio_model: str = "default"
    lmstudio_embed_model: str = "default"
    lmstudio_api_key: str = ""
    lmstudio_auto_load_enabled: bool = True
    lmstudio_auto_context_reload: bool = False
    lmstudio_max_load_attempts_per_request: int = 1
    lmstudio_allow_unload_on_reload: bool = False
    llm_capability_active_probe_enabled: bool = False

    # Optional authenticated fallback for OpenAI-compatible secondary servers.
    # Used after the primary provider exhausts its retry budget.
    llm_fallback_host: str = ""
    llm_fallback_provider: str = "openai_compat"
    llm_fallback_model: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_api_key_keychain_service: str = "istara-secondary-openai-compatible-tests"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/istara.db"
    lance_db_path: str = "./data/lance_db"
    sqlite_busy_timeout_ms: int = 30000

    # Files
    upload_dir: str = "./data/uploads"
    projects_dir: str = "./data/projects"
    agent_avatars_dir: str = "./data/agent_avatars"
    upload_max_bytes: int = 100 * 1024 * 1024
    upload_scanner_command: str = ""
    upload_scanner_timeout_seconds: int = 30
    upload_quarantine_on_prompt_injection: bool = True
    avatar_max_bytes: int = 5 * 1024 * 1024
    channel_attachment_max_bytes: int = 25 * 1024 * 1024
    file_encryption_enabled: bool = False
    file_encryption_key: str = ""
    file_encryption_keychain_service: str = "istara-file-encryption"
    file_encryption_key_file: str = "./data/security/file-encryption.key"

    # Team mode (multi-user)
    team_mode: bool = False
    jwt_secret: str = ""  # Auto-generated on first run if empty
    jwt_expire_minutes: int = 1440  # 24 hours

    # WebAuthn / passkeys. RP ID must match the production host domain.
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Istara"
    webauthn_origins: str = ""  # Empty = derive from CORS origins

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origin_regex: str = ""

    # Admin bootstrap (auto-created on first startup if no users exist)
    admin_username: str = "admin"
    admin_password: str = ""  # Auto-generated if empty

    # Data encryption key for sensitive DB fields (auto-generated on first run)
    data_encryption_key: str = ""

    # Network security — access token for non-localhost connections
    # When set, any request from outside localhost must provide this token
    # via X-Access-Token header or ?token= query parameter.
    # Empty = disabled (backward-compatible, localhost-only setups).
    network_access_token: str = ""
    # Bind host: "127.0.0.1" = localhost only, "0.0.0.0" = network accessible
    bind_host: str = "0.0.0.0"

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "200/minute"
    a2a_rate_limit_per_minute: int = 60
    a2a_tasks_send_rate_limit_per_minute: int = 12
    a2a_replay_ttl_seconds: int = 300
    a2a_agent_card_auth_required_team_mode: bool = True
    webhook_replay_ttl_seconds: int = 300
    # Comma-separated exact hosts/IPs or CIDRs whose forwarded client headers
    # may be trusted for rate limiting and request identity.
    trusted_proxy_hosts: str = "127.0.0.1,::1,localhost"

    # Runtime/source boundary. Public installs keep shipped personas and skill
    # definitions read-only; local user changes go under ignored data overlays.
    istara_runtime_profile: str = "dev"  # dev | public | personal-lab
    allow_source_persona_mutation: bool = False
    allow_source_skill_mutation: bool = False
    runtime_personas_dir: str = "./data/personas"
    runtime_skills_dir: str = "./data/skills/custom"

    # Hardware resource budget
    resource_reserve_ram_gb: float = 4.0
    resource_reserve_cpu_percent: int = 30
    strict_auto_routing: bool = False

    # Skill request budgets. Routes enforce these before the client gives up so
    # cancelled simulations and UI calls do not leave orphaned LLM work running.
    skill_execute_timeout_seconds: float = 600.0
    skill_execute_max_timeout_seconds: float = 900.0
    skill_plan_timeout_seconds: float = 180.0
    skill_plan_max_timeout_seconds: float = 300.0
    skill_execute_context_limit_tokens: int = 4096
    skill_execute_max_output_tokens: int = 1024
    skill_execute_item_limit: int = 4
    skill_schema_prompt_char_limit: int = 4000
    skill_execute_max_schema_tokens: int = 1200
    agent_react_skill_candidate_limit: int = 6
    agent_react_skill_tool_timeout_seconds: float = 300.0
    agent_react_skill_min_candidate_score: float = 0.12

    # File watcher
    file_watch_interval_seconds: int = 5

    # Context window
    max_context_tokens: int = 8192
    _detected_context_tokens: int = 0
    context_budget_strategy: str = "adaptive"

    # General data directory
    data_dir: str = "./data"

    # RAG
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180
    rag_top_k: int = 5
    rag_score_threshold: float = 0.3
    rag_hybrid_vector_weight: float = 0.7
    rag_hybrid_keyword_weight: float = 0.3

    # DAG Context Summarization
    dag_enabled: bool = True
    dag_fresh_tail_size: int = 32
    dag_batch_size: int = 32
    dag_rollup_threshold: int = 4
    dag_summary_max_tokens: int = 300

    # Design integrations
    stitch_api_key: str = ""
    stitch_api_host: str = "https://generativelanguage.googleapis.com"
    figma_api_token: str = ""
    figma_api_host: str = "https://api.figma.com"
    design_screens_dir: str = "./data/design_screens"
    interfaces_mock_endpoints_enabled: bool = False

    # Backup
    backup_dir: str = "./data/backups"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_count: int = 7
    backup_full_interval_days: int = 7

    # Agent Identity & Evolution
    prompt_compression_strategy: str = "llmlingua"  # "llmlingua", "prompt_rag", "truncate"
    prompt_rag_use_embeddings: bool = True  # Use embedding similarity for Prompt RAG
    prompt_rag_top_k: int = 8  # Number of dynamic sections to retrieve
    self_evolution_enabled: bool = True  # Enable auto self-evolution scan
    self_evolution_auto_promote: bool = False  # Auto-promote (vs user approval)
    autonomous_quality_agents_enabled: bool = (
        False  # Dev/Admin QA loops only when explicitly enabled
    )

    # Pi replacement candidate (off unless explicitly selected by env/header).
    pi_replacement_enabled: bool = False
    pi_replacement_request_header: str = "x-istara-agent-engine"
    pi_replacement_deepseek_base_url: str = "https://api.deepseek.com"
    pi_replacement_deepseek_model: str = "deepseek-v4-pro"
    pi_replacement_deepseek_keychain_service: str = "istara-pi-deepseek"
    pi_replacement_deepseek_keychain_account: str = "openclaw"
    # Default endpoint pricing (USD per 1M tokens). Sourced from the configured
    # model's (deepseek-v4-pro) published list price as of 2026-07-20 so the
    # built-in endpoint is priced out of the box and its per-run cost ceiling
    # fails closed; operators override per env/.env with their own negotiated
    # contract rate. Every category the endpoint can spend must be priced: pi-ai
    # prices input, output, and cache-read (DeepSeek reports cache hits via
    # ``prompt_cache_hit_tokens``) independently, and a cache-read turn on an
    # endpoint that priced only input/output would otherwise fail closed as
    # unpriced. DeepSeek bills cache writes at the cache-miss input rate and does
    # not report a separate cache-write token count, so that category is never
    # spent and needs no rate. Never zero — an unpriced real endpoint cannot
    # enforce a cost budget.
    pi_replacement_deepseek_cost_input_per_mtok: float = 0.435  # cache-miss input
    pi_replacement_deepseek_cost_output_per_mtok: float = 0.87  # output
    pi_replacement_deepseek_cost_cache_read_per_mtok: float = 0.003625  # cache-hit input
    # JSON-compatible settings input.  Empty preserves the existing default
    # endpoint without registering it as donated/shared compute.
    pi_api_endpoints: list[PiApiEndpoint] = []
    # Bounded Pi runtime worker pool size (round-robin by session_key hash).
    pi_worker_pool_size: int = 2
    # Petals bridge (CF-335..338): expose consented donors as identity-pinned,
    # OpenAI-compatible loopback endpoints for the Pi engine. Disabled by default.
    petals_bridge_enabled: bool = False
    petals_bridge_base_path: str = "/api/petals/v1"

    # Audio is a separate, explicit catalog. Empty provider fails closed;
    # credentials are referenced by opaque keychain/encrypted-store handles.
    audio_model_provider: str = ""
    audio_model: str = "whisper-base"
    audio_model_endpoint_id: str = "audio-default"
    audio_model_credential_ref: str = ""
    audio_model_mode: str = "local"
    audio_model_languages: list[str] = []
    audio_model_diarization: bool = False
    audio_model_timestamps: bool = True
    audio_model_speaker_count: str = "unknown"
    audio_model_review_threshold: float = 0.7

    # AgenticDispatcher engine default (master plan §5.1): the last resort after
    # per-call override, request header, and the project's `agentic_engine`
    # setting. Stays "legacy" until the owner flips the rollout.
    agentic_engine_default: str = "legacy"
    agentic_core: bool = False
    # True when the configured Ollama-compatible provider plane is a
    # deterministic wire stub (QA contract / connectivity-acceptance stacks),
    # not a model service. Interactive chat fails closed instead of serving
    # canned contract text as an assistant reply (CF-SPEC-1 ITEM-002).
    llm_provider_contract_stub: bool = False

    # Meta-Hyperagent (optional layer that tunes subsystem parameters)
    meta_hyperagent_enabled: bool = False
    meta_hyperagent_observation_interval_hours: int = 6
    meta_hyperagent_variant_observation_hours: int = 72

    # MCP Server (exposes Istara to external agents — OFF by default for security)
    mcp_server_enabled: bool = False
    mcp_server_port: int = 8001

    # Autoresearch (Karpathy-inspired optimization loops — OFF by default)
    autoresearch_enabled: bool = False
    autoresearch_max_experiments_per_run: int = 20
    autoresearch_max_daily_experiments: int = 200
    autoresearch_min_improvement_delta: float = 0.01
    autoresearch_measurement_repeats: int = 1
    validation_timeout_seconds: int = 120

    # Telemetry (local-first, zero-trust — OFF for sharing by default)
    telemetry_enabled: bool = False
    telemetry_export_dir: str = "./data/telemetry_exports"

    model_config = {
        "env_file": _BACKEND_ENV_FILES,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def resolve_llm_fallback_api_key(self) -> str:
        """Return fallback API key from env first, then the configured keychain service."""
        configured_key = self.llm_fallback_api_key.strip()
        if configured_key:
            return configured_key
        return _read_macos_keychain_secret(self.llm_fallback_api_key_keychain_service.strip())

    def resolve_pi_replacement_deepseek_api_key(self) -> str:
        """Return the Pi candidate DeepSeek key from the configured Keychain item."""
        return _read_macos_keychain_secret(
            self.pi_replacement_deepseek_keychain_service.strip(),
            self.pi_replacement_deepseek_keychain_account.strip(),
        )

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [
            self.upload_dir,
            self.projects_dir,
            self.lance_db_path,
            self.agent_avatars_dir,
            self.runtime_personas_dir,
            self.runtime_skills_dir,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        Path(self.design_screens_dir).mkdir(parents=True, exist_ok=True)
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

    def ensure_secrets(self) -> None:
        """Generate random JWT secret if not configured.

        Persists the generated secret to .env so it survives container restarts.
        """
        import secrets as _secrets

        insecure_defaults = {"", "istara-dev-secret-change-in-production"}
        if self.jwt_secret in insecure_defaults:
            self.jwt_secret = _secrets.token_urlsafe(32)
            # Persist to .env
            env_path = Path(__file__).parent.parent / ".env"
            try:
                lines = env_path.read_text().splitlines() if env_path.exists() else []
                # Replace or append JWT_SECRET
                found = False
                for i, line in enumerate(lines):
                    if line.startswith("JWT_SECRET="):
                        lines[i] = f"JWT_SECRET={self.jwt_secret}"
                        found = True
                        break
                if not found:
                    lines.append(f"JWT_SECRET={self.jwt_secret}")
                env_path.write_text("\n".join(lines) + "\n")
            except Exception:
                pass  # Non-fatal — secret still in memory for this session

    def update_context_window(self, detected_tokens: int) -> None:
        """Update the context window based on auto-detected model capabilities.

        Only updates if the detected value differs significantly (>2x) from
        the current setting, to avoid unnecessary churn.
        """
        if (
            detected_tokens > 0
            and abs(detected_tokens - self.max_context_tokens) > self.max_context_tokens
        ):
            logger = __import__("logging").getLogger(__name__)
            logger.info(
                f"Auto-detected context window: {detected_tokens} tokens "
                f"(was {self.max_context_tokens}). Updating budget."
            )
            self.max_context_tokens = detected_tokens
            self._detected_context_tokens = detected_tokens

    def ensure_telemetry_dir(self) -> None:
        """Create telemetry export directory."""
        Path(self.telemetry_export_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
