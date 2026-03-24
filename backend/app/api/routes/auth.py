"""Authentication API routes for team mode."""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.core.auth import create_token, hash_password, verify_password
from app.models.database import async_session

router = APIRouter()
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class PreferencesRequest(BaseModel):
    preferences: dict


@router.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user (team mode only)."""
    if not settings.team_mode:
        raise HTTPException(status_code=400, detail="Registration requires team mode. Enable TEAM_MODE=true.")

    from sqlalchemy import select
    from app.models.user import User, UserRole

    async with async_session() as db:
        # Check for existing username/email
        existing = await db.execute(
            select(User).where((User.username == req.username) | (User.email == req.email))
        )
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="Username or email already exists.")

        # First user becomes admin
        count_result = await db.execute(select(User))
        is_first = len(count_result.scalars().all()) == 0

        user = User(
            id=str(uuid.uuid4()),
            username=req.username,
            email=req.email,
            password_hash=hash_password(req.password),
            role=UserRole.ADMIN if is_first else UserRole.RESEARCHER,
            display_name=req.display_name or req.username,
        )
        db.add(user)
        await db.commit()

        token = create_token(user.id, user.username, user.role.value)
        logger.info(f"User registered: {user.username} (role={user.role.value})")

        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "display_name": user.display_name,
                "preferences": json.loads(user.preferences),
            },
        }


@router.post("/auth/login")
async def login(req: LoginRequest):
    """Log in and receive a JWT token."""
    if not settings.team_mode:
        # In local mode, return a dummy token for compatibility
        return {
            "token": "local-mode",
            "user": {
                "id": "local",
                "username": "local",
                "email": "local@localhost",
                "role": "admin",
                "display_name": "Local User",
                "preferences": {},
            },
        }

    from sqlalchemy import select
    from app.models.user import User

    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == req.username))
        user = result.scalars().first()

        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        token = create_token(user.id, user.username, user.role.value)

        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "display_name": user.display_name,
                "preferences": json.loads(user.preferences),
            },
        }


@router.get("/auth/me")
async def get_me(user: dict = None):
    """Get current user info. In local mode, returns a default user."""
    if not settings.team_mode:
        return {
            "id": "local",
            "username": "local",
            "email": "local@localhost",
            "role": "admin",
            "display_name": "Local User",
            "preferences": {},
            "team_mode": False,
        }

    # Extract token from the request — handled by middleware injecting user
    # For now this route requires the auth middleware to populate `user`
    from fastapi import Request

    return {"team_mode": True, "message": "Use Authorization header with JWT token"}


@router.put("/auth/preferences")
async def update_preferences(req: PreferencesRequest):
    """Update user preferences (theme, UI density, etc.)."""
    if not settings.team_mode:
        return {"status": "ok", "preferences": req.preferences}

    return {"status": "ok", "preferences": req.preferences}


@router.get("/auth/team-status")
async def team_status():
    """Check if team mode is enabled and get basic info."""
    return {
        "team_mode": settings.team_mode,
        "registration_enabled": settings.team_mode,
    }
