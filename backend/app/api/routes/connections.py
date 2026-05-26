"""Connection string API routes — generate, validate, and redeem connection strings."""

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_token, generate_recovery_codes, hash_password
from app.core.auth_sessions import issue_auth_session_token
from app.core.client_identity import BoundedWindowRateLimiter, get_client_ip
from app.core.connection_string import (
    create_compute_donation_string,
    create_connection_string,
    decode_connection_string,
    hash_connection_string,
    preview_connection_string,
)
from app.core.env_persistence import persist_env_value
from app.core.field_encryption import hash_field
from app.core.recovery_codes import replace_recovery_codes
from app.core.security_middleware import require_admin_from_request
from app.models.connection_string import ConnectionString
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)
_validation_limiter = BoundedWindowRateLimiter()
_redeem_limiter = BoundedWindowRateLimiter()
VALIDATION_RATE_LIMIT = 30
VALIDATION_RATE_WINDOW_S = 60
REDEEM_RATE_LIMIT = 10
REDEEM_RATE_WINDOW_S = 300


def _ensure_network_access_token() -> tuple[str, bool]:
    """Ensure compute donation strings can authenticate relay connections."""
    token = (settings.network_access_token or "").strip()
    if token:
        return token, False

    token = secrets.token_urlsafe(32)
    settings.network_access_token = token
    try:
        persist_env_value("NETWORK_ACCESS_TOKEN", token)
    except Exception as exc:
        logger.warning("Could not persist generated NETWORK_ACCESS_TOKEN: %s", exc)
    return token, True


