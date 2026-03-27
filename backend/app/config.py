"""ReClaw application configuration."""

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
    database_url: str = "sqlite+aiosqlite:///./data/reclaw.db"
    lance_db_path: str = "./data/lance_db"

    # Files
    upload_dir: str = "./data/uploads"
    projects_dir: str = "./data/projects"
    agent_avatars_dir: str = "./data/agent_avatars"

    # Team mode (multi-user)
    team_mode: bool = False
    jwt_secret: str = "reclaw-dev-secret-change-in-production"
    jwt_expire_minutes: int = 1440  # 24 hours

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

    # MCP Server (exposes ReClaw to external agents — OFF by default for security)
    mcp_server_enabled: bool = False
    mcp_server_port: int = 8001

    # Autoresearch (Karpathy-inspired optimization loops — OFF by default)
    autoresearch_enabled: bool = False
    autoresearch_max_experiments_per_run: int = 20
    autoresearch_max_daily_experiments: int = 200

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.upload_dir, self.projects_dir, self.lance_db_path, self.agent_avatars_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        Path(self.design_screens_dir).mkdir(parents=True, exist_ok=True)
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
