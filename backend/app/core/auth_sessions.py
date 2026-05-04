"""Server-backed auth session lifecycle helpers."""

from __future__ import annotations

import logging
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


async def revoke_user_auth_sessions(db: AsyncSession, user_id: str) -> int:
    """Revoke every active auth session for a user."""
    now = datetime.now(UTC)
    result = await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return int(result.rowcount or 0)
