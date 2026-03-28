"""Authentication API routes for team mode."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_token, hash_password, verify_password
from app.core.security_middleware import require_admin_from_request
from app.models.database import async_session, get_db
from app.models.user import User

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


# ---------------------------------------------------------------------------
# Admin User Management
# ---------------------------------------------------------------------------


@router.get("/auth/users")
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    """List all users. Admin only."""
    require_admin_from_request(request)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else u.role,
            "display_name": u.display_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/auth/users")
async def create_user(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user. Admin only. Works regardless of TEAM_MODE."""
    require_admin_from_request(request)
    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role="researcher",
        display_name=body.display_name or body.username,
    )
    db.add(user)
    await db.commit()
    logger.info("Admin created user: %s", user.username)
    return {"id": user.id, "username": user.username, "role": "researcher"}


@router.delete("/auth/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a user. Admin only. Cannot delete yourself."""
    require_admin_from_request(request)
    current = getattr(request.state, "user", {})
    if current.get("id") == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    logger.info("Admin deleted user: %s (id=%s)", user.username, user_id)
    return {"deleted": True}


@router.patch("/auth/users/{user_id}/role")
async def change_role(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role. Admin only."""
    require_admin_from_request(request)
    body = await request.json()
    new_role = body.get("role", "")
    if new_role not in ("admin", "researcher", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = new_role
    await db.commit()
    logger.info("Admin changed role for %s to %s", user.username, new_role)
    return {
        "id": user.id,
        "username": user.username,
        "role": new_role,
    }