def _strip_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_url(value: str, *, schemes: set[str], field_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in schemes or not parsed.hostname:
        allowed = ", ".join(sorted(schemes))
        raise ValueError(f"{field_name} must be an absolute URL using {allowed}")
    return value.rstrip("/")


class GenerateRequest(BaseModel):
    server_url: str = Field(..., min_length=8, max_length=2048)
    ws_url: str = Field(default="", max_length=2048)
    label: str = Field(default="", max_length=120)
    expires_hours: int = Field(default=168, ge=1, le=8760)  # 7 days, max 1 year
    role: Literal["admin", "researcher", "viewer"] = "researcher"

    @field_validator("server_url", mode="before")
    @classmethod
    def validate_server_url(cls, value: object) -> str:
        return _validate_url(_strip_text(value), schemes={"http", "https"}, field_name="server_url")

    @field_validator("ws_url", mode="before")
    @classmethod
    def validate_ws_url(cls, value: object) -> str:
        text = _strip_text(value)
        if not text:
            return ""
        return _validate_url(text, schemes={"ws", "wss"}, field_name="ws_url")

    @field_validator("label", mode="before")
    @classmethod
    def normalize_label(cls, value: object) -> str:
        return _strip_text(value)


class ComputeDonationGenerateRequest(BaseModel):
    server_url: str = Field(..., min_length=8, max_length=2048)
    ws_url: str = Field(default="", max_length=2048)
    label: str = Field(default="", max_length=120)
    expires_hours: int = Field(default=168, ge=1, le=8760)
    allowed_project_ids: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("server_url", mode="before")
    @classmethod
    def validate_server_url(cls, value: object) -> str:
        return _validate_url(_strip_text(value), schemes={"http", "https"}, field_name="server_url")

    @field_validator("ws_url", mode="before")
    @classmethod
    def validate_ws_url(cls, value: object) -> str:
        text = _strip_text(value)
        if not text:
            return ""
        return _validate_url(text, schemes={"ws", "wss"}, field_name="ws_url")

    @field_validator("label", mode="before")
    @classmethod
    def normalize_label(cls, value: object) -> str:
        return _strip_text(value)

    @field_validator("allowed_project_ids", mode="before")
    @classmethod
    def normalize_allowed_project_ids(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("allowed_project_ids must be a list")
        normalized: list[str] = []
        for item in value:
            project_id = _strip_text(item)
            if project_id and project_id not in normalized:
                normalized.append(project_id)
        return normalized


class ValidateRequest(BaseModel):
    connection_string: str = Field(..., min_length=1, max_length=20000)


class RedeemRequest(BaseModel):
    connection_string: str = Field(..., min_length=1, max_length=20000)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=256)
    email: str = Field(default="", max_length=320)
    display_name: str = Field(default="", max_length=120)

    @field_validator("username", "email", "display_name", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        return _strip_text(value)


@router.post("/connections/generate")
async def generate_connection_string(
    data: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a connection string for inviting team members.
    Admin only. User invite strings never carry compute relay credentials."""
    # Admin enforcement
    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(
                status_code=403, detail="Admin required to generate connection strings"
            )

    if not data.server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    if data.role not in ("admin", "researcher", "viewer"):
        raise HTTPException(status_code=422, detail="role must be admin, researcher, or viewer")

    conn_str = create_connection_string(
        server_url=data.server_url,
        ws_url=data.ws_url or None,
        label=data.label,
        expires_hours=data.expires_hours,
        role=data.role,
    )

    new_conn = ConnectionString(
        id=str(uuid.uuid4()),
        connection_string=preview_connection_string(conn_str),
        connection_string_hash=hash_connection_string(conn_str),
        token_type="user_invite",
        label=data.label,
        server_url=data.server_url,
        ws_url=data.ws_url or "",
        intended_role=data.role,
        expires_at=datetime.now(UTC) + timedelta(hours=data.expires_hours),
    )
    db.add(new_conn)
    await db.commit()
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="pooled_compute_connection_strings",
            source_system="connection_strings",
            source_id=f"invite:{new_conn.id}",
            agent_id="connection-string-service",
            summary="User invite connection string generated with hashed storage.",
            evidence={
                "passed": True,
                "connection_id": new_conn.id,
                "token_type": "user_invite",
                "intended_role": data.role,
                "has_hash": bool(new_conn.connection_string_hash),
            },
        )
    except Exception:
        pass

    return {
        "id": new_conn.id,
        "connection_string": conn_str,
        "server_url": data.server_url,
        "label": data.label,
        "expires_at": new_conn.expires_at.isoformat(),
    }


@router.post("/connections/compute-donation/generate")
async def generate_compute_donation_string(
    data: ComputeDonationGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a relay/compute donation string. Admin only.

    Donation strings are intentionally not redeemable as user accounts.
    """
    if settings.team_mode:
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(
                status_code=403, detail="Admin required to generate compute donation strings"
            )

    if not data.server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    allowed_project_ids = list(data.allowed_project_ids)
    if settings.team_mode:
        if not allowed_project_ids:
            raise HTTPException(
                status_code=422,
                detail="Select at least one project for compute donation access",
            )
        from app.models.project import Project

        result = await db.execute(select(Project.id).where(Project.id.in_(allowed_project_ids)))
        existing_ids = {str(project_id) for project_id in result.scalars().all()}
        unknown_ids = [project_id for project_id in allowed_project_ids if project_id not in existing_ids]
        if unknown_ids:
            raise HTTPException(status_code=404, detail="One or more projects were not found")
    elif not allowed_project_ids:
        allowed_project_ids = ["*"]

    network_token, network_token_created = _ensure_network_access_token()

    conn_str = create_compute_donation_string(
        server_url=data.server_url,
        ws_url=data.ws_url or None,
        label=data.label,
        expires_hours=data.expires_hours,
        allowed_project_ids=allowed_project_ids,
    )
    payload = decode_connection_string(conn_str) or {}

    new_conn = ConnectionString(
        id=str(uuid.uuid4()),
        connection_string=preview_connection_string(conn_str),
        connection_string_hash=hash_connection_string(conn_str),
        token_type="compute_donation",
        label=data.label,
        server_url=data.server_url,
        ws_url=payload.get("ws_url", data.ws_url or ""),
        intended_role="compute_node",
        allowed_project_ids_json=json.dumps(allowed_project_ids),
        expires_at=datetime.now(UTC) + timedelta(hours=data.expires_hours),
    )
    db.add(new_conn)
    await db.commit()
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="pooled_compute_connection_strings",
            source_system="connection_strings",
            source_id=f"compute_donation:{new_conn.id}",
            agent_id="connection-string-service",
            summary="Compute donation connection string generated with hashed storage.",
            evidence={
                "passed": True,
                "connection_id": new_conn.id,
                "token_type": "compute_donation",
                "has_hash": bool(new_conn.connection_string_hash),
                "has_ws_url": bool(new_conn.ws_url),
                "allowed_project_count": len(allowed_project_ids),
                "network_token_configured": bool(network_token),
                "network_token_auto_created": network_token_created,
            },
        )
    except Exception:
        pass

    return {
        "id": new_conn.id,
        "connection_string": conn_str,
        "token_type": "compute_donation",
        "server_url": data.server_url,
        "ws_url": new_conn.ws_url,
        "allowed_project_ids": allowed_project_ids,
        "network_token_configured": bool(network_token),
        "network_token_auto_created": network_token_created,
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
async def revoke_connection_string(
    conn_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Revoke a connection string. Admin only."""
    require_admin_from_request(request)
    conn = await db.get(ConnectionString, conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection string not found")

    conn.is_active = False
    await db.commit()
    return {"status": "revoked"}


@router.post("/connections/validate")
async def validate_connection_string(
    data: ValidateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate a connection string without redeeming it.
    Public endpoint — used by clients to preview connection info."""
    client_id = get_client_ip(request, settings.trusted_proxy_hosts)
    if _is_validation_rate_limited(client_id):
        return {"valid": False, "error": "Too many validation attempts. Try again shortly."}

    payload = decode_connection_string(data.connection_string)
    if not payload:
        return {"valid": False, "error": "Invalid or expired connection string"}

    conn, reason = await _get_connection_string_status(db, data.connection_string)
    if conn is None:
        return {"valid": False, "error": _connection_error_message(reason)}
    conn.last_validated_at = datetime.now(UTC)
    await db.commit()

    return {
        "valid": True,
        "token_type": payload.get("kind", getattr(conn, "token_type", "user_invite")),
        "server_url": payload.get("server_url"),
        "ws_url": payload.get("ws_url"),
        "label": payload.get("label"),
        "expires_at": payload.get("expires_at"),
    }


@router.post("/connections/redeem")
async def redeem_connection_string(
    data: RedeemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Redeem a user invite connection string.

    Redemption creates the account and returns a server-backed auth token.
    User invite strings do not carry relay credentials; compute donation
    strings are the separate relay bootstrap path.
    """
    client_id = get_client_ip(request, settings.trusted_proxy_hosts)
    if _is_redeem_rate_limited(client_id):
        raise HTTPException(
            status_code=429, detail="Too many redemption attempts. Try again shortly."
        )

    payload = decode_connection_string(data.connection_string)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired connection string")
    conn, reason = await _get_connection_string_status(db, data.connection_string)
    if conn is None:
        raise HTTPException(status_code=400, detail=_connection_error_message(reason))
    if payload.get("server_url", "").rstrip("/") != conn.server_url.rstrip("/"):
        raise HTTPException(status_code=400, detail="Connection string server mismatch")
    if payload.get("kind", conn.token_type) != conn.token_type:
        raise HTTPException(status_code=400, detail="Connection string type mismatch")
    token_type = payload.get("kind", conn.token_type or "user_invite")
    if token_type != "user_invite":
        raise HTTPException(
            status_code=400, detail="Compute donation strings cannot create user accounts"
        )

    if not data.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    if not data.password or len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create user account (team mode must be enabled for this)
    if not settings.team_mode:
        # In local mode, just return a local-admin token + network token
        token = create_token("local", data.username.strip(), "admin")
        conn.is_redeemed = True
        conn.redeemed_by_user_id = "local"
        conn.redeemed_username = data.username.strip()
        conn.redeemed_at = datetime.now(UTC)
        await db.commit()
        try:
            from app.core.improvement_governance import improvement_governance

            await improvement_governance.record_feature_evidence(
                feature="pooled_compute_connection_strings",
                source_system="connection_strings",
                source_id=f"redeem:{conn.id}",
                agent_id="connection-string-service",
                summary="Connection string redeemed in local mode.",
                evidence={
                    "passed": True,
                    "connection_id": conn.id,
                    "token_type": token_type,
                    "local_mode": True,
                },
            )
        except Exception:
            pass
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

    recovery_codes = generate_recovery_codes()

    user = User(
        id=str(uuid.uuid4()),
        username=data.username.strip(),
        email=email,
        email_hash=email_hash,
        password_hash=hash_password(data.password),
        role=UserRole(conn.intended_role or payload.get("role") or UserRole.RESEARCHER.value),
        display_name=data.display_name.strip() or data.username.strip(),
    )
    db.add(user)
    user.recovery_codes_hashed = None
    await replace_recovery_codes(
        db,
        user_id=user.id,
        codes=recovery_codes,
        request=request,
        created_by_user_id="connection-string",
    )
    conn.is_redeemed = True
    conn.redeemed_by_user_id = user.id
    conn.redeemed_username = user.username
    conn.redeemed_at = datetime.now(UTC)
    await db.commit()
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="pooled_compute_connection_strings",
            source_system="connection_strings",
            source_id=f"redeem:{conn.id}",
            agent_id="connection-string-service",
            summary="Connection string redeemed into a team user.",
            evidence={
                "passed": True,
                "connection_id": conn.id,
                "token_type": token_type,
                "user_id": user.id,
                "role": user.role.value,
            },
        )
    except Exception:
        pass

    token = await issue_auth_session_token(
        db,
        user,
        request,
        auth_method="connection_string",
    )
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
        "recovery_codes": recovery_codes,
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
    revoked = 0
    for conn in result.scalars().all():
        conn.is_active = False
        revoked += 1
    await db.commit()
    try:
        from app.core.improvement_governance import improvement_governance

        await improvement_governance.record_feature_evidence(
            feature="pooled_compute_connection_strings",
            source_system="connection_strings",
            source_id=f"rotate_network_token:{datetime.now(UTC).isoformat()}",
            agent_id="connection-string-service",
            summary="Network access token rotated and active connection strings revoked.",
            evidence={
                "passed": True,
                "revoked_connection_strings": revoked,
            },
            metrics_after={"revoked_connection_strings": revoked},
        )
    except Exception:
        pass

    # Broadcast to connected relays so they know the token changed
    try:
        from app.core.compute_registry import compute_registry

        for node in list(compute_registry._nodes.values()):
            if node.websocket and node.source == "relay":
                try:
                    await node.websocket.send_json(
                        {
                            "type": "token_rotated",
                            "message": (
                                "Network access token has been rotated. "
                                "Reconnect with a new connection string."
                            ),
                        }
                    )
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
    conn, reason = await _get_connection_string_status(db, connection_string)
    if reason != "ok":
        return None
    return conn


async def _find_connection_string_record(
    db: AsyncSession,
    connection_string: str,
) -> ConnectionString | None:
    conn_hash = hash_connection_string(connection_string)
    result = await db.execute(
        select(ConnectionString).where(ConnectionString.connection_string_hash == conn_hash)
    )
    conn = result.scalar_one_or_none()
    if conn:
        return conn

    # Legacy fallback for rows created before hashing was introduced.
    result = await db.execute(
        select(ConnectionString).where(ConnectionString.connection_string == connection_string)
    )
    conn = result.scalar_one_or_none()
    if conn and not conn.connection_string_hash:
        conn.connection_string_hash = conn_hash
        conn.connection_string = preview_connection_string(connection_string)
    return conn


def _connection_expired(conn: ConnectionString) -> bool:
    if not conn or not conn.is_active or conn.is_redeemed:
        return True
    expires_at = conn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < datetime.now(UTC)


def _is_validation_rate_limited(client_id: str) -> bool:
    return _validation_limiter.is_limited(
        client_id,
        limit=VALIDATION_RATE_LIMIT,
        window_seconds=VALIDATION_RATE_WINDOW_S,
    )


def _is_redeem_rate_limited(client_id: str) -> bool:
    return _redeem_limiter.is_limited(
        client_id,
        limit=REDEEM_RATE_LIMIT,
        window_seconds=REDEEM_RATE_WINDOW_S,
    )


async def _get_connection_string_status(
    db: AsyncSession,
    connection_string: str,
) -> tuple[ConnectionString | None, str]:
    conn = await _find_connection_string_record(db, connection_string)
    if not conn:
        return None, "missing"
    if not conn.is_active:
        return None, "revoked"
    if conn.is_redeemed:
        return None, "redeemed"
    expires_at = conn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return None, "expired"
    return conn, "ok"


def _connection_error_message(reason: str) -> str:
    return {
        "missing": "Connection string was not issued by this server",
        "revoked": "Connection string has been revoked",
        "redeemed": "Connection string has already been redeemed",
        "expired": "Connection string has expired",
    }.get(reason, "Connection string is not valid")
