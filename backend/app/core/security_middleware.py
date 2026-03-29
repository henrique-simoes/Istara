"""Global Security Middleware — enforces JWT authentication on ALL requests.

This is the primary security layer for ReClaw. Every request to a protected
endpoint MUST carry a valid JWT in the Authorization header. No exceptions
except explicitly exempt paths (health check, login, register, webhooks).

Architecture:
    Request → CORS → SecurityAuthMiddleware → NetworkSecurity → Rate Limiting → Route

Security model:
    - ALL endpoints require JWT authentication by default
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

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

# Paths that NEVER require authentication
EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/team-status",
    "/api/settings/status",
    "/.well-known/agent.json",
}

# Path prefixes that don't require authentication
EXEMPT_PREFIXES = (
    "/_next/",       # Next.js static assets
    "/favicon",      # Browser icon
    "/webhooks/",    # External platform webhooks (have their own verification)
    "/static/",      # Static files
    "/a2a",          # A2A Protocol — agent-to-agent communication (open by spec)
)


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

        # Extract JWT from Authorization header
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Fallback: query parameter (for non-browser clients)
        if not token:
            token = request.query_params.get("token", "")

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Provide Authorization: Bearer <token> header."},
            )

        # Verify JWT
        from app.core.auth import verify_token
        payload = verify_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired authentication token."},
            )

        # Attach user info to request state for downstream use
        request.state.user = {
            "id": payload.get("sub", ""),
            "username": payload.get("username", ""),
            "role": payload.get("role", "researcher"),
        }

        return await call_next(request)


def require_admin_from_request(request: Request) -> None:
    """Check that the authenticated user has admin role.

    Call this in route handlers for admin-only operations.
    Raises 403 if not admin.

    Usage:
        from app.core.security_middleware import require_admin_from_request
        require_admin_from_request(request)
    """
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required.")


def get_user_from_request(request: Request) -> dict:
    """Get the authenticated user from request state.

    Returns the user dict attached by SecurityAuthMiddleware.
    """
    return getattr(request.state, "user", {"id": "unknown", "username": "unknown", "role": "viewer"})
