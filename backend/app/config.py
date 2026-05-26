"""Istara application configuration."""

from pathlib import Path
import subprocess

from pydantic_settings import BaseSettings


_BACKEND_DIR = Path(__file__).resolve().parent.parent
_BACKEND_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    str(_BACKEND_DIR / ".env.local"),
)


def _read_macos_keychain_secret(service: str) -> str:
    """Read a local secret from macOS Keychain without logging its value."""
    if not service or not Path("/usr/bin/security").exists():
        return ""
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
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
    autonomous_quality_agents_enabled: bool = False  # Dev/Admin QA loops only when explicitly enabled

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
        return _read_macos_keychain_secret(
            self.llm_fallback_api_key_keychain_service.strip()
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
