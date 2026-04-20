"""Audit Log Middleware — persistent audit trail for all API requests.

Creates a general-purpose audit log model and FastAPI middleware that captures
every HTTP request with user identity, method, path, status, and duration.

This fills the gap identified in P2: the only existing audit trail was
MCP-specific (mcp_audit_log). This provides system-wide coverage for
compliance, debugging, and research audit requirements.
"""

import time
import uuid
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.models.database import Base, async_session
from app.models.database import engine as async_engine

from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column


class AuditLog(Base):
    """General-purpose audit log for all API requests."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    user_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    method: Mapped[str] = mapped_column(String(10), default="")
    path: Mapped[str] = mapped_column(String(500), default="", index=True)
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    ip_address: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    request_body_hash: Mapped[str] = mapped_column(String(64), default="")
    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    details: Mapped[str] = mapped_column(Text, default="")


SKIP_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/health",
}

SKIP_PREFIXES = ("/api/mcp/server",)


async def write_audit_entry(
    user_id: str = "",
    method: str = "",
    path: str = "",
    status_code: int = 0,
    duration_ms: float = 0.0,
    ip_address: str = "",
    user_agent: str = "",
    request_body_hash: str = "",
    project_id: str = "",
    details: str = "",
) -> None:
    """Write an audit log entry to the database."""
    try:
        from sqlalchemy.ext.asyncio import AsyncSession

        async with async_session() as session:
            entry = AuditLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                ip_address=ip_address[:45],
                user_agent=user_agent[:500],
                request_body_hash=request_body_hash,
                project_id=project_id,
                details=details[:2000],
            )
            session.add(entry)
            await session.commit()
    except Exception:
        pass


class AuditLogMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that logs all HTTP requests to the audit_log table."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in SKIP_PATHS or any(path.startswith(p) for p in SKIP_PREFIXES):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        start = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            response = None
            status_code = 500
        else:
            status_code = response.status_code

        duration_ms = (time.monotonic() - start) * 1000

        user_id = ""
        project_id = ""
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.auth import decode_token

                payload = decode_token(auth_header[7:])
                user_id = payload.get("sub", "") if payload else ""
                project_id = payload.get("project_id", "") if payload else ""
            except Exception:
                pass

        path_segments = path.split("/")
        if not project_id and len(path_segments) > 3:
            for i, seg in enumerate(path_segments):
                if seg in (
                    "projects",
                    "metrics",
                    "findings",
                    "tasks",
                    "documents",
                    "agents",
                ) and i + 1 < len(path_segments):
                    project_id = path_segments[i + 1]
                    break

        await write_audit_entry(
            user_id=user_id,
            method=request.method,
            path=path[:500],
            status_code=status_code,
            duration_ms=duration_ms,
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:500],
            request_body_hash="",
            project_id=project_id,
        )

        if response is not None:
            return response

        from starlette.responses import Response as StarletteResponse

        return StarletteResponse(content="Internal Server Error", status_code=500)


def get_recent_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
    project_id: str | None = None,
    method: str | None = None,
    path_prefix: str | None = None,
) -> str:
    """Get recent audit log entries (sync context for API routes).

    Returns a JSON string of audit entries.
    """
    import json

    try:
        from sqlalchemy import select
        from app.models.database import async_session
        import asyncio

        async def _query():
            async with async_session() as session:
                stmt = (
                    select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
                )
                if user_id:
                    stmt = stmt.where(AuditLog.user_id == user_id)
                if project_id:
                    stmt = stmt.where(AuditLog.project_id == project_id)
                if method:
                    stmt = stmt.where(AuditLog.method == method)
                if path_prefix:
                    stmt = stmt.where(AuditLog.path.startswith(path_prefix))
                result = await session.execute(stmt)
                rows = result.scalars().all()
                return [
                    {
                        "id": r.id,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                        "user_id": r.user_id,
                        "method": r.method,
                        "path": r.path,
                        "status_code": r.status_code,
                        "duration_ms": r.duration_ms,
                        "ip_address": r.ip_address,
                        "project_id": r.project_id,
                    }
                    for r in rows
                ]

        return json.dumps(asyncio.get_event_loop().run_until_complete(_query()))
    except Exception as e:
        return json.dumps({"error": str(e)})
