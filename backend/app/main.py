"""ReClaw — Local-first AI agent for UX Research."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, chat, files, findings, projects, settings, skills, tasks
from app.api.websocket import router as ws_router
from app.agents.devops_agent import devops_agent
from app.agents.ui_audit_agent import ui_audit_agent
from app.core.agent import agent as agent_orchestrator
from app.config import settings as app_settings
from app.core.file_watcher import FileWatcher
from app.models.database import init_db
from app.skills.registry import load_default_skills
from app.skills.skill_manager import skill_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    # Startup
    app_settings.ensure_dirs()
    await init_db()
    load_default_skills()
    skill_manager.load_all()  # Load individual skill definition files

    # Start file watcher
    watcher = FileWatcher()
    watcher_task = asyncio.create_task(watcher.start())
    app.state.file_watcher = watcher

    # Start audit agents and orchestrator
    devops_task = asyncio.create_task(devops_agent.start())
    ui_audit_task = asyncio.create_task(ui_audit_agent.start())
    agent_task = asyncio.create_task(agent_orchestrator.start())

    yield

    # Shutdown
    watcher.stop()
    devops_agent.stop()
    ui_audit_agent.stop()
    agent_orchestrator.stop()

    for task in [watcher_task, devops_task, ui_audit_task, agent_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ReClaw",
    description="Local-first AI agent for UX Research",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(tasks.router, prefix="/api", tags=["Tasks"])
app.include_router(findings.router, prefix="/api", tags=["Findings"])
app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(ws_router)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "reclaw"}


@app.get("/api/skills/registry")
async def list_registered_skills():
    """List all registered skills from the runtime registry."""
    from app.skills.registry import registry
    return registry.to_dict()
