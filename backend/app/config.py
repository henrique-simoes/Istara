"""Istara application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


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

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/istara.db"
    lance_db_path: str = "./data/lance_db"

    # Files
    upload_dir: str = "./data/uploads"
    projects_dir: str = "./data/projects"
    agent_avatars_dir: str = "./data/agent_avatars"

    # Team mode (multi-user)
    team_mode: bool = False
    jwt_secret: str = ""  # Auto-generated on first run if empty
    jwt_expire_minutes: int = 1440  # 24 hours

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

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

    # Hardware resource budget
    resource_reserve_ram_gb: float = 4.0
    resource_reserve_cpu_percent: int = 30

    # File watcher
    file_watch_interval_seconds: int = 5

    # Context window
    max_context_tokens: int = 8192

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.upload_dir, self.projects_dir, self.lance_db_path, self.agent_avatars_dir]:
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


settings = Settings()
