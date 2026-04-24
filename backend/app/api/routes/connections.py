"""Connection string API routes — generate, validate, and redeem connection strings."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_token, hash_password
from app.core.field_encryption import hash_field
from app.core.connection_string import create_connection_string, decode_connection_string
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db
from app.models.connection_string import ConnectionString

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    server_url: str
    label: str = ""
    expires_hours: int = 168  # 7 days


class ValidateRequest(BaseModel):
    connection_string: str


class RedeemRequest(BaseModel):
    connection_string: str
    username: str
    password: str
    email: str = ""
    display_name: str = ""


@router.post("/connections/generate")
async def generate_connection_string(
    data: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a connection string for inviting team members.
    Admin only. Bundles server URL, network token, and a pre-minted JWT."""
    # Admin enforcement
    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(status_code=403, detail="Admin required to generate connection strings")

    if not data.server_url:
        raise HTTPException(status_code=400, detail="server_url is required")

    conn_str = create_connection_string(
        server_url=data.server_url,
        label=data.label,
        expires_hours=data.expires_hours,
    )

    new_conn = ConnectionString(
        id=str(uuid.uuid4()),
        connection_string=conn_str,
        label=data.label,
        server_url=data.server_url,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=data.expires_hours),
    )
    db.add(new_conn)
    await db.commit()

    return {
        "id": new_conn.id,
        "connection_string": conn_str,
        "server_url": data.server_url,
        "label": data.label,
        "expires_at": new_conn.expires_at.isoformat(),
    }


@router.get("/connections")
async def list_connection_strings(request: Request, db: AsyncSession = Depends(get_db)):
    """List all generated connection strings. Admin only."""
    require_admin_from_request(request)
    result = await db.execute(select(ConnectionString).order_by(ConnectionString.created_at.desc()))
    conns = result.scalars().all()
    return [c.to_dict() for c in conns]


@router.delete("/connections/{conn_id}")
async def revoke_connection_string(conn_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Revoke a connection string. Admin only."""
    require_admin_from_request(request)
    conn = await db.get(ConnectionString, conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection string not found")

    await db.delete(conn)
    await db.commit()
    return {"status": "revoked"}


@router.post("/connections/validate")
async def validate_connection_string(data: ValidateRequest, db: AsyncSession = Depends(get_db)):
    """Validate a connection string without redeeming it.
    Public endpoint — used by clients to preview connection info."""
    payload = decode_connection_string(data.connection_string)
    if not payload:
        return {"valid": False, "error": "Invalid or expired connection string"}

    conn = await _get_redeemable_connection_string(db, data.connection_string)
    if conn is None:
        return {"valid": False, "error": "Connection string has been revoked, redeemed, or expired"}

    return {
        "valid": True,
        "server_url": payload.get("server_url"),
        "ws_url": payload.get("ws_url"),
        "label": payload.get("label"),
        "expires_at": payload.get("expires_at"),
    }


@router.post("/connections/redeem")
async def redeem_connection_string(data: RedeemRequest, db: AsyncSession = Depends(get_db)):
    """Redeem a connection string — creates a user account and returns auth tokens.
    The user can then access the web UI with the JWT and connect a relay with the
    network token."""
    payload = decode_connection_string(data.connection_string)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired connection string")
    conn = await _get_redeemable_connection_string(db, data.connection_string)
    if conn is None:
        raise HTTPException(status_code=400, detail="Connection string has been revoked, redeemed, or expired")

    if not data.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    if not data.password or len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create user account (team mode must be enabled for this)
    if not settings.team_mode:
        # In local mode, just return a local-admin token + network token
        token = create_token("local", data.username.strip(), "admin")
        conn.is_redeemed = True
        await db.commit()
        return {
            "token": token,
            "network_token": payload.get("network_token", ""),
            "server_url": payload.get("server_url", ""),
            "ws_url": payload.get("ws_url", ""),
            "user": {
                "id": "local",
                "username": data.username.strip(),
                "email": "",
                "role": "admin",
                "display_name": data.username.strip(),
            },
        }

    # Team mode — create a real user
    from app.models.user import User, UserRole

    email = data.email.strip() or f"{data.username.strip()}@istara.local"
    email_hash = hash_field(email)
    existing = await db.execute(
        select(User).where(
            (User.username == data.username.strip()) | (User.email_hash == email_hash)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists")

    user = User(
        id=str(uuid.uuid4()),
        username=data.username.strip(),
        email=email,
        email_hash=email_hash,
        password_hash=hash_password(data.password),
        role=UserRole.RESEARCHER,
        display_name=data.display_name.strip() or data.username.strip(),
    )
    db.add(user)
    conn.is_redeemed = True
    await db.commit()

    token = create_token(user.id, user.username, user.role.value)
    logger.info(f"User created via connection string: {user.username}")

    return {
        "token": token,
        "network_token": payload.get("network_token", ""),
        "server_url": payload.get("server_url", ""),
        "ws_url": payload.get("ws_url", ""),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "display_name": user.display_name,
        },
    }


@router.post("/connections/rotate-network-token")
async def rotate_network_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Generate a new NETWORK_ACCESS_TOKEN. Admin only.
    Invalidates all existing connection strings that bundled the old token."""
    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(status_code=403, detail="Admin required")

    new_token = secrets.token_urlsafe(32)
    settings.network_access_token = new_token

    # Persist to .env
    from app.api.routes.settings import _persist_env
    _persist_env("NETWORK_ACCESS_TOKEN", new_token)

    result = await db.execute(select(ConnectionString).where(ConnectionString.is_active.is_(True)))
    for conn in result.scalars().all():
        conn.is_active = False
    await db.commit()

    # Broadcast to connected relays so they know the token changed
    try:
        from app.core.compute_registry import compute_registry
        for node in list(compute_registry._nodes.values()):
            if node.websocket and node.source == "relay":
                try:
                    await node.websocket.send_json({
                        "type": "token_rotated",
                        "message": "Network access token has been rotated. Reconnect with a new connection string.",
                    })
                except Exception:
                    pass
    except Exception:
        pass

    logger.info("Network access token rotated")
    return {"status": "rotated", "token_preview": new_token[:8] + "..."}


async def _get_redeemable_connection_string(
    db: AsyncSession,
    connection_string: str,
) -> ConnectionString | None:
    result = await db.execute(
        select(ConnectionString).where(ConnectionString.connection_string == connection_string)
    )
    conn = result.scalar_one_or_none()
    if not conn or not conn.is_active or conn.is_redeemed:
        return None
    expires_at = conn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return conn
