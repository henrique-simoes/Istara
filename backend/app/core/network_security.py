"""Network Security Middleware — protects Istara when accessible beyond localhost.

When Istara binds to 0.0.0.0 (network-accessible), non-localhost requests
must provide a valid access token. This is a lightweight security layer
that works WITHOUT team mode / PostgreSQL — suitable for LAN deployments
and enterprise networks.

Security model:
- localhost (127.0.0.1, ::1): Always allowed, no token needed
- LAN/remote: Must provide NETWORK_ACCESS_TOKEN via:
  - X-Access-Token header (preferred)
  - Authorization: Bearer <token> header (also accepted)
  - ?token=<token> query parameter (for WebSocket connections)

Exempt paths (always allowed without token):
- /api/health — Docker/monitoring health checks
- /api/auth/login — Login endpoint (needs to be reachable to get JWT)
- /api/auth/register — Registration endpoint
"""

from __future__ import annotations

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket

from app.config import settings

logger = logging.getLogger(__name__)

# Paths that are always accessible without authentication
EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/team-status",
    "/api/settings/status",
    "/api/connections/validate",
    "/api/connections/redeem",
}

# Paths prefixed with these are exempt (for static assets, etc.)
EXEMPT_PREFIXES = (
    "/_next/",  # Next.js static assets
    "/favicon",
)


def _is_localhost(client_host: str | None) -> bool:
    """Check if the request is from localhost."""
    if not client_host:
        return False
    return client_host in ("127.0.0.1", "::1", "localhost")


def _extract_token(request: Request) -> str | None:
    """Extract access token from request headers or query params."""
    # 1. X-Access-Token header (preferred)
    token = request.headers.get("x-access-token", "")
    if token:
        return token

    # 2. Authorization: Bearer <token> (if not a JWT — JWTs are longer)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and len(auth) < 200:  # Access tokens are short
        return auth[7:]

    # 3. Query parameter (for WebSocket and browser access)
    token = request.query_params.get("token", "")
    if token:
        return token

    return None


class NetworkSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces access token for non-localhost requests.

    Activated when NETWORK_ACCESS_TOKEN is set in .env.
    Disabled when empty (backward-compatible — existing setups unaffected).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip if no network token configured (backward-compatible)
        if not settings.network_access_token:
            return await call_next(request)

        # Always allow localhost
        client_host = request.client.host if request.client else None
        if _is_localhost(client_host):
            return await call_next(request)

        # Always allow exempt paths
        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)
        if path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        # Require valid token for non-localhost requests
        token = _extract_token(request)
        if not token or token != settings.network_access_token:
            logger.warning(
                "Network access denied: %s %s from %s (invalid or missing token)",
                request.method, path, client_host,
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Network access token required. "
                    "Set X-Access-Token header or ?token= parameter. "
                    "Configure NETWORK_ACCESS_TOKEN in the server's .env file."
                },
            )

        return await call_next(request)


def check_websocket_network_token(ws: WebSocket) -> bool:
    """Validate network access token for WebSocket connections.

    Call this at the start of WebSocket endpoints for non-localhost clients.
    Returns True if access is allowed, False if denied.
    """
    if not settings.network_access_token:
        return True  # No token configured — allow all

    client_host = ws.client.host if ws.client else None
    if _is_localhost(client_host):
        return True  # Localhost always allowed

    # Check headers
    token = ws.headers.get("x-access-token", "")
    if not token:
        auth = ws.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        token = ws.query_params.get("token", "")

    if token == settings.network_access_token:
        return True

    logger.warning("WebSocket access denied from %s (invalid token)", client_host)
    return False
