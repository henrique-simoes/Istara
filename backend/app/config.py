"""ReClaw application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:latest"
    ollama_embed_model: str = "nomic-embed-text"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/reclaw.db"
    lance_db_path: str = "./data/lance_db"

    # Files
    upload_dir: str = "./data/uploads"
    projects_dir: str = "./data/projects"

    # Hardware resource budget
    resource_reserve_ram_gb: float = 4.0
    resource_reserve_cpu_percent: int = 30

    # File watcher
    file_watch_interval_seconds: int = 5

    # RAG
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5
    rag_score_threshold: float = 0.7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.upload_dir, self.projects_dir, self.lance_db_path]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
