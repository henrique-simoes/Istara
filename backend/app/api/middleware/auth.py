"""Authentication middleware — enforces JWT auth in team mode."""

import logging

from fastapi import Depends, HTTPException, Request

from app.config import settings
from app.core.auth import verify_token

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and verify the current user from JWT.

    In local mode (team_mode=False), returns a default local user.
    In team mode, requires a valid Authorization: Bearer <token> header.
    """
    if not settings.team_mode:
        return {
            "id": "local",
            "username": "local",
            "role": "admin",
        }

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return {
        "id": payload["sub"],
        "username": payload["username"],
        "role": payload["role"],
    }


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role for protected operations."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


async def require_researcher(user: dict = Depends(get_current_user)) -> dict:
    """Require at least researcher role."""
    if user["role"] not in ("admin", "researcher"):
        raise HTTPException(status_code=403, detail="Researcher access required.")
    return user
