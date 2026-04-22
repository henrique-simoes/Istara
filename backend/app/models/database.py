"""Database connection and session management."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

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
    # NullPool prevents "database is locked" and "Event loop is closed" issues
    # across tests by closing connections immediately.
    _engine_kwargs["poolclass"] = NullPool
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
    from app.models.connection_string import ConnectionString  # noqa: F401
    from app.core.audit_middleware import AuditLog  # noqa: F401
    from app.models.telemetry_span import TelemetrySpan  # noqa: F401
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
            # MFA / 2FA columns
            "ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)",
            "ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN recovery_codes_hashed TEXT",
            "ALTER TABLE users ADD COLUMN passkey_enabled BOOLEAN NOT NULL DEFAULT 0",
            # Widen password_hash for Argon2id hashes (SQLite ignores this, but needed for PostgreSQL)
            "ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)",
        ]
        for ddl in migrations:
            try:
                await conn.execute(sa.text(ddl))
                await conn.commit()
            except Exception:
                pass  # Column already exists or SQLite doesn't support this DDL

        # Create webauthn_credentials table if it doesn't exist
        try:
            from app.models.webauthn_credential import WebAuthnCredential

            await conn.run_sync(lambda c: WebAuthnCredential.__table__.create(c, checkfirst=True))
        except Exception:
            pass  # Table already exists
