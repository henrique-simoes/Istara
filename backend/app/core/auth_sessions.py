"""Server-backed auth session lifecycle helpers."""

from __future__ import annotations

import logging
import hashlib
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_token, verify_token
from app.core.client_identity import get_client_ip
from app.models.auth_session import AuthSession
from app.models.user import User

logger = logging.getLogger(__name__)

SESSION_ID_CLAIM = "sid"
SESSION_BOUND_CLAIM = "session_bound"
_LAST_SEEN_UPDATE_SECONDS = 300


def is_session_bound(payload: dict[str, Any] | None) -> bool:
    """Return whether a token is bound to a server-side auth session."""
    if not payload:
        return False
    return bool(payload.get(SESSION_BOUND_CLAIM)) or bool(payload.get(SESSION_ID_CLAIM))


def _role_value(role: object) -> str:
    return str(getattr(role, "value", role))


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _request_ip(request: Request | None) -> str:
    if request is None:
        return ""
    return get_client_ip(request, settings.trusted_proxy_hosts)[:128]


def _request_user_agent(request: Request | None) -> str:
    if request is None:
        return ""
    return request.headers.get("user-agent", "")[:512]


def _sha256_preview(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _device_label(user_agent: str) -> str:
    """Return a coarse device label without storing a full parser dependency."""
    ua = (user_agent or "").lower()
    if not ua:
        return "Unknown device"
    if "iphone" in ua:
        return "iPhone"
    if "ipad" in ua:
        return "iPad"
    if "android" in ua:
        return "Android"
    if "windows" in ua:
        return "Windows"
    if "mac os" in ua or "macintosh" in ua:
        return "Mac"
    if "linux" in ua:
        return "Linux"
    return "Browser session"


async def issue_auth_session_token(
    db: AsyncSession,
    user: User,
    request: Request | None,
    *,
    auth_method: str = "password",
    mfa_verified: bool = False,
) -> str:
    """Create a bound token and persist the matching revocable session."""
    session_id = str(uuid.uuid4())
    token = create_token(
        user.id,
        user.username,
        _role_value(user.role),
        mfa_verified=mfa_verified,
        session_id=session_id,
        session_bound=True,
    )
    payload = verify_token(token)
    if not payload:
        raise RuntimeError("Created authentication token failed verification.")

    now = datetime.now(UTC)
    session = AuthSession(
        id=session_id,
        user_id=user.id,
        token_jti=str(payload["jti"]),
        auth_method=auth_method[:40],
        mfa_verified=mfa_verified,
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        created_at=now,
        expires_at=datetime.fromtimestamp(int(payload["exp"]), UTC),
        last_seen_at=now,
    )
    db.add(session)
    await db.commit()
    return token


async def validate_auth_session(
    db: AsyncSession,
    payload: dict[str, Any],
    request: Request | None = None,
) -> bool:
    """Validate server-side state for bound tokens.

    Unbound tokens are accepted for backwards compatibility with internal tests
    and service flows that still mint direct JWTs via ``create_token``.
    """
    if not is_session_bound(payload):
        return True

    session_id = str(payload.get(SESSION_ID_CLAIM) or "")
    token_jti = str(payload.get("jti") or "")
    user_id = str(payload.get("sub") or "")
    if not session_id or not token_jti or not user_id:
        return False

    try:
        result = await db.execute(select(AuthSession).where(AuthSession.id == session_id))
        session = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if (
            not session
            or session.user_id != user_id
            or session.token_jti != token_jti
            or session.revoked_at is not None
            or (_aware(session.expires_at) or now) <= now
        ):
            return False

        last_seen = _aware(session.last_seen_at)
        if last_seen is None or time.time() - last_seen.timestamp() >= _LAST_SEEN_UPDATE_SECONDS:
            session.last_seen_at = now
            await db.commit()
        return True
    except Exception:
        logger.exception("Auth session validation failed.")
        await db.rollback()
        return False


async def current_user_context_for_payload(
    db: AsyncSession,
    payload: dict[str, Any],
) -> dict[str, str] | None:
    """Resolve current user identity for a payload.

    Bound sessions use the database as authority so role changes and deleted
    users take effect immediately. Legacy unbound tokens keep their claims.
    """
    if not is_session_bound(payload):
        return {
            "id": str(payload.get("sub", "")),
            "username": str(payload.get("username", "")),
            "role": str(payload.get("role", "researcher")),
        }

    user = await db.get(User, str(payload.get("sub") or ""))
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "role": _role_value(user.role),
    }


async def revoke_auth_session_for_payload(
    db: AsyncSession,
    payload: dict[str, Any],
) -> bool:
    """Revoke a single bound session represented by a token payload."""
    if not is_session_bound(payload):
        return False
    session_id = str(payload.get(SESSION_ID_CLAIM) or "")
    token_jti = str(payload.get("jti") or "")
    if not session_id or not token_jti:
        return False
    now = datetime.now(UTC)
    result = await db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.token_jti == token_jti,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await db.commit()
    return bool(result.rowcount)


def current_auth_session_id(payload: dict[str, Any]) -> str:
    """Return the bound auth session id carried by a token payload."""
    return str(payload.get(SESSION_ID_CLAIM) or "")


def _session_to_public_dict(session: AuthSession, current_session_id: str) -> dict[str, Any]:
    return {
        "id": session.id,
        "auth_method": session.auth_method,
        "mfa_verified": bool(session.mfa_verified),
        "ip_address": session.ip_address,
        "ip_hash": _sha256_preview(session.ip_address or ""),
        "user_agent": session.user_agent,
        "user_agent_hash": _sha256_preview(session.user_agent or ""),
        "device_label": _device_label(session.user_agent or ""),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_seen_at": session.last_seen_at.isoformat() if session.last_seen_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "current": session.id == current_session_id,
    }


async def list_active_auth_sessions(
    db: AsyncSession,
    user_id: str,
    *,
    current_session_id: str = "",
) -> list[dict[str, Any]]:
    """List non-revoked, non-expired auth sessions for a user without tokens."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .order_by(AuthSession.last_seen_at.desc(), AuthSession.created_at.desc())
    )
    sessions = [
        session for session in result.scalars().all() if (_aware(session.expires_at) or now) > now
    ]
    return [_session_to_public_dict(session, current_session_id) for session in sessions]


async def revoke_auth_session_by_id(
    db: AsyncSession,
    user_id: str,
    session_id: str,
) -> bool:
    """Revoke one active auth session owned by a user."""
    now = datetime.now(UTC)
    result = await db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await db.commit()
    return bool(result.rowcount)


async def revoke_other_auth_sessions(
    db: AsyncSession,
    user_id: str,
    current_session_id: str,
) -> int:
    """Revoke active sessions for a user except the current session."""
    now = datetime.now(UTC)
    result = await db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.id != current_session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await db.commit()
    return int(result.rowcount or 0)


async def revoke_user_auth_sessions(db: AsyncSession, user_id: str) -> int:
    """Revoke every active auth session for a user."""
    now = datetime.now(UTC)
    result = await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.commit()
    return int(result.rowcount or 0)
