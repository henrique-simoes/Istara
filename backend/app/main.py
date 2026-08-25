"""Istara — Local-first AI agent for UX Research."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.agents.custom_worker import (
    load_custom_agents_from_db,
)
from app.agents.custom_worker import (
    stop_custom_agent as stop_custom_worker,
)
from app.agents.devops_agent import devops_agent
from app.agents.orchestrator import meta_orchestrator
from app.agents.ui_audit_agent import ui_audit_agent
from app.agents.user_sim_agent import user_sim_agent
from app.agents.ux_eval_agent import ux_eval_agent
from app.api.routes import (
    a2a as a2a_routes,
    admin,
    agents,
    audit,
    auth,
    channels,
    chat,
    codebooks,
    documents,
    files,
    findings,
    interfaces,
    memory,
    metrics,
    petals_bridge as petals_bridge_routes,
    projects,
    sessions,
    settings,
    skills,
    tasks,
)
from app.api.routes import autoresearch as autoresearch_routes
from app.api.routes import backup as backup_routes
from app.api.routes import code_applications as code_applications_routes
from app.api.routes import codebook_versions as codebook_versions_routes
from app.api.routes import compute as compute_routes
from app.api.routes import connections as connection_routes
from app.api.routes import (
    context_dag as context_dag_routes,
)
from app.api.routes import context_hierarchy as context_hierarchy_routes
from app.api.routes import deployments as deployment_routes
from app.api.routes import dgmh_archive as dgmh_archive_routes
from app.api.routes import improvement_governance as improvement_governance_routes
from app.api.routes import laws as laws_routes
from app.api.routes import loops as loops_routes
from app.api.routes import mcp as mcp_routes
from app.api.routes import meta_hyperagent as meta_hyperagent_routes
from app.api.routes import notifications as notification_routes
from app.api.routes import permission_requests as permission_request_routes
from app.api.routes import presentation as presentation_routes
from app.api.routes import reasoning_bank as reasoning_bank_routes
from app.api.routes import reports as reports_routes
from app.api.routes import research_validity as research_validity_routes
from app.api.routes import (
    scheduler as scheduler_routes,
)
from app.api.routes import steering as steering_routes
from app.api.routes import surveys as survey_routes
from app.api.routes import updates as update_routes
from app.api.routes import webauthn as webauthn_routes
from app.api.routes import webhooks as webhook_routes
from app.api.websocket import router as ws_router
from app.channels.base import channel_router
from app.config import settings as app_settings
from app.core.agent import agent as agent_orchestrator
from app.core.agent_hooks import register_builtin_hooks
from app.core.audit_middleware import AuditLogMiddleware
from app.core.backup_manager import backup_manager
from app.core.file_watcher import FileWatcher
from app.core.log_redaction import install_sensitive_log_redaction
from app.core.network_security import NetworkSecurityMiddleware, requires_local_admin_network_guard
from app.core.scheduler import scheduler
from app.core.security_middleware import SecurityAuthMiddleware
from app.core.version import read_istara_version
from app.models.database import async_session, init_db
from app.services.agent_service import seed_system_agents
from app.services.heartbeat import heartbeat_manager
from app.skills.registry import load_default_skills
from app.skills.skill_manager import skill_manager

install_sensitive_log_redaction()


def _build_configured_local_llm_node():
    """Build the configured local LLM node with auth/model metadata intact."""
    from app.core.compute_registry import ComputeNode

    local_type = app_settings.llm_provider
    local_host = app_settings.lmstudio_host if local_type == "lmstudio" else app_settings.ollama_host
    model_name = app_settings.lmstudio_model if local_type == "lmstudio" else app_settings.ollama_model
    api_key = app_settings.lmstudio_api_key if local_type == "lmstudio" else ""
    loaded_models = [model_name] if model_name and model_name != "default" else []

    return ComputeNode(
        node_id=f"local-{local_type}",
        name=f"Local {local_type.title()}",
        host=local_host,
        source="local",
        provider_type=local_type,
        priority=1,
        is_local=True,
        is_healthy=True,  # Assume healthy; health loop will verify
        api_key=api_key,
        loaded_models=loaded_models,
    )


def _build_configured_fallback_llm_node():
    """Build an optional authenticated fallback LLM node from settings."""
    fallback_host = (app_settings.llm_fallback_host or "").strip()
    if not fallback_host:
        return None

    from app.core.compute_registry import ComputeNode, infer_provider_type

    fallback_provider = infer_provider_type(
        app_settings.llm_fallback_provider,
        fallback_host,
    )
    fallback_model = (app_settings.llm_fallback_model or "").strip()
    loaded_models = [fallback_model] if fallback_model and fallback_model != "default" else []

    return ComputeNode(
        node_id="configured-llm-fallback",
        name="Configured LLM Fallback",
        host=fallback_host,
        source="network",
        provider_type=fallback_provider,
        priority=5,
        is_local=False,
        is_healthy=True,
        api_key=app_settings.resolve_llm_fallback_api_key(),
        loaded_models=loaded_models,
    )


# Global shutdown flag for graceful termination
_shutting_down = False


def _build_bootstrap_admin_user(
    *,
    user_id: str,
    username: str,
    password_hash: str,
    recovery_codes_hashed: str,
):
    """Create the first admin record with required encrypted-field indexes."""
    from app.core.field_encryption import hash_field
    from app.models.user import User

    email = f"{username}@istara.local"
    return User(
        id=user_id,
        username=username,
        email=email,
        email_hash=hash_field(email),
        password_hash=password_hash,
        role="admin",
        recovery_codes_hashed=None,
    )


def _write_initial_admin_credentials_file(
    *,
    username: str,
    password: str,
    recovery_codes: list[str],
):
    """Write first-start credentials to an owner-only runtime file."""
    import os
    import stat

    path = Path(app_settings.data_dir) / "initial-admin-credentials.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Istara initial admin credentials",
                "",
                f"Username: {username}",
                f"Password: {password}",
                "",
                "Recovery codes:",
                *[f"- {code}" for code in recovery_codes],
                "",
                "Delete this file after the admin password and recovery codes are stored safely.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    global _shutting_down
    # Startup
    app_settings.ensure_dirs()
    app_settings.ensure_secrets()
    try:
        from app.core.auth_origins import (
            production_security_configuration_issues,
            security_configuration_warnings,
        )

        _auth_log = __import__("logging").getLogger(__name__)
        for warning in security_configuration_warnings(app_settings):
            _auth_log.warning("Auth security configuration: %s", warning)
        for issue in production_security_configuration_issues(app_settings):
            _auth_log.error("Production auth security configuration: %s", issue)
    except Exception as e:
        __import__("logging").getLogger(__name__).warning(
            "Auth security configuration check skipped: %s", e
        )

    # Ensure data encryption key exists (auto-generated on first run)
    try:
        from app.core.field_encryption import ensure_encryption_key

        ensure_encryption_key()
    except Exception as e:
        __import__("logging").getLogger(__name__).warning(f"Encryption key setup: {e}")

    # Harden data directory permissions (owner-only access)
    import os
    import stat
    from pathlib import Path

    data_path = Path(app_settings.data_dir)
    if data_path.exists():
        try:
            os.chmod(data_path, stat.S_IRWXU)  # 700: owner only
            for item in data_path.iterdir():
                if item.is_file():
                    os.chmod(item, stat.S_IRUSR | stat.S_IWUSR)  # 600: owner read/write
        except OSError:
            pass  # May fail on some filesystems

    await init_db()

    # Bootstrap admin user if none exists
    try:
        from sqlalchemy import func, select

        from app.core.auth import (
            generate_recovery_codes,
            hash_password,
            is_password_breached,
        )
        from app.core.recovery_codes import replace_recovery_codes
        from app.models.user import User

        async with async_session() as db:
            user_count = await db.execute(select(func.count(User.id)))
            count = user_count.scalar() or 0
            if count == 0:
                import secrets as _s

                admin_user = app_settings.admin_username or "admin"
                admin_pass = app_settings.admin_password or _s.token_urlsafe(16)
                # NIST: breach check for admin password
                if not app_settings.admin_password and await is_password_breached(admin_pass):
                    # Auto-generated password was breached — generate a new one
                    admin_pass = _s.token_urlsafe(16)
                    _log = __import__("logging").getLogger(__name__)
                    _log.warning(
                        "Auto-generated admin password was found in a breach. Generated a new one."
                    )

                # Generate recovery codes for admin user
                recovery_codes = generate_recovery_codes()
                user = _build_bootstrap_admin_user(
                    user_id=str(__import__("uuid").uuid4()),
                    username=admin_user,
                    password_hash=hash_password(admin_pass),
                    recovery_codes_hashed="",
                )
                db.add(user)
                await replace_recovery_codes(
                    db,
                    user_id=user.id,
                    codes=recovery_codes,
                    created_by_user_id=user.id,
                )
                await db.commit()
                _log = __import__("logging").getLogger(__name__)
                credentials_path = _write_initial_admin_credentials_file(
                    username=admin_user,
                    password=admin_pass,
                    recovery_codes=recovery_codes,
                )
                _log.info("=" * 60)
                _log.info("  ADMIN USER CREATED (first startup)")
                _log.info(f"  Username: {admin_user}")
                _log.info("  Initial credentials saved to owner-only file: %s", credentials_path)
                _log.info("  Change this password after first login!")
                _log.info("  Delete the credentials file after secure storage.")
                _log.info("=" * 60)
                # Persist to the runtime env file if auto-generated
                if not app_settings.admin_password:
                    try:
                        from app.core.env_persistence import persist_env_value

                        persist_env_value("ADMIN_PASSWORD", admin_pass)
                    except Exception:
                        pass
    except Exception as e:
        __import__("logging").getLogger(__name__).warning(f"Admin bootstrap skipped: {e}")
    load_default_skills()

    # Seed default system agents
    async with async_session() as db:
        await seed_system_agents(db)
    skill_manager.load_all()

    # Recover incomplete tasks from previous crash
    import logging as _startup_log

    _recovery_log = _startup_log.getLogger("startup.recovery")
    try:
        from app.core.checkpoint import recover_incomplete

        async with async_session() as db:
            recovered = await recover_incomplete(db)
            if recovered:
                _recovery_log.warning(
                    f"Recovered {len(recovered)} incomplete task(s) from last session:"
                )
                for r in recovered:
                    _recovery_log.warning(
                        f"  task={r['task_id']} phase={r['phase']} agent={r['agent_id']}"
                    )
            else:
                _recovery_log.info("No incomplete tasks to recover.")
    except Exception as e:
        _recovery_log.warning(f"Checkpoint recovery skipped: {e}")

    # Startup cleanup: remove orphaned sessions/messages whose project no longer exists
    _cleanup_log = _startup_log.getLogger("startup.cleanup")
    try:
        from sqlalchemy import delete as sa_delete
        from sqlalchemy import select as sa_select

        from app.models.message import Message
        from app.models.project import Project
        from app.models.session import ChatSession

        async with async_session() as db:
            # Find all project IDs that actually exist
            existing_result = await db.execute(sa_select(Project.id))
            existing_ids = {row[0] for row in existing_result.fetchall()}

            # Find orphaned sessions (project_id not in existing projects)
            all_sessions_result = await db.execute(sa_select(ChatSession))
            all_sessions = all_sessions_result.scalars().all()
            orphaned_session_ids = [s.id for s in all_sessions if s.project_id not in existing_ids]

            # Find orphaned messages (session not in any existing session)
            if orphaned_session_ids:
                from app.models.context_dag import ContextDAGNode

                await db.execute(
                    sa_delete(ContextDAGNode).where(
                        ContextDAGNode.session_id.in_(orphaned_session_ids)
                    )
                )
                await db.execute(
                    sa_delete(Message).where(Message.session_id.in_(orphaned_session_ids))
                )
                await db.execute(
                    sa_delete(ChatSession).where(ChatSession.id.in_(orphaned_session_ids))
                )
                await db.commit()
                _cleanup_log.info(
                    f"Startup cleanup: removed {len(orphaned_session_ids)} orphaned session(s)"
                )
            else:
                _cleanup_log.info("Startup cleanup: no orphaned records found")
    except Exception as e:
        _cleanup_log.warning(f"Startup cleanup skipped: {e}")

    import logging

    _log = logging.getLogger(__name__)

    # Load active channel instances from database
    try:
        from app.services.channel_service import load_active_instances
        from app.services.inbound_processor import process_inbound_channel_message

        channel_router.set_handler(process_inbound_channel_message)
        async with async_session() as db:
            loaded = await load_active_instances(db)
        _log.info(f"Loaded {loaded} active channel instance(s)")
    except Exception as e:
        _log.warning(f"Channel instance loading skipped: {e}")

    # Register configured local LLM server FIRST (before discovery)
    try:
        from app.core.compute_registry import compute_registry

        local_node = _build_configured_local_llm_node()
        # Check if already registered (ollama.py _init_llm_router may have done this)
        existing_hosts = {n.host for n in compute_registry._nodes.values()}
        if local_node.host not in existing_hosts:
            compute_registry.register_node(local_node)
            _log.info(f"Registered local LLM server: {local_node.host}")
            existing_hosts.add(local_node.host)
        fallback_node = _build_configured_fallback_llm_node()
        if fallback_node and fallback_node.host not in existing_hosts:
            compute_registry.register_node(fallback_node)
            _log.info(f"Registered configured LLM fallback: {fallback_node.host}")
    except Exception as e:
        _log.warning(f"Local LLM registration failed: {e}")

    # Network discovery: find LLM servers on local network
    try:
        from app.core.network_discovery import discover_and_register

        discovered = await discover_and_register()
        if discovered:
            _log.info(f"Auto-discovered {len(discovered)} LLM servers on the network")
        else:
            _log.info("Network discovery: no additional LLM servers found on local network")
    except Exception as e:
        _log.warning(f"Network discovery skipped: {e}")

    # Load persisted LLM servers from database
    try:
        from app.core.ollama import load_persisted_servers_async

        await load_persisted_servers_async()
    except Exception as e:
        _log.warning(f"Failed to load persisted LLM servers: {e}")

    # Run health checks on all nodes (populates available_models for each)
    try:
        from app.core.compute_registry import compute_registry

        await compute_registry.check_all_health()
        healthy = [n for n in compute_registry._nodes.values() if n.is_healthy]
        _log.info(f"ComputeRegistry: {len(healthy)}/{len(compute_registry._nodes)} nodes healthy")
    except Exception as e:
        _log.warning(f"Health check failed: {e}")

    # Vector store dimension health check
    try:
        from app.core.vector_health import check_embedding_dimensions

        dim_check = await check_embedding_dimensions()
        if dim_check["status"] == "mismatch":
            _log.warning(f"Embedding dimension mismatch: {dim_check['message']}")
        elif dim_check["status"] == "ok":
            _log.info(f"Vector dimensions OK ({dim_check['model_dim']}d)")
    except Exception as e:
        _log.warning(f"Dimension check skipped: {e}")

    # W8 vector-space invariant: both engines must embed with the SAME model —
    # an engine switch must never silently change the embedding space, or
    # every stored vector is invalidated.
    try:
        from app.core.pi_runtime.embeddings_gateway import assert_vector_space_invariant
        from app.core.vector_health import check_embedding_dimensions

        shared_embed_model = await assert_vector_space_invariant(
            dimension_probe=check_embedding_dimensions
        )
        _log.info(f"Vector-space invariant OK (embed model: {shared_embed_model})")
    except Exception as e:
        _log.critical(
            "Vector-space invariant check failed; refusing startup to prevent unsafe "
            "engine switching: %s",
            e,
        )
        raise RuntimeError("vector_space_invariant_violation") from e

    # ── Data integrity check ──
    try:
        from app.core.data_integrity import run_integrity_check

        async with async_session() as _check_db:
            integrity = await run_integrity_check(_check_db)
            if integrity["warnings"]:
                for w in integrity["warnings"]:
                    _log.warning(f"Data integrity: {w}")
                _log.warning(
                    "Run POST /api/settings/data-integrity for full report. "
                    "If you recently switched databases, use "
                    "/api/settings/import-database to restore data."
                )
            else:
                _log.info("Data integrity check passed — no orphaned data.")
    except Exception as e:
        _log.debug(f"Data integrity check skipped: {e}")

    # Start file watcher
    watcher = FileWatcher()
    watcher_task = asyncio.create_task(watcher.start())
    app.state.file_watcher = watcher

    disable_background_agents = os.environ.get(
        "ISTARA_DISABLE_BACKGROUND_AGENTS", ""
    ).lower() in {"1", "true", "yes"}

    autonomous_quality_agents_enabled = app_settings.autonomous_quality_agents_enabled

    # Start project-scoped task workers and orchestrators unless a live harness
    # explicitly needs exclusive model access from process start. Synthetic
    # Dev/Admin QA loops are opt-in because they can create test projects,
    # call audit endpoints, and ask the LLM outside the user's active project.
    if disable_background_agents:
        _log.info("Background agents and scheduler disabled for this process.")
        bg_tasks = []
    elif autonomous_quality_agents_enabled:
        _log.info("Autonomous quality audit/simulation agents enabled.")
        bg_tasks = [
            asyncio.create_task(devops_agent.start()),
            asyncio.create_task(ui_audit_agent.start()),
            asyncio.create_task(ux_eval_agent.start()),
            asyncio.create_task(user_sim_agent.start()),
            asyncio.create_task(agent_orchestrator.start()),
            asyncio.create_task(meta_orchestrator.start()),
            asyncio.create_task(heartbeat_manager.start()),
            asyncio.create_task(scheduler.start()),
        ]
    else:
        _log.info(
            "Autonomous quality audit/simulation agents disabled; "
            "starting project-scoped task workers only."
        )
        bg_tasks = [
            devops_agent.start_task_worker(),
            ui_audit_agent.start_task_worker(),
            ux_eval_agent.start_task_worker(),
            user_sim_agent.start_task_worker(),
            asyncio.create_task(agent_orchestrator.start()),
            asyncio.create_task(meta_orchestrator.start()),
            asyncio.create_task(heartbeat_manager.start()),
            asyncio.create_task(scheduler.start()),
        ]

    # Start custom agent workers from DB
    if not disable_background_agents:
        await load_custom_agents_from_db()

    # Start backup scheduler
    asyncio.create_task(backup_manager.start_scheduled())

    # Meta-Hyperagent is project-scoped. The UI starts the loop only after a
    # user selects an authorized active project.
    try:
        from app.core.meta_hyperagent import meta_hyperagent as mh

        mh.load_confirmed_overrides()
        if app_settings.meta_hyperagent_enabled and not disable_background_agents:
            _log.info("Meta-hyperagent enabled; waiting for active project scope.")
    except Exception as e:
        _log.debug(f"Meta-hyperagent startup skipped: {e}")

    # Background update check (non-blocking, 15s delay)
    try:
        from app.api.routes.updates import check_for_updates_on_startup

        asyncio.create_task(check_for_updates_on_startup())
        _log.info("Startup update check scheduled.")
    except Exception as e:
        _log.debug(f"Startup update check skipped: {e}")

    yield

    # Shutdown
    import logging as _shutdown_log

    _sd_log = _shutdown_log.getLogger("shutdown")
    _sd_log.info("Initiating graceful shutdown...")
    _shutting_down = True

    await channel_router.stop_all()
    watcher.stop()
    backup_manager.stop()
    try:
        from app.core.meta_hyperagent import meta_hyperagent as mh

        mh.stop()
    except Exception:
        pass
    devops_agent.stop()
    ui_audit_agent.stop()
    ux_eval_agent.stop()
    user_sim_agent.stop()
    agent_orchestrator.stop()
    meta_orchestrator.stop()
    heartbeat_manager.stop()
    scheduler.stop()

    # Stop custom agent workers
    from app.agents.custom_worker import get_active_workers

    for worker_id in list(get_active_workers().keys()):
        await stop_custom_worker(worker_id)

    # Wait up to 30s for agents to finish in-flight tasks
    _sd_log.info("Waiting up to 30s for agents to finish in-flight tasks...")
    for _wait_i in range(30):
        if agent_orchestrator._current_task_id is None:
            break
        await asyncio.sleep(1)
    else:
        _sd_log.warning(
            f"Shutdown timeout: agent still working on task {agent_orchestrator._current_task_id}"
        )

    for task in [watcher_task, *bg_tasks]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _sd_log.warning(f"Background task stopped with error during shutdown: {e}")

    # Owned teardown of the supervised Pi runtime worker (Plan C D-C1): cancel
    # runs, terminate, then kill only the child PID it created. No-op when a Pi
    # request never started the worker; never blocks shutdown on a stuck child.
    try:
        from app.core.pi_runtime import shutdown_supervisor

        await shutdown_supervisor()
    except Exception as e:
        _sd_log.warning(f"Pi runtime worker shutdown error: {e}")

    _sd_log.info("Shutdown complete.")


ISTARA_VERSION = read_istara_version()

app = FastAPI(
    title="Istara",
    description="Local-first AI agent for UX Research",
    version=ISTARA_VERSION,
    lifespan=lifespan,
)

app.add_middleware(SecurityAuthMiddleware)

app.add_middleware(AuditLogMiddleware)

register_builtin_hooks()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security-hardening HTTP headers into every response."""

    async def dispatch(self, request, call_next):
        from app.core.security_headers import apply_security_headers

        response = await call_next(request)
        apply_security_headers(response.headers)
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Configurable CORS — set CORS_ORIGINS env var for production/Docker
_cors_origins = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=app_settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Access-Token"],
)

