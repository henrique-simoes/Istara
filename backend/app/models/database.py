"""Database connection and session management."""

import os
from importlib import import_module
from pathlib import Path

from sqlalchemy import event
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
    _engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": max(1.0, settings.sqlite_busy_timeout_ms / 1000),
    }
    # NullPool prevents "database is locked" and "Event loop is closed" issues
    # across tests by closing connections immediately.
    _engine_kwargs["poolclass"] = NullPool
else:
    # PostgreSQL: SSL by default; disable explicitly for internal networks where the
    # server has no TLS (POSTGRES_SSL=false). "prefer"-equivalent context when enabled.
    if str(os.getenv("POSTGRES_SSL", "true")).strip().lower() not in ("0", "false", "no", "off"):
        import ssl as _ssl

        _pg_ssl_ctx = _ssl.create_default_context()
        _pg_ssl_ctx.check_hostname = False
        _pg_ssl_ctx.verify_mode = _ssl.CERT_NONE  # "prefer" equivalent
        _engine_kwargs.setdefault("connect_args", {})["ssl"] = _pg_ssl_ctx

engine = create_async_engine(settings.database_url, **_engine_kwargs)


if _is_sqlite:
    _sqlite_busy_timeout_ms = max(1000, int(settings.sqlite_busy_timeout_ms))

    @event.listens_for(engine.sync_engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
        """Tune SQLite for concurrent agent/report writes.

        Istara's local/dev profile can have UI requests, simulation runs, and
        background agents writing at the same time. WAL plus a busy timeout
        makes those writes queue briefly instead of immediately poisoning a
        long-running session with "database is locked".
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout={_sqlite_busy_timeout_ms}")
            if ":memory:" not in settings.database_url:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Get a database session (for use as a FastAPI dependency)."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def register_models() -> None:
    """Import every mapped model before SQLAlchemy configures relationships.

    This is intentionally separate from database creation so processes and
    test harnesses that instantiate an ORM row before ``init_db`` can establish
    a complete mapper registry without opening or mutating a database.
    """
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
        "app.models.recovery_code",
        "app.models.auth_session",
        "app.models.llm_server",
        "app.models.method_metric",
        "app.models.webauthn_credential",
        "app.models.webauthn_challenge",
        "app.core.checkpoint",
        "app.core.context_hierarchy",
        "app.core.scheduler",
        "app.models.context_dag",
        "app.models.design_screen",
        "app.models.interface_config",
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
        "app.models.research_validity",
        "app.models.connection_string",
        "app.models.reasoning_memory",
        "app.models.improvement_governance",
        "app.models.dgmh_archive",
        "app.core.agent_learning",
        "app.core.audit_middleware",
        "app.models.telemetry_span",
        "app.models.agentic_usage",
        "app.models.project_report",
        "app.models.project_member",
        "app.models.permission_request",
        "app.models.task_review",
    ):
        import_module(module_name)


async def init_db() -> None:
    """Register mapped models and create all database tables."""
    register_models()

    async with engine.begin() as conn:
        # PostgreSQL + enums: SQLAlchemy's checkfirst sees an existing enum TYPE and
        # skips the tables that depend on it, even when no table exists yet (fresh DB).
        # Detect an empty schema and force-create all tables so recovery_codes,
        # task_checkpoints, etc. are never missing on first boot. Idempotent for an
        # already-populated database: create_all(checkfirst=True) skips existing tables.
        # The emptiness probe is dialect-aware: information_schema is PostgreSQL-only;
        # SQLite exposes sqlite_master instead (upgrade-safe for existing SQLite users).
        from sqlalchemy import text as _sa_text

        if _is_sqlite:
            _empty_probe = _sa_text(
                "select count(*) from sqlite_master where type = 'table' "
                "and name not like 'sqlite_%'"
            )
        else:
            _empty_probe = _sa_text(
                "select count(*) from information_schema.tables where table_schema = 'public'"
            )
        existing = (await conn.execute(_empty_probe)).scalar() or 0
        if existing == 0:
            await conn.run_sync(lambda sc: Base.metadata.create_all(sc, checkfirst=False))
        else:
            await conn.run_sync(lambda sc: Base.metadata.create_all(sc, checkfirst=True))

        # Lightweight schema migration: add columns that create_all()
        # won't add to pre-existing tables.  Each ALTER runs inside its own
        # SAVEPOINT (begin_nested) so a single "column already exists" failure
        # rolls back only that statement. PostgreSQL aborts the WHOLE transaction
        # on the first failing statement; without savepoints the final COMMIT
        # silently becomes a ROLLBACK and the create_all above is undone too.
        import sqlalchemy as sa

        migrations = [
            "ALTER TABLE projects ADD COLUMN is_paused BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE projects ADD COLUMN owner_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE agents ADD COLUMN scope VARCHAR(10) NOT NULL DEFAULT 'universal'",
            "ALTER TABLE agents ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE projects ADD COLUMN watch_folder_path VARCHAR(1000)",
            "ALTER TABLE chat_sessions ADD COLUMN thinking_mode VARCHAR(20) "
            "NOT NULL DEFAULT 'server_default'",
            "ALTER TABLE chat_sessions ADD COLUMN endpoint_override VARCHAR(120)",
            # MFA / 2FA columns
            "ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)",
            "ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN totp_last_accepted_counter INTEGER",
            "ALTER TABLE users ADD COLUMN totp_pending_expires_at DATETIME",
            "ALTER TABLE users ADD COLUMN recovery_codes_hashed TEXT",
            "ALTER TABLE users ADD COLUMN passkey_enabled BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE users ALTER COLUMN totp_secret TYPE TEXT",
            # Widen password_hash for Argon2id hashes. SQLite ignores this, but
            # PostgreSQL needs the larger column for Argon2id hashes.
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
            "ALTER TABLE connection_strings ADD COLUMN token_type VARCHAR(40) "
            "NOT NULL DEFAULT 'user_invite'",
            "ALTER TABLE connection_strings ADD COLUMN ws_url VARCHAR(1000) NOT NULL DEFAULT ''",
            "ALTER TABLE connection_strings ADD COLUMN intended_role VARCHAR(40) "
            "NOT NULL DEFAULT 'researcher'",
            "ALTER TABLE connection_strings ADD COLUMN connection_string_hash VARCHAR(64)",
            "ALTER TABLE connection_strings ADD COLUMN allowed_project_ids_json TEXT "
            "NOT NULL DEFAULT '[]'",
            "ALTER TABLE mcp_server_configs ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE mcp_audit_log ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_mcp_audit_log_project_id ON mcp_audit_log(project_id)",
            # Scheduler/loops hardening columns for existing installations.
            "ALTER TABLE loop_executions ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_loop_executions_project_id "
            "ON loop_executions(project_id)",
            "ALTER TABLE a2a_messages ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_a2a_messages_project_id ON a2a_messages(project_id)",
            # Finding provenance for approved-task-only reporting.
            "ALTER TABLE nuggets ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_nuggets_task_id ON nuggets(task_id)",
            "ALTER TABLE facts ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_facts_task_id ON facts(task_id)",
            "ALTER TABLE insights ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_insights_task_id ON insights(task_id)",
            "ALTER TABLE recommendations ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_recommendations_task_id ON recommendations(task_id)",
            "ALTER TABLE scheduled_tasks ADD COLUMN is_running BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE scheduled_tasks ADD COLUMN agent_id VARCHAR(36)",
            "ALTER TABLE scheduled_tasks ADD COLUMN loop_type VARCHAR(50) NOT NULL DEFAULT 'cron'",
            "ALTER TABLE scheduled_tasks ADD COLUMN interval_seconds INTEGER",
            "ALTER TABLE scheduled_tasks ADD COLUMN execution_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE scheduled_tasks ADD COLUMN last_status VARCHAR(20) NOT NULL DEFAULT ''",
            # Checkpoint/recovery hardening.
            "ALTER TABLE task_checkpoints ADD COLUMN agent_state VARCHAR(20) "
            "NOT NULL DEFAULT 'idle'",
            # F-P1: checkpoint timestamps must be timestamptz to match the
            # UTC-aware model defaults (asyncpg rejects aware datetimes for
            # naive columns). Postgres-only type change; SQLite tolerates.
            "ALTER TABLE task_checkpoints ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE task_checkpoints ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE",
            # WebAuthn credential metadata and persisted challenge state.
            "ALTER TABLE webauthn_credentials ADD COLUMN device_type VARCHAR(50) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE webauthn_credentials ADD COLUMN backed_up BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE webauthn_credentials ADD COLUMN user_verified BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE webauthn_credentials ADD COLUMN last_used_ip VARCHAR(128) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE webauthn_credentials ADD COLUMN last_used_user_agent VARCHAR(512) "
            "NOT NULL DEFAULT ''",
            # Research-validity architecture: evidence units, coding runs, route evidence.
            "ALTER TABLE evidence_units ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_evidence_units_task_id ON evidence_units(task_id)",
            "ALTER TABLE coding_runs ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_coding_runs_task_id ON coding_runs(task_id)",
            "ALTER TABLE research_evidence_edges ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_research_evidence_edges_task_id "
            "ON research_evidence_edges(task_id)",
            "ALTER TABLE code_applications ADD COLUMN evidence_unit_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_code_applications_evidence_unit_id "
            "ON code_applications(evidence_unit_id)",
            "ALTER TABLE code_applications ADD COLUMN coding_run_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_code_applications_coding_run_id "
            "ON code_applications(coding_run_id)",
            "ALTER TABLE code_applications ADD COLUMN task_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_code_applications_task_id ON code_applications(task_id)",
            "ALTER TABLE code_applications ADD COLUMN start_offset INTEGER",
            "ALTER TABLE code_applications ADD COLUMN end_offset INTEGER",
            "ALTER TABLE code_applications ADD COLUMN model_name VARCHAR(200) NOT NULL DEFAULT ''",
            "ALTER TABLE code_applications ADD COLUMN donor_id VARCHAR(120) NOT NULL DEFAULT ''",
            "ALTER TABLE code_applications ADD COLUMN route_id VARCHAR(120) NOT NULL DEFAULT ''",
            "ALTER TABLE code_applications ADD COLUMN route_evidence_json TEXT "
            "NOT NULL DEFAULT '{}'",
            "ALTER TABLE code_applications ADD COLUMN reliability_status VARCHAR(40) "
            "NOT NULL DEFAULT 'unknown'",
            "ALTER TABLE code_applications ADD COLUMN reconciliation_status VARCHAR(40) "
            "NOT NULL DEFAULT 'unreconciled'",
            "ALTER TABLE code_applications ADD COLUMN promotion_status VARCHAR(40) "
            "NOT NULL DEFAULT 'blocked'",
            # Telemetry stays content-free but now carries research-validity audit handles.
            "ALTER TABLE telemetry_spans ADD COLUMN event_kind VARCHAR(80) NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN route_id VARCHAR(120) NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN donor_id VARCHAR(120) NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN retrieval_mode VARCHAR(40) NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN coding_run_id VARCHAR(36) NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN evidence_unit_id VARCHAR(36) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN codebook_version_id VARCHAR(36) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE telemetry_spans ADD COLUMN reliability_score FLOAT",
            # Project-scoped model/skill learning. Global stats must not steer
            # another project's research process.
            "ALTER TABLE model_skill_stats ADD COLUMN project_id VARCHAR(36) NOT NULL DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_model_skill_stats_project_id "
            "ON model_skill_stats(project_id)",
            # Per-experiment autoresearch engine selection (W6). Nullable so
            # pre-W6 rows keep an honest "unknown engine" (NULL).
            "ALTER TABLE autoresearch_experiments ADD COLUMN engine VARCHAR(16)",
            "CREATE INDEX IF NOT EXISTS ix_autoresearch_experiments_engine "
            "ON autoresearch_experiments(engine)",
            # Chat usage menu: scope exact/estimated totals to one session.
            "ALTER TABLE agentic_usage_rows ADD COLUMN session_id VARCHAR(36)",
            "CREATE INDEX IF NOT EXISTS ix_agentic_usage_rows_session_id "
            "ON agentic_usage_rows(session_id)",
        ]
        for ddl in migrations:
            try:
                async with conn.begin_nested():
                    await conn.execute(sa.text(ddl))
            except Exception:
                pass  # Column already exists or SQLite doesn't support this DDL

        # Create tables with follow-up lightweight migrations when needed.
        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["webauthn_credentials"].create(
                        c, checkfirst=True
                    )
                )
        except Exception:
            pass  # Table already exists

        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["webauthn_challenges"].create(c, checkfirst=True)
                )
        except Exception:
            pass  # Table already exists

        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["recovery_codes"].create(c, checkfirst=True)
                )
        except Exception:
            pass  # Table already exists

        try:
            async with conn.begin_nested():
                await conn.execute(
                    sa.text(
                        "ALTER TABLE audit_log ADD COLUMN event_type VARCHAR(80) "
                        "NOT NULL DEFAULT ''"
                    )
                )
        except Exception:
            pass  # Column already exists or audit_log has not been created yet

        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["task_review_events"].create(c, checkfirst=True)
                )
        except Exception:
            pass  # Table already exists

        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["permission_requests"].create(c, checkfirst=True)
                )
        except Exception:
            pass  # Table already exists

        try:
            async with conn.begin_nested():
                await conn.run_sync(
                    lambda c: Base.metadata.tables["project_interface_configs"].create(
                        c, checkfirst=True
                    )
                )
        except Exception:
            pass  # Table already exists

        for table_name in (
            "evidence_units",
            "coding_runs",
            "coding_run_coders",
            "research_evidence_edges",
            "reconciliation_decisions",
        ):
            try:
                async with conn.begin_nested():
                    await conn.run_sync(
                        lambda c, name=table_name: Base.metadata.tables[name].create(
                            c, checkfirst=True
                        )
                    )
            except Exception:
                pass  # Table already exists
