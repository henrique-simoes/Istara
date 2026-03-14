"""ReClaw — Local-first AI agent for UX Research."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, files, findings, projects, settings, tasks
from app.api.websocket import router as ws_router
from app.config import settings as app_settings
from app.core.file_watcher import FileWatcher
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    # Startup
    app_settings.ensure_dirs()
    await init_db()

    # Start file watcher in background
    watcher = FileWatcher()
    watcher_task = asyncio.create_task(watcher.start())
    app.state.file_watcher = watcher

    yield

    # Shutdown
    watcher.stop()
    watcher_task.cancel()
    try:
        await watcher_task
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
app.include_router(ws_router)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "reclaw"}
