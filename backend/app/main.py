"""ReClaw — Local-first AI agent for UX Research."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agents, audit, auth, channels, chat, codebooks, context_dag as context_dag_routes, documents, files, findings, interfaces, llm_servers, memory, metrics, projects, scheduler as scheduler_routes, sessions, settings, skills, tasks
from app.api.routes import backup as backup_routes
from app.api.routes import compute as compute_routes
from app.api.routes import deployments as deployment_routes
from app.api.routes import loops as loops_routes, notifications as notification_routes
from app.api.routes import surveys as survey_routes
from app.api.routes import mcp as mcp_routes
from app.api.routes import meta_hyperagent as meta_hyperagent_routes
from app.api.routes import autoresearch as autoresearch_routes
from app.api.routes import laws as laws_routes
from app.api.routes import reports as reports_routes
from app.api.routes import code_applications as code_applications_routes
from app.api.routes import codebook_versions as codebook_versions_routes
from app.api.routes import webhooks as webhook_routes
from app.api.routes import connections as connection_routes
from app.api.websocket import router as ws_router
from app.channels.base import channel_router
from app.agents.devops_agent import devops_agent
from app.agents.ui_audit_agent import ui_audit_agent
from app.agents.ux_eval_agent import ux_eval_agent
from app.agents.user_sim_agent import user_sim_agent
from app.agents.orchestrator import meta_orchestrator
from app.agents.custom_worker import load_custom_agents_from_db, stop_custom_agent as stop_custom_worker
from app.config import settings as app_settings
from app.core.agent import agent as agent_orchestrator
from app.core.backup_manager import backup_manager
from app.core.file_watcher import FileWatcher
from app.core.scheduler import scheduler
from app.models.database import async_session, init_db
from app.services.agent_service import seed_system_agents
from app.services.heartbeat import heartbeat_manager
from app.skills.registry import load_default_skills
from app.skills.skill_manager import skill_manager


def _persist_env_startup(key: str, value: str, logger=None) -> None:
    """Persist a key to .env during startup (reuses settings.py logic)."""
    try:
        from app.api.routes.settings import _persist_env
        _persist_env(key, value)
        if logger:
            logger.info(f"Auto-persisted {key}={value} to .env")
    except Exception as e:
        if logger:
            logger.warning(f"Could not persist {key} to .env: {e}")


# Global shutdown flag for graceful termination
_shutting_down = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    global _shutting_down
    # Startup
    app_settings.ensure_dirs()
    app_settings.ensure_secrets()

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

    # Bootstrap admin user if none exists
    try:
        from app.models.user import User
        from app.core.auth import hash_password, create_token
        from sqlalchemy import select, func
        async with async_session() as db:
            user_count = await db.execute(select(func.count(User.id)))
            count = user_count.scalar() or 0
            if count == 0:
                import secrets as _s
                admin_user = app_settings.admin_username or "admin"
                admin_pass = app_settings.admin_password or _s.token_urlsafe(16)
                user = User(
                    id=str(__import__("uuid").uuid4()),
                    username=admin_user,
                    password_hash=hash_password(admin_pass),
                    role="admin",
                )
                db.add(user)
                await db.commit()
                _log = __import__("logging").getLogger(__name__)
                _log.info("=" * 60)
                _log.info("  ADMIN USER CREATED (first startup)")
                _log.info(f"  Username: {admin_user}")
                _log.info(f"  Password: {admin_pass}")
                _log.info("  Change this password after first login!")
                _log.info("=" * 60)
                # Persist to .env if auto-generated
                if not app_settings.admin_password:
                    try:
                        from pathlib import Path
                        env_path = Path(__file__).parent.parent / ".env"
                        lines = env_path.read_text().splitlines() if env_path.exists() else []
                        lines.append(f"ADMIN_PASSWORD={admin_pass}")
                        env_path.write_text("\n".join(lines) + "\n")
                    except Exception:
                        pass
    except Exception as e:
        __import__("logging").getLogger(__name__).warning(f"Admin bootstrap skipped: {e}")
    await init_db()
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
        from sqlalchemy import delete as sa_delete, select as sa_select
        from app.models.session import ChatSession
        from app.models.message import Message
        from app.models.project import Project

        async with async_session() as db:
            # Find all project IDs that actually exist
            existing_result = await db.execute(sa_select(Project.id))
            existing_ids = {row[0] for row in existing_result.fetchall()}

            # Find orphaned sessions (project_id not in existing projects)
            all_sessions_result = await db.execute(sa_select(ChatSession))
            all_sessions = all_sessions_result.scalars().all()
            orphaned_session_ids = [
                s.id for s in all_sessions if s.project_id not in existing_ids
            ]

            # Find orphaned messages (session not in any existing session)
            if orphaned_session_ids:
                from app.models.context_dag import ContextDAGNode
                await db.execute(
                    sa_delete(ContextDAGNode).where(
                        ContextDAGNode.session_id.in_(orphaned_session_ids)
                    )
                )
                await db.execute(
                    sa_delete(Message).where(
                        Message.session_id.in_(orphaned_session_ids)
                    )
                )
                await db.execute(
                    sa_delete(ChatSession).where(
                        ChatSession.id.in_(orphaned_session_ids)
                    )
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
        async with async_session() as db:
            loaded = await load_active_instances(db)
        _log.info(f"Loaded {loaded} active channel instance(s)")
    except Exception as e:
        _log.warning(f"Channel instance loading skipped: {e}")

    # Register configured local LLM server FIRST (before discovery)
    try:
        from app.core.compute_registry import compute_registry, ComputeNode
        local_host = app_settings.lmstudio_host if app_settings.llm_provider == "lmstudio" else app_settings.ollama_host
        local_type = app_settings.llm_provider
        # Check if already registered (ollama.py _init_llm_router may have done this)
        existing_hosts = {n.host for n in compute_registry._nodes.values()}
        if local_host not in existing_hosts:
            local_node = ComputeNode(
                node_id=f"local-{local_type}",
                name=f"Local {local_type.title()}",
                host=local_host,
                source="local",
                provider_type=local_type,
                priority=1,
                is_local=True,
                is_healthy=True,  # Assume healthy; health loop will verify
            )
            compute_registry.register_node(local_node)
            _log.info(f"Registered local LLM server: {local_host}")
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

    # Auto-detect LLM provider: try configured first, fall back to the other
    from app.core.ollama import ollama, auto_detect_provider
    try:
        await auto_detect_provider()
        # Re-import after potential provider switch
        from app.core import ollama as ollama_mod
        current_client = ollama_mod.ollama
        if await current_client.health():
            _log.info(f"LLM provider ({app_settings.llm_provider}) is online.")
            models = await current_client.list_models()
            model_names = [m.get("name", "") for m in models]

            if app_settings.llm_provider == "ollama":
                if not any(app_settings.ollama_model in n for n in model_names):
                    _log.info(f"Pulling default model: {app_settings.ollama_model}")
                    async for _ in current_client.pull_model(app_settings.ollama_model):
                        pass
                # Auto-detect if configured model is "default" or not loaded
                active = app_settings.ollama_model
                if active == "default" or not any(active in n for n in model_names):
                    non_embed = [n for n in model_names if "embed" not in n.lower()]
                    if non_embed:
                        resolved = non_embed[0]
                        app_settings.ollama_model = resolved
                        _log.info(f"Ollama active model resolved to: {resolved}")
                        _persist_env_startup("OLLAMA_MODEL", resolved, _log)
            elif app_settings.llm_provider == "lmstudio":
                # Detect the ACTUALLY loaded model by probing LM Studio.
                # /v1/models lists all downloaded models, not just loaded ones.
                # The only reliable detection is a minimal chat probe — the
                # response's 'model' field reveals which model is serving.
                from app.core.lmstudio import LMStudioClient
                lms_client = current_client if isinstance(current_client, LMStudioClient) else LMStudioClient()
                loaded = await lms_client.detect_loaded_model(force=True)
                if loaded and loaded != app_settings.lmstudio_model:
                    app_settings.lmstudio_model = loaded
                    _log.info(f"LM Studio active model detected: {loaded}")
                    _persist_env_startup("LMSTUDIO_MODEL", loaded, _log)
                elif loaded:
                    _log.info(f"LM Studio model confirmed: {loaded}")
                elif not loaded:
                    # Fallback: pick from model list if probe fails
                    active = app_settings.lmstudio_model
                    non_embed = [n for n in model_names if "embed" not in n.lower()]
                    if active == "default" or (active and active not in model_names):
                        if non_embed:
                            resolved = non_embed[0]
                            app_settings.lmstudio_model = resolved
                            _log.info(f"LM Studio model fallback to: {resolved}")
                            _persist_env_startup("LMSTUDIO_MODEL", resolved, _log)
                        elif model_names:
                            app_settings.lmstudio_model = model_names[0]
                            _persist_env_startup("LMSTUDIO_MODEL", model_names[0], _log)
        else:
            _log.warning(f"LLM provider ({app_settings.llm_provider}) is not reachable.")
    except Exception:
        pass  # Don't block startup if provider check fails

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
                    "If you recently switched databases, use /api/settings/import-database to restore data."
                )
            else:
                _log.info("Data integrity check passed — no orphaned data.")
    except Exception as e:
        _log.debug(f"Data integrity check skipped: {e}")

    # Start file watcher
    watcher = FileWatcher()
    watcher_task = asyncio.create_task(watcher.start())
    app.state.file_watcher = watcher

    # Start all agents and orchestrator
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

    # Start custom agent workers from DB
    await load_custom_agents_from_db()

    # Start backup scheduler
    asyncio.create_task(backup_manager.start_scheduled())

    # Meta-Hyperagent: always load confirmed overrides; conditionally start loop
    try:
        from app.core.meta_hyperagent import meta_hyperagent as mh
        mh.load_confirmed_overrides()
        if app_settings.meta_hyperagent_enabled:
            asyncio.create_task(mh.start_observation_loop())
            _log.info("Meta-hyperagent observation loop started.")
    except Exception as e:
        _log.debug(f"Meta-hyperagent startup skipped: {e}")

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

    _sd_log.info("Shutdown complete.")


app = FastAPI(
    title="ReClaw",
    description="Local-first AI agent for UX Research",
    version="0.1.0",
    lifespan=lifespan,
)

# Global JWT authentication enforcement — ALL endpoints require auth
from app.core.security_middleware import SecurityAuthMiddleware
app.add_middleware(SecurityAuthMiddleware)


# Security headers — prevent clickjacking, MIME sniffing, and XSS
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security-hardening HTTP headers into every response."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Configurable CORS — set CORS_ORIGINS env var for production/Docker
_cors_origins = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Access-Token"],
)

# Network security — access token for non-localhost connections
if app_settings.network_access_token:
    from app.core.network_security import NetworkSecurityMiddleware
    app.add_middleware(NetworkSecurityMiddleware)
    import logging
    logging.getLogger(__name__).info(
        "Network security enabled — non-localhost requests require access token"
    )

# Rate limiting
if app_settings.rate_limit_enabled:
    try:
        from app.core.rate_limiter import limiter
        app.state.limiter = limiter
        from slowapi.errors import RateLimitExceeded
        from slowapi import _rate_limit_exceeded_handler
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        pass  # slowapi not installed — rate limiting disabled

# API routes
app.include_router(auth.router, prefix="/api", tags=["Auth"])
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
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(scheduler_routes.router, prefix="/api", tags=["Schedules"])
app.include_router(channels.router, prefix="/api", tags=["Channels"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(context_dag_routes.router, prefix="/api", tags=["Context DAG"])
app.include_router(llm_servers.router, prefix="/api", tags=["LLM Servers"])
app.include_router(compute_routes.router, prefix="/api", tags=["Compute"])
app.include_router(interfaces.router, prefix="/api", tags=["Interfaces"])
app.include_router(loops_routes.router, prefix="/api", tags=["Loops"])
app.include_router(notification_routes.router, prefix="/api", tags=["Notifications"])
app.include_router(backup_routes.router, prefix="/api", tags=["Backup"])
app.include_router(meta_hyperagent_routes.router, prefix="/api", tags=["Meta-Hyperagent"])
app.include_router(deployment_routes.router, prefix="/api", tags=["Deployments"])
app.include_router(survey_routes.router, prefix="/api", tags=["Surveys"])
app.include_router(mcp_routes.router, prefix="/api", tags=["MCP"])
app.include_router(autoresearch_routes.router, prefix="/api", tags=["Autoresearch"])
app.include_router(reports_routes.router, prefix="/api", tags=["Reports"])
app.include_router(code_applications_routes.router, prefix="/api", tags=["Code Applications"])
app.include_router(codebook_versions_routes.router, prefix="/api", tags=["Codebook Versions"])
app.include_router(laws_routes.router, prefix="/api", tags=["Laws of UX"])
app.include_router(webhook_routes.router, tags=["Webhooks"])
app.include_router(connection_routes.router, prefix="/api", tags=["Connections"])
app.include_router(ws_router)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "reclaw"}


@app.get("/api/skill-registry")
async def list_registered_skills():
    """List all registered skills from the runtime registry."""
    from app.skills.registry import registry
    return registry.to_dict()


@app.get("/.well-known/agent.json")
async def agent_card():
    """A2A Protocol: Agent Card discovery endpoint."""
    return {
        "name": "ReClaw",
        "description": "Local-first AI agent for UX Research — analyzes interviews, surveys, usability tests and more using 40+ research skills.",
        "url": "http://localhost:8000",
        "version": "0.1.0",
        "protocol_version": "0.1",
        "capabilities": {
            "streaming": False,
            "push_notifications": False,
            "state_transition_history": True,
        },
        "skills": [
            {
                "id": "ux-research",
                "name": "UX Research Analysis",
                "description": "Analyzes user interviews, surveys, usability tests, and field studies to extract insights and recommendations.",
                "tags": ["ux", "research", "analysis", "interviews", "surveys"],
                "examples": [
                    "Analyze these interview transcripts",
                    "Run thematic analysis on survey responses",
                    "Create personas from research data",
                ],
            }
        ],
        "default_input_modes": ["text/plain", "application/json"],
        "default_output_modes": ["application/json"],
    }


@app.post("/a2a")
async def a2a_jsonrpc(request: Request):
    """A2A Protocol: JSON-RPC 2.0 endpoint for agent-to-agent communication."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
        )

    method = body.get("method", "")
    params = body.get("params", {})
    req_id = body.get("id")

    if method == "tasks/send":
        # Create a task from A2A message
        from app.models.database import async_session as a2a_session
        from app.services import a2a as a2a_svc
        async with a2a_session() as db:
            msg = await a2a_svc.send_message(
                db,
                from_agent_id=params.get("from", "external"),
                to_agent_id=params.get("to", "reclaw-main"),
                message_type="a2a_task",
                content=params.get("message", {}).get("text", ""),
                metadata=params.get("message", {}).get("metadata"),
            )
            return {"jsonrpc": "2.0", "result": {"id": msg["id"], "status": "submitted"}, "id": req_id}

    elif method == "tasks/get":
        task_id = params.get("id")
        from app.models.database import async_session as a2a_session
        from app.services import a2a as a2a_svc
        async with a2a_session() as db:
            messages = await a2a_svc.get_full_log(db, limit=200)
            task = next((m for m in messages if m["id"] == task_id), None)
            if task:
                return {"jsonrpc": "2.0", "result": task, "id": req_id}
            return JSONResponse(
                status_code=404,
                content={"jsonrpc": "2.0", "error": {"code": -32001, "message": "Task not found"}, "id": req_id},
            )

    elif method == "tasks/list":
        from app.models.database import async_session as a2a_session
        from app.services import a2a as a2a_svc
        async with a2a_session() as db:
            messages = await a2a_svc.get_full_log(db, limit=params.get("limit", 50))
            return {"jsonrpc": "2.0", "result": {"tasks": messages}, "id": req_id}

    elif method == "tasks/cancel":
        return {"jsonrpc": "2.0", "result": {"status": "canceled"}, "id": req_id}

    elif method == "agent/discover":
        # Return list of available agents
        from app.models.database import async_session as a2a_session
        from app.services import agent_service
        async with a2a_session() as db:
            agents = await agent_service.list_agents(db)
            return {"jsonrpc": "2.0", "result": {"agents": agents}, "id": req_id}

    else:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id},
        )
