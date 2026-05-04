"""Global Security Middleware — enforces JWT authentication on protected requests.

This is the primary security layer for Istara. Every request to a protected
endpoint MUST carry a valid JWT in the Authorization header. No exceptions
except explicitly exempt paths (health check, login, register, webhooks).

Architecture:
    Request → CORS → SecurityAuthMiddleware → NetworkSecurity → Rate Limiting → Route

Security model:
    - Team-mode endpoints require JWT authentication by default
    - Local mode attaches the built-in local admin user for local-first desktop use
    - Exempt paths: /api/health, /api/auth/login, /api/auth/register,
      /api/auth/team-status, /api/settings/status, /.well-known/agent.json
    - Exempt prefixes: /_next/, /favicon, /webhooks/, /static/, /a2a
    - WebSocket: JWT via ?token= query parameter
    - Admin-only operations checked via request.state.user.role

This middleware makes per-route Depends(get_current_user) unnecessary — auth is
enforced globally. Routes can still use request.state.user to access the
authenticated user's info.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Local mode intentionally has a single built-in admin identity. Route
# dependencies already expose this identity via get_current_user; the global
# middleware must do the same so local desktop mode can bootstrap without a JWT.
LOCAL_ADMIN_USER = {
    "id": "local",
    "username": "local",
    "role": "admin",
}

# Paths that NEVER require authentication
EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/team-status",
    "/api/webauthn/authenticate/start",
    "/api/webauthn/authenticate/finish",
    "/api/settings/status",
    "/api/connections/validate",
    "/api/connections/redeem",
    "/api/updates/version",
    "/api/updates/check",
    "/.well-known/agent.json",
}

# Path prefixes that don't require authentication
EXEMPT_PREFIXES = (
    "/_next/",  # Next.js static assets
    "/favicon",  # Browser icon
    "/webhooks/",  # External platform webhooks (have their own verification)
    "/static/",  # Static files
    "/a2a",  # A2A Protocol — agent-to-agent communication (open by spec)
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _is_exempt(path: str) -> bool:
    """Check if a request path is exempt from authentication.

    Handles trailing-slash variants so that both ``/api/auth/login``
    and ``/api/auth/login/`` are recognised as exempt.
    """
    # Normalise: strip trailing slash for comparison (but keep "/" itself)
    normalised = path.rstrip("/") or "/"
    if normalised in EXEMPT_PATHS:
        return True
    if path.startswith(EXEMPT_PREFIXES):
        return True
    # Root path (frontend)
    if path == "/" or not path.startswith("/api"):
        return True
    return False


def _trusted_origins(request: Request) -> set[str]:
    """Return configured browser origins allowed to use cookie auth."""
    from app.config import settings

    origins = {
        origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()
    }
    origins.add(f"{request.url.scheme}://{request.url.netloc}".rstrip("/"))
    return origins


def _request_origin(request: Request) -> str:
    """Return the browser Origin or Referer origin for CSRF checks."""
    origin = request.headers.get("origin", "").strip()
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer", "").strip()
    if not referer:
        return ""
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _cookie_origin_denial(request: Request) -> str | None:
    """Reject unsafe cross-origin requests that rely on the session cookie."""
    if request.method.upper() in SAFE_METHODS:
        return None
    if not request.cookies.get("istara_session"):
        return None

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return None

    origin = _request_origin(request)
    if not origin:
        return None
    if origin in _trusted_origins(request):
        return None
    return "Untrusted browser origin for cookie-authenticated request."


class SecurityAuthMiddleware(BaseHTTPMiddleware):
    """Global JWT authentication enforcement.

    Every non-exempt request must provide a valid JWT token via:
    - Authorization: Bearer <token> header (HTTP requests)
    - ?token=<token> query parameter (WebSocket connections)

    On success: attaches user info to request.state.user
    On failure: returns 401 Unauthorized JSON response
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt paths
        if _is_exempt(path):
            return await call_next(request)

        # Skip WebSocket upgrade requests — intentional bypass.
        # WebSocket connections cannot be authenticated via HTTP middleware because
        # the protocol upgrade happens before headers are fully available. Each
        # WebSocket endpoint MUST authenticate independently:
        #   - /ws: validates JWT from ?token= query param BEFORE accepting
        #   - /ws/relay: validates network token + JWT BEFORE accepting
        # If you add a new WebSocket endpoint, you MUST add auth in that handler.
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        from app.config import settings

        if not settings.team_mode:
            from app.core.network_security import remote_local_admin_block_reason

            client_host = request.client.host if request.client else None
            local_admin_denial = remote_local_admin_block_reason(client_host, path)
            if local_admin_denial:
                return JSONResponse(
                    status_code=403,
                    content={"detail": local_admin_denial},
                )
            request.state.user = LOCAL_ADMIN_USER.copy()
            return await call_next(request)

        cookie_origin_denial = _cookie_origin_denial(request)
        if cookie_origin_denial:
            return JSONResponse(
                status_code=403,
                content={"detail": cookie_origin_denial},
            )

        # Extract JWT from Authorization header
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Fallback 1: HttpOnly session cookie (cookie-based auth)
        if not token:
            token = request.cookies.get("istara_session", "")

        # Fallback 2: query parameter (for non-browser clients)
        if not token:
            token = request.query_params.get("token", "")

        if not token:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "Authentication required. Provide Authorization: Bearer <token> header."
                    )
                },
            )

        # Verify JWT
        from app.core.auth import verify_token
        from app.core.auth_sessions import current_user_context_for_payload, validate_auth_session
        from app.models.database import async_session

        payload = verify_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired authentication token."},
            )

        async with async_session() as db:
            if not await validate_auth_session(db, payload, request):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or revoked authentication session."},
                )
            user_context = await current_user_context_for_payload(db, payload)
            if not user_context:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authenticated user no longer exists."},
                )

        # Attach user info to request state for downstream use
        request.state.user = user_context

        return await call_next(request)


def require_admin_from_request(request: Request) -> None:
    """Check that the authenticated user has admin role.

    Call this in route handlers for admin-only operations.
    Raises 403 if not admin.

    Usage:
        from app.core.security_middleware import require_admin_from_request
        require_admin_from_request(request)
    """
    from app.core.permissions import require_global_admin

    require_global_admin(request)


def require_admin_or_localhost_for_destructive_action(request: Request, action: str) -> None:
    """Require team admin or localhost for destructive local-mode operations."""
    from app.config import settings
    from app.core.network_security import _is_localhost

    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            raise PermissionError(f"Admin required to {action}")
        return

    client_host = request.client.host if request.client else None
    if not _is_localhost(client_host):
        raise PermissionError(f"Localhost access required to {action} while team mode is disabled")


def get_user_from_request(request: Request) -> dict:
    """Get the authenticated user from request state.

    Returns the user dict attached by SecurityAuthMiddleware.
    """
    return getattr(
        request.state, "user", {"id": "unknown", "username": "unknown", "role": "viewer"}
    )
