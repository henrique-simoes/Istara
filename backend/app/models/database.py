"""Database connection and session management."""

from importlib import import_module
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
    # Import model modules so they're registered with Base. Keep this dynamic so
    # database.py does not statically depend on every model-owning feature module.
    for module_name in (
        "app.models.agent",
        "app.models.codebook",
        "app.models.document",
        "app.models.finding",
        "app.models.message",
        "app.models.project",
        "app.models.session",
        "app.models.task",
        "app.models.user",
        "app.models.auth_session",
        "app.models.llm_server",
        "app.models.method_metric",
        "app.models.webauthn_credential",
        "app.core.checkpoint",
        "app.core.context_hierarchy",
        "app.core.scheduler",
        "app.models.context_dag",
        "app.models.design_screen",
        "app.models.loop_execution",
        "app.models.agent_loop_config",
        "app.models.notification",
        "app.models.backup",
        "app.models.channel_instance",
        "app.models.channel_message",
        "app.models.channel_conversation",
        "app.models.research_deployment",
        "app.models.survey_integration",
        "app.models.mcp_server_config",
        "app.models.mcp_access_policy",
        "app.models.mcp_audit_log",
        "app.models.model_skill_stats",
        "app.models.autoresearch_experiment",
        "app.models.codebook_version",
        "app.models.code_application",
        "app.models.connection_string",
        "app.models.reasoning_memory",
        "app.models.improvement_governance",
        "app.models.dgmh_archive",
        "app.core.audit_middleware",
        "app.models.telemetry_span",
        "app.models.project_report",
        "app.models.project_member",
        "app.models.task_review",
    ):
        import_module(module_name)

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
            # Email encryption support
            "ALTER TABLE users ADD COLUMN email_hash VARCHAR(64)",
            # Task review/reward state
            "ALTER TABLE tasks ADD COLUMN labels TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE tasks ADD COLUMN review_state VARCHAR(30) NOT NULL DEFAULT 'none'",
            "ALTER TABLE tasks ADD COLUMN what_to_review TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE tasks ADD COLUMN review_cycle_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN failure_streak INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN approval_streak INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN last_review_outcome VARCHAR(50)",
            "ALTER TABLE tasks ADD COLUMN last_reviewed_by VARCHAR(36)",
            "ALTER TABLE tasks ADD COLUMN last_reviewed_at DATETIME",
            "ALTER TABLE tasks ADD COLUMN last_review_feedback TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE tasks ADD COLUMN next_agent_action VARCHAR(30)",
            "ALTER TABLE tasks ADD COLUMN human_feedback_score FLOAT",
            "ALTER TABLE tasks ADD COLUMN review_severity VARCHAR(20)",
            "ALTER TABLE tasks ADD COLUMN review_failure_category VARCHAR(60)",
            # Connection-string redemption and admin visibility.
            "ALTER TABLE connection_strings ADD COLUMN redeemed_by_user_id VARCHAR(36)",
            "ALTER TABLE connection_strings ADD COLUMN redeemed_username VARCHAR(255)",
            "ALTER TABLE connection_strings ADD COLUMN redeemed_at DATETIME",
            "ALTER TABLE connection_strings ADD COLUMN last_validated_at DATETIME",
            "ALTER TABLE connection_strings ADD COLUMN token_type VARCHAR(40) NOT NULL DEFAULT 'user_invite'",
            "ALTER TABLE connection_strings ADD COLUMN ws_url VARCHAR(1000) NOT NULL DEFAULT ''",
            "ALTER TABLE connection_strings ADD COLUMN intended_role VARCHAR(40) NOT NULL DEFAULT 'researcher'",
            "ALTER TABLE connection_strings ADD COLUMN connection_string_hash VARCHAR(64)",
            # Scheduler/loops hardening columns for existing installations.
            "ALTER TABLE scheduled_tasks ADD COLUMN is_running BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE scheduled_tasks ADD COLUMN agent_id VARCHAR(36)",
            "ALTER TABLE scheduled_tasks ADD COLUMN loop_type VARCHAR(50) NOT NULL DEFAULT 'cron'",
            "ALTER TABLE scheduled_tasks ADD COLUMN interval_seconds INTEGER",
            "ALTER TABLE scheduled_tasks ADD COLUMN execution_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE scheduled_tasks ADD COLUMN last_status VARCHAR(20) NOT NULL DEFAULT ''",
        ]
        for ddl in migrations:
            try:
                await conn.execute(sa.text(ddl))
            except Exception:
                pass  # Column already exists or SQLite doesn't support this DDL

        # Create tables with follow-up lightweight migrations when needed.
        try:
            await conn.run_sync(
                lambda c: Base.metadata.tables["webauthn_credentials"].create(c, checkfirst=True)
            )
        except Exception:
            pass  # Table already exists

        try:
            await conn.run_sync(
                lambda c: Base.metadata.tables["task_review_events"].create(c, checkfirst=True)
            )
        except Exception:
            pass  # Table already exists