if app_settings.network_access_token or requires_local_admin_network_guard(app_settings):
    app.add_middleware(NetworkSecurityMiddleware)
    import logging

    logging.getLogger(__name__).info(
        "Network security enabled — non-localhost requests require access token or are denied"
    )

# Rate limiting
if app_settings.rate_limit_enabled:
    try:
        from app.core.rate_limiter import limiter

        app.state.limiter = limiter
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded

        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        pass  # slowapi not installed — rate limiting disabled

# API routes
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(webauthn_routes.router, prefix="/api", tags=["WebAuthn"])
app.include_router(steering_routes.router, prefix="/api", tags=["Steering"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(tasks.router, prefix="/api", tags=["Tasks"])
app.include_router(findings.router, prefix="/api", tags=["Findings"])
app.include_router(codebooks.router, prefix="/api", tags=["Codebooks"])
app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])
app.include_router(context_hierarchy_routes.router, prefix="/api", tags=["Context"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(scheduler_routes.router, prefix="/api", tags=["Schedules"])
app.include_router(channels.router, prefix="/api", tags=["Channels"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(context_dag_routes.router, prefix="/api", tags=["Context DAG"])
app.include_router(compute_routes.router, prefix="/api", tags=["Compute"])
# Connection strings and the standalone relay CLI advertise /ws/relay.
# Keep the prefixed /api/ws/relay route above for API consistency, and expose
# this compatibility route so donated-compute clients can connect directly.
app.add_api_websocket_route("/ws/relay", compute_routes.relay_websocket)
app.include_router(interfaces.router, prefix="/api", tags=["Interfaces"])
app.include_router(loops_routes.router, prefix="/api", tags=["Loops"])
app.include_router(notification_routes.router, prefix="/api", tags=["Notifications"])
app.include_router(permission_request_routes.router, prefix="/api", tags=["Permission Requests"])
app.include_router(backup_routes.router, prefix="/api", tags=["Backup"])
app.include_router(meta_hyperagent_routes.router, prefix="/api", tags=["Meta-Hyperagent"])
app.include_router(reasoning_bank_routes.router, prefix="/api", tags=["ReasoningBank"])
app.include_router(
    improvement_governance_routes.router, prefix="/api", tags=["Improvement Governance"]
)
app.include_router(dgmh_archive_routes.router, prefix="/api", tags=["DGM-H Archive"])
app.include_router(deployment_routes.router, prefix="/api", tags=["Deployments"])
app.include_router(survey_routes.router, prefix="/api", tags=["Surveys"])
app.include_router(mcp_routes.router, prefix="/api", tags=["MCP"])
app.include_router(autoresearch_routes.router, prefix="/api", tags=["Autoresearch"])
app.include_router(reports_routes.router, prefix="/api", tags=["Reports"])
app.include_router(research_validity_routes.router, prefix="/api", tags=["Research Validity"])
app.include_router(presentation_routes.router, prefix="/api", tags=["Presentation"])
app.include_router(code_applications_routes.router, prefix="/api", tags=["Code Applications"])
app.include_router(codebook_versions_routes.router, prefix="/api", tags=["Codebook Versions"])
app.include_router(laws_routes.router, prefix="/api", tags=["Laws of UX"])
app.include_router(webhook_routes.router, tags=["Webhooks"])
app.include_router(connection_routes.router, prefix="/api", tags=["Connections"])
app.include_router(update_routes.router, prefix="/api", tags=["Updates"])
app.include_router(ws_router)
app.include_router(a2a_routes.router, tags=["A2A"])
from app.config import settings as _app_settings

app.include_router(
    petals_bridge_routes.router,
    prefix=_app_settings.petals_bridge_base_path,
    tags=["PetalsBridge"],
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "istara"}


@app.get("/api/skill-registry")
async def list_registered_skills():
    """List all registered skills from the runtime registry."""
    from app.skills.registry import registry

    return registry.to_dict()
