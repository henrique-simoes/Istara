"""Database connection and session management."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# Build engine kwargs — SQLite needs check_same_thread, PostgreSQL does not
_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs: dict = {"echo": False}

if _is_sqlite:
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: prefer SSL for connections (does not break local dev)
    import ssl as _ssl

    _pg_ssl_ctx = _ssl.create_default_context()
    _pg_ssl_ctx.check_hostname = False
    _pg_ssl_ctx.verify_mode = _ssl.CERT_NONE  # "prefer" equivalent
    _engine_kwargs.setdefault("connect_args", {})["ssl"] = _pg_ssl_ctx

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Get a database session (for use as a FastAPI dependency)."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all database tables."""
    # Import all models so they're registered with Base
    from app.models import agent, codebook, document, finding, message, project, session, task  # noqa: F401
    from app.models import user  # noqa: F401
    from app.models import llm_server, method_metric  # noqa: F401
    from app.models.webauthn_credential import WebAuthnCredential  # noqa: F401
    from app.core.checkpoint import TaskCheckpoint  # noqa: F401
    from app.core.context_hierarchy import ContextDocument  # noqa: F401
    from app.core.scheduler import ScheduledTask  # noqa: F401
    from app.models.context_dag import ContextDAGNode  # noqa: F401
    from app.models.design_screen import DesignScreen, DesignBrief, DesignDecision  # noqa: F401
    from app.models.loop_execution import LoopExecution  # noqa: F401
    from app.models.agent_loop_config import AgentLoopConfig  # noqa: F401
    from app.models.notification import Notification, NotificationPreference  # noqa: F401
    from app.models.backup import BackupRecord  # noqa: F401
    from app.models.channel_instance import ChannelInstance  # noqa: F401
    from app.models.channel_message import ChannelMessage  # noqa: F401
    from app.models.channel_conversation import ChannelConversation  # noqa: F401
    from app.models.research_deployment import ResearchDeployment  # noqa: F401
    from app.models.survey_integration import SurveyIntegration, SurveyLink  # noqa: F401
    from app.models.mcp_server_config import MCPServerConfig  # noqa: F401
    from app.models.mcp_access_policy import MCPAccessPolicy  # noqa: F401
    from app.models.mcp_audit_log import MCPAuditEntry  # noqa: F401
    from app.models.model_skill_stats import ModelSkillStats  # noqa: F401
    from app.models.autoresearch_experiment import AutoresearchExperiment  # noqa: F401
    from app.models.codebook_version import CodebookVersion  # noqa: F401
    from app.models.code_application import CodeApplication  # noqa: F401
    from app.models.project_report import ProjectReport  # noqa: F401
    from app.models.project_member import ProjectMember  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight schema migration: add columns that create_all()
        # won't add to pre-existing tables.  Each ALTER is wrapped in a
        # try/except so it's a no-op once the column exists.
        import sqlalchemy as sa
        migrations = [
            "ALTER TABLE projects ADD COLUMN is_paused BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE projects ADD COLUMN owner_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE agents ADD COLUMN scope VARCHAR(10) NOT NULL DEFAULT 'universal'",
            "ALTER TABLE agents ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE projects ADD COLUMN watch_folder_path VARCHAR(1000)",
        ]
        for ddl in migrations:
            try:
                await conn.execute(sa.text(ddl))
            except Exception:
                pass  # column already exists — safe to ignore
