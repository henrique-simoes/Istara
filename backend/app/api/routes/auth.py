"""Authentication API routes for team mode.

Supports:
- Password-based login with Argon2id hashing (NIST SP 800-63B Rev.4)
- Breach password checking via Have I Been Pwned k-anonymity API
- TOTP (RFC 6238) two-factor authentication
- Cryptographically secure recovery codes
- Cookie-based auth (HttpOnly, Secure, SameSite=Strict)
- WebAuthn/Passkey integration (via webauthn.py routes)
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    create_token,
    generate_recovery_codes,
    generate_totp_provisioning_uri,
    generate_totp_secret,
    hash_password,
    is_password_breached,
    needs_rehash,
    verify_password,
    verify_totp_with_counter,
)
from app.core.auth_audit import record_auth_event
from app.core.auth_cookies import clear_auth_cookies, get_auth_cookie_token, set_auth_cookie
from app.core.auth_origins import security_configuration_warnings
from app.core.auth_sessions import (
    current_auth_session_id,
    is_session_bound,
    issue_auth_session_token,
    list_active_auth_sessions,
    revoke_auth_session_by_id,
    revoke_auth_session_for_payload,
    revoke_other_auth_sessions,
    revoke_user_auth_sessions,
    validate_auth_session,
)
from app.core.client_identity import BoundedWindowRateLimiter, get_client_ip
from app.core.field_encryption import hash_field
from app.core.recovery_codes import (
    consume_recovery_code,
    recovery_code_status,
    replace_recovery_codes,
)
from app.core.security_middleware import browser_origin_denial, require_admin_from_request
from app.models.database import async_session, get_db
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory login rate limiter
# ---------------------------------------------------------------------------
_login_limiter = BoundedWindowRateLimiter()
_mfa_limiter = BoundedWindowRateLimiter()
_registration_lock = asyncio.Lock()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 60  # seconds
MAX_MFA_ATTEMPTS = 6
MFA_WINDOW = 300
TOTP_SETUP_TTL_MINUTES = 10


async def _check_login_rate(request: Request):
    client_ip = get_client_ip(request, settings.trusted_proxy_hosts)
    if _login_limiter.is_limited(
        client_ip,
        limit=MAX_LOGIN_ATTEMPTS,
        window_seconds=LOGIN_WINDOW,
    ):
        raise HTTPException(
            status_code=429, detail="Too many login attempts. Try again in 60 seconds."
        )


def _check_mfa_rate(request: Request, user_id: str) -> None:
    client_ip = get_client_ip(request, settings.trusted_proxy_hosts)
    if _mfa_limiter.is_limited(
        f"{user_id}:{client_ip}",
        limit=MAX_MFA_ATTEMPTS,
        window_seconds=MFA_WINDOW,
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many verification attempts. Try again shortly.",
        )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None  # TOTP code for 2FA
    recovery_code: str | None = None  # Recovery code for account recovery


class TOTPSetupRequest(BaseModel):
    """Request to enable TOTP for a user."""

    current_password: str


class TOTPDisableRequest(BaseModel):
    """Request to disable TOTP for a user."""

    current_password: str


class TOTPVerifyRequest(BaseModel):
    """Verify a TOTP code."""

    totp_code: str


class RecoveryCodeRequest(BaseModel):
    """Generate new recovery codes."""

    current_password: str


class ProfileUpdateRequest(BaseModel):
    """Update the current user's profile and login identifier."""

    current_password: str
    username: str | None = None
    email: str | None = None
    display_name: str | None = None


class PasswordChangeRequest(BaseModel):
    """Change the current user's password."""

    current_password: str
    new_password: str


class PreferencesRequest(BaseModel):
    preferences: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_request_local(request: Request) -> bool:
    """Check if the request truly originates from localhost."""
    local_ips = ("127.0.0.1", "::1", "localhost")
    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host not in local_ips:
        return False
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        real_ip = forwarded.split(",")[0].strip()
        if real_ip not in local_ips:
            return False
    real_ip_header = request.headers.get("x-real-ip")
    if real_ip_header and real_ip_header.strip() not in local_ips:
        return False
    return True


def _set_auth_cookie(response: Response, token: str):
    """Set an HttpOnly, Secure, SameSite=Strict cookie with the auth token."""
    set_auth_cookie(response, token)


def _clear_auth_cookie(response: Response):
    """Clear the auth cookie."""
    clear_auth_cookies(response)


def _user_to_dict(user: User) -> dict:
    """Convert a User model to a dictionary for API responses."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "display_name": user.display_name or user.username,
        "preferences": json.loads(user.preferences) if user.preferences else {},
        "totp_enabled": getattr(user, "totp_enabled", False),
        "passkey_enabled": getattr(user, "passkey_enabled", False),
    }


def _token_from_request(request: Request) -> str:
    """Return a bearer or session-cookie token from the request."""
    auth_header = request.headers.get("Authorization", "")
    token_str = (
        auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    )
    if not token_str:
        token_str = get_auth_cookie_token(request)
    if not token_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    return token_str


async def _token_payload_from_request(
    request: Request,
    db: AsyncSession | None = None,
) -> dict:
    """Return a verified token payload from Authorization or the session cookie."""
    token_str = _token_from_request(request)

    from app.core.auth import verify_token

    payload = verify_token(token_str)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    if db is not None:
        if not await validate_auth_session(db, payload, request):
            raise HTTPException(
                status_code=401,
                detail="Invalid or revoked authentication session.",
            )
    elif is_session_bound(payload):
        async with async_session() as session:
            if not await validate_auth_session(session, payload, request):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or revoked authentication session.",
                )
    return payload


def _require_current_password(user: User, current_password: str) -> None:
    """Require password confirmation before changing authentication factors."""
    if not current_password:
        raise HTTPException(status_code=400, detail="Current password is required.")
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password.")


def _validate_username(username: str) -> str:
    value = username.strip()
    if not 3 <= len(value) <= 100:
        raise HTTPException(status_code=400, detail="Username must be 3-100 characters.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise HTTPException(
            status_code=400,
            detail="Username may only contain letters, numbers, dots, dashes, and underscores.",
        )
    return value


async def _validate_new_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if len(password) > 256:
        raise HTTPException(status_code=400, detail="Password must be at most 256 characters.")
    if await is_password_breached(password):
        raise HTTPException(
            status_code=400,
            detail=(
                "This password has appeared in a known data breach. "
                "Please choose a different password."
            ),
        )


def _require_trusted_auth_origin(request: Request) -> None:
    """Reject browser login/register attempts from untrusted origins."""
    denial = browser_origin_denial(request)
    if denial:
        raise HTTPException(status_code=403, detail=denial)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _role_value(role: object) -> str:
    return str(getattr(role, "value", role))


async def _admin_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(func.lower(cast(User.role, String)) == "admin")
    )
    return int(result.scalar_one() or 0)


async def _ensure_not_last_admin_demoted_or_deleted(
    db: AsyncSession,
    user: User,
    *,
    new_role: str | None = None,
) -> None:
    old_role = _role_value(user.role)
    if old_role != "admin":
        return
    if new_role == "admin":
        return
    if await _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="At least one admin account must remain.")


def _verify_totp_for_user(user: User, code: str) -> None:
    """Verify a TOTP code and reject replay of accepted counters."""
    verified, counter = verify_totp_with_counter(user.totp_secret or "", code)
    if not verified or counter is None:
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")
    last_counter = getattr(user, "totp_last_accepted_counter", None)
    if last_counter is not None and counter <= last_counter:
        raise HTTPException(status_code=401, detail="TOTP code has already been used.")
    user.totp_last_accepted_counter = counter


async def _replace_user_recovery_codes(
    db: AsyncSession,
    user: User,
    codes: list[str],
    request: Request | None,
    *,
    created_by_user_id: str = "",
) -> None:
    user.recovery_codes_hashed = None
    await replace_recovery_codes(
        db,
        user_id=user.id,
        codes=codes,
        request=request,
        created_by_user_id=created_by_user_id,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/auth/register")
async def register(req: RegisterRequest, response: Response, request: Request):
    """Register a new user (team mode only).

    NIST SP 800-63B Rev.4 requirements:
    - Minimum 8 characters, maximum 64+
    - No complexity requirements
    - Check against known breaches
    - Generate recovery codes
    """
    _require_trusted_auth_origin(request)

    if not settings.team_mode:
        raise HTTPException(
            status_code=400, detail="Registration requires team mode. Enable TEAM_MODE=true."
        )

    username = _validate_username(req.username)

    # NIST: password length check (8-64 chars)
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if len(req.password) > 256:
        raise HTTPException(status_code=400, detail="Password must be at most 256 characters.")

    # NIST: breach checking
    if await is_password_breached(req.password):
        raise HTTPException(
            status_code=400,
            detail=(
                "This password has appeared in a known data breach. "
                "Please choose a different password."
            ),
        )

    async with _registration_lock:
        async with async_session() as db:
            existing_user = await db.execute(select(User.id).limit(1))
            if existing_user.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Public registration is only available for the first admin account. "
                        "Ask an admin for an invite connection string."
                    ),
                )

            email_hash = hash_field(req.email)
            existing = await db.execute(
                select(User).where(
                    (User.username == username) | (User.email_hash == email_hash)
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=409, detail="Username or email already exists.")

            recovery_codes = generate_recovery_codes()

            user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=req.email,
                email_hash=email_hash,
                password_hash=hash_password(req.password),
                role="admin",
                display_name=req.display_name or username,
            )
            db.add(user)
            await _replace_user_recovery_codes(
                db, user, recovery_codes, request, created_by_user_id=user.id
            )
            await db.commit()

            token = await issue_auth_session_token(
                db,
                user,
                request,
                auth_method="register",
            )
            _set_auth_cookie(response, token)
            logger.info(f"User registered: {user.username} (role={user.role})")
            await record_auth_event(
                request,
                "auth.register.success",
                user_id=user.id,
                details={
                    "username": user.username,
                    "role": _role_value(user.role),
                    "first_user": True,
                },
            )

            return {
                "token": token,
                "recovery_codes": recovery_codes,  # Shown ONCE — user must save these
                "user": _user_to_dict(user),
            }


@router.post("/auth/login")
async def login(
    req: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)
):
    """Log in and receive a JWT token + HttpOnly session cookie.

    Supports:
    - Password-only login (local mode)
    - Password + TOTP (team mode with 2FA enabled)
    - Password + recovery code (account recovery)
    - Automatic password hash upgrade on login (PBKDF2 → Argon2id)
    """
    _require_trusted_auth_origin(request)
    await _check_login_rate(request)

    # Local mode — issue a local-admin token without DB lookup
    if not settings.team_mode:
        if not is_request_local(request):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This server is in Local Mode. Remote access requires a connection string "
                    "or Team Mode."
                ),
            )
        token = create_token("local", req.username or "local", "admin")
        _set_auth_cookie(response, token)
        await record_auth_event(
            request,
            "auth.local_login.success",
            user_id="local",
            details={"username": req.username or "local"},
        )
        return {
            "token": token,
            "user": {
                "id": "local",
                "username": req.username or "local",
                "email": "local@localhost",
                "role": "admin",
                "display_name": req.username or "Local User",
                "preferences": {},
                "totp_enabled": False,
                "passkey_enabled": False,
            },
        }

    # Find user by username
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        await record_auth_event(
            request,
            "auth.login.failed",
            status_code=401,
            details={"username": req.username, "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Upgrade password hash if needed (PBKDF2 → Argon2id)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(req.password)
        await db.commit()
        logger.info(f"Upgraded password hash for user {user.username} to Argon2id")

    # Handle 2FA
    mfa_verified = False
    if getattr(user, "totp_enabled", False):
        # User has TOTP enabled — must provide a valid TOTP code or recovery code
        if req.recovery_code:
            # Recovery code flow
            _check_mfa_rate(request, user.id)
            matched = await consume_recovery_code(
                db, user=user, code=req.recovery_code, request=request
            )
            if not matched:
                await record_auth_event(
                    request,
                    "auth.mfa.recovery_code.failed",
                    user_id=user.id,
                    status_code=401,
                    details={"username": user.username},
                )
                raise HTTPException(status_code=401, detail="Invalid recovery code.")
            mfa_verified = True
            logger.info(f"User {user.username} logged in with recovery code")
            await record_auth_event(
                request,
                "auth.mfa.recovery_code.used",
                user_id=user.id,
                details={"username": user.username},
            )
        elif req.totp_code:
            _check_mfa_rate(request, user.id)
            try:
                _verify_totp_for_user(user, req.totp_code)
            except HTTPException:
                await record_auth_event(
                    request,
                    "auth.mfa.totp.failed",
                    user_id=user.id,
                    status_code=401,
                    details={"username": user.username},
                )
                raise
            mfa_verified = True
            await record_auth_event(
                request,
                "auth.mfa.totp.verified",
                user_id=user.id,
                details={"username": user.username},
            )
        else:
            # No TOTP code or recovery code provided — return 401 with 2FA required flag
            await record_auth_event(
                request,
                "auth.login.mfa_required",
                user_id=user.id,
                status_code=202,
                details={"username": user.username, "methods": ["totp", "recovery_code"]},
            )
            return {
                "requires_2fa": True,
                "methods": ["totp", "recovery_code"],
            }

    token = await issue_auth_session_token(
        db,
        user,
        request,
        auth_method="password",
        mfa_verified=mfa_verified,
    )
    _set_auth_cookie(response, token)
    await record_auth_event(
        request,
        "auth.login.success",
        user_id=user.id,
        details={
            "username": user.username,
            "auth_method": "password",
            "mfa_verified": mfa_verified,
        },
    )
    return {
        "token": token,
        "user": _user_to_dict(user),
    }


@router.post("/auth/logout")
async def logout(response: Response, request: Request, db: AsyncSession = Depends(get_db)):
    """Log out and clear the session cookie."""
    try:
        token = _token_from_request(request)
        from app.core.auth import verify_token

        payload = verify_token(token)
        if payload:
            await revoke_auth_session_for_payload(db, payload)
            await record_auth_event(
                request,
                "auth.logout",
                user_id=str(payload.get("sub") or ""),
                details={"session_bound": is_session_bound(payload)},
            )
    except HTTPException:
        pass
    _clear_auth_cookie(response)
    return {"status": "ok"}


def _require_bound_session_payload(payload: dict) -> tuple[str, str]:
    if not is_session_bound(payload):
        raise HTTPException(
            status_code=400,
            detail="Active session management requires a server-backed session.",
        )
    user_id = str(payload.get("sub") or "")
    session_id = current_auth_session_id(payload)
    if not user_id or not session_id:
        raise HTTPException(status_code=401, detail="Invalid authentication session.")
    return user_id, session_id


@router.get("/auth/sessions")
async def list_auth_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    """List active server-backed auth sessions for the current user."""
    payload = await _token_payload_from_request(request, db)
    if not is_session_bound(payload):
        return []
    user_id, session_id = _require_bound_session_payload(payload)
    return await list_active_auth_sessions(db, user_id, current_session_id=session_id)


@router.post("/auth/sessions/revoke-others")
async def revoke_other_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    """Revoke every active auth session except the current one."""
    payload = await _token_payload_from_request(request, db)
    user_id, session_id = _require_bound_session_payload(payload)
    revoked_count = await revoke_other_auth_sessions(db, user_id, session_id)
    return {"status": "ok", "revoked_count": revoked_count}


@router.delete("/auth/sessions/{session_id}")
async def revoke_auth_session(
    session_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Revoke one auth session owned by the current user."""
    payload = await _token_payload_from_request(request, db)
    user_id, current_session_id = _require_bound_session_payload(payload)
    revoked = await revoke_auth_session_by_id(db, user_id, session_id)
    revoked_current = revoked and session_id == current_session_id
    if revoked_current:
        _clear_auth_cookie(response)
    return {"status": "ok", "revoked": revoked, "revoked_current": revoked_current}


# ---------------------------------------------------------------------------
# TOTP 2FA Management
# ---------------------------------------------------------------------------


@router.post("/auth/totp/setup")
async def totp_setup(
    req: TOTPSetupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and provisioning URI for QR code display.

    Returns the secret (shown once) and a URI for QR code generation.
    The user must verify a code to enable TOTP.
    """
    payload = await _token_payload_from_request(request, db)
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _require_current_password(user, req.current_password)

    secret = generate_totp_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="TOTP support is not available.")
    uri = generate_totp_provisioning_uri(secret, user.username)
    if not uri:
        raise HTTPException(status_code=503, detail="TOTP support is not available.")

    # Store secret but don't enable yet (requires verification)
    user.totp_secret = secret
    user.totp_pending_expires_at = datetime.now(UTC) + timedelta(minutes=TOTP_SETUP_TTL_MINUTES)
    user.totp_last_accepted_counter = None
    await db.commit()
    await record_auth_event(
        request,
        "auth.totp.setup_started",
        user_id=user.id,
        details={"username": user.username, "expires_at": user.totp_pending_expires_at},
    )

    return {
        "secret": secret,
        "provisioning_uri": uri,
        "expires_at": user.totp_pending_expires_at.isoformat(),
        "message": (
            "Scan the QR code with your authenticator app, then verify with /auth/totp/verify"
        ),
    }


@router.post("/auth/totp/verify")
async def totp_verify(req: TOTPVerifyRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify a TOTP code to enable 2FA."""
    payload = await _token_payload_from_request(request, db)
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call /auth/totp/setup first.")
    pending_expires_at = _as_utc(getattr(user, "totp_pending_expires_at", None))
    if not user.totp_enabled and pending_expires_at and pending_expires_at <= datetime.now(UTC):
        user.totp_secret = None
        user.totp_pending_expires_at = None
        await db.commit()
        raise HTTPException(status_code=400, detail="TOTP setup expired. Start setup again.")

    _check_mfa_rate(request, user.id)
    _verify_totp_for_user(user, req.totp_code)

    user.totp_enabled = True
    user.totp_pending_expires_at = None
    await db.commit()
    await record_auth_event(
        request,
        "auth.totp.enabled",
        user_id=user.id,
        details={"username": user.username},
    )

    return {
        "success": True,
        "message": "TOTP 2FA enabled. Save your recovery codes from /auth/recovery-codes.",
    }


@router.post("/auth/totp/disable")
async def totp_disable(
    req: TOTPDisableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Disable TOTP 2FA. Requires password verification."""
    payload = await _token_payload_from_request(request, db)
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _require_current_password(user, req.current_password)

    user.totp_enabled = False
    user.totp_secret = None
    user.totp_last_accepted_counter = None
    user.totp_pending_expires_at = None
    await db.commit()
    await record_auth_event(
        request,
        "auth.totp.disabled",
        user_id=user.id,
        details={"username": user.username},
    )

    return {"success": True, "message": "TOTP 2FA disabled."}


# ---------------------------------------------------------------------------
# Recovery Codes
# ---------------------------------------------------------------------------


@router.post("/auth/recovery-codes/generate")
async def generate_recovery_codes_endpoint(
    req: RecoveryCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate new recovery codes. Replaces all existing codes.

    Requires the user's current password for verification.
    """
    payload = await _token_payload_from_request(request, db)
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _require_current_password(user, req.current_password)

    codes = generate_recovery_codes()
    await _replace_user_recovery_codes(
        db,
        user,
        codes,
        request,
        created_by_user_id=user.id,
    )
    await db.commit()
    await record_auth_event(
        request,
        "auth.recovery_codes.generated",
        user_id=user.id,
        details={"username": user.username, "count": len(codes)},
    )

    return {
        "recovery_codes": codes,
        "message": "Save these codes — they will only be shown once.",
    }


@router.get("/auth/recovery-codes/status")
async def recovery_codes_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Check how many unused recovery codes remain."""
    payload = await _token_payload_from_request(request, db)
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    status = await recovery_code_status(db, user)
    await db.commit()
    return status


# ---------------------------------------------------------------------------
# User Info
# ---------------------------------------------------------------------------


@router.get("/auth/me")
async def get_me(request: Request):
    """Get current user info from JWT token. Works in both local and team mode."""
    from app.core.auth import verify_token

    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        token = get_auth_cookie_token(request)

    if not token:
        if not settings.team_mode:
            return {
                "id": "local",
                "username": "local",
                "email": "local@localhost",
                "role": "admin",
                "display_name": "Local User",
                "preferences": {},
                "team_mode": False,
                "totp_enabled": False,
                "passkey_enabled": False,
            }
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    async with async_session() as db:
        if not await validate_auth_session(db, payload, request):
            raise HTTPException(
                status_code=401,
                detail="Invalid or revoked authentication session",
            )
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email or "",
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "display_name": user.display_name or user.username,
                "preferences": json.loads(user.preferences) if user.preferences else {},
                "team_mode": settings.team_mode,
                "totp_enabled": getattr(user, "totp_enabled", False),
                "passkey_enabled": getattr(user, "passkey_enabled", False),
            }
        if is_session_bound(payload):
            raise HTTPException(
                status_code=401,
                detail="Authenticated user no longer exists",
            )

    if not settings.team_mode:
        return {
            "id": payload.get("sub", "local"),
            "username": payload.get("username", "local"),
            "email": "local@localhost",
            "role": "admin",
            "display_name": payload.get("username", "Local User"),
            "preferences": {},
            "team_mode": False,
            "totp_enabled": False,
            "passkey_enabled": False,
        }

    return {
        "id": payload.get("sub", ""),
        "username": payload.get("username", ""),
        "email": "",
        "role": payload.get("role", "viewer"),
        "display_name": payload.get("username", ""),
        "preferences": {},
        "team_mode": True,
        "totp_enabled": False,
        "passkey_enabled": False,
    }


@router.patch("/auth/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's username, email, or display name.

    Username and email changes require a fresh password confirmation and are
    audited. This mirrors Better Auth's guidance that account-management
    operations belong beside authentication, not in a generic user settings
    route.
    """
    payload = await _token_payload_from_request(request, db)
    user = await db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == "local":
        raise HTTPException(status_code=400, detail="Local mode profile cannot be changed.")

    _require_current_password(user, req.current_password)

    changed: list[str] = []
    if req.username is not None:
        username = _validate_username(req.username)
        if username != user.username:
            existing = await db.execute(select(User.id).where(User.username == username))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Username already exists.")
            user.username = username
            changed.append("username")

    if req.email is not None:
        email = req.email.strip()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="A valid email address is required.")
        email_hash = hash_field(email)
        if email_hash != user.email_hash:
            existing = await db.execute(
                select(User.id).where(User.email_hash == email_hash, User.id != user.id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Email already exists.")
            user.email = email
            user.email_hash = email_hash
            changed.append("email")

    if req.display_name is not None:
        display_name = req.display_name.strip()[:200]
        if display_name != (user.display_name or ""):
            user.display_name = display_name or user.username
            changed.append("display_name")

    if changed:
        await db.commit()
        await record_auth_event(
            request,
            "auth.profile.updated",
            user_id=user.id,
            details={"changed": changed},
        )
    return {"status": "ok", "user": _user_to_dict(user), "changed": changed}


@router.post("/auth/password/change")
async def change_password(
    req: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password and revoke other sessions."""
    payload = await _token_payload_from_request(request, db)
    user = await db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == "local":
        raise HTTPException(status_code=400, detail="Local mode password cannot be changed.")

    _require_current_password(user, req.current_password)
    await _validate_new_password(req.new_password)
    if verify_password(req.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different.")

    user.password_hash = hash_password(req.new_password)
    revoked_count = 0
    if is_session_bound(payload):
        try:
            _user_id, session_id = _require_bound_session_payload(payload)
            revoked_count = await revoke_other_auth_sessions(db, user.id, session_id)
        except HTTPException:
            revoked_count = await revoke_user_auth_sessions(db, user.id)
    else:
        revoked_count = await revoke_user_auth_sessions(db, user.id)
    await db.commit()
    await record_auth_event(
        request,
        "auth.password.changed",
        user_id=user.id,
        details={"revoked_sessions": revoked_count},
    )
    return {"status": "ok", "revoked_sessions": revoked_count}


@router.put("/auth/preferences")
async def update_preferences(
    req: PreferencesRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Update user preferences (theme, UI density, etc.)."""
    try:
        payload = await _token_payload_from_request(request, db)
    except HTTPException:
        if not settings.team_mode:
            return {"status": "ok", "preferences": req.preferences}
        raise

    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if user:
        user.preferences = json.dumps(req.preferences)
        await db.commit()
    return {"status": "ok", "preferences": req.preferences}


@router.get("/auth/team-status")
async def team_status(request: Request):
    """Check if team mode is enabled and get basic info."""
    has_users = False
    if settings.team_mode:
        async with async_session() as db:
            result = await db.execute(select(User).limit(1))
            has_users = result.scalar_one_or_none() is not None

    insecure = not settings.team_mode and not is_request_local(request)

    return {
        "team_mode": settings.team_mode,
        "registration_enabled": settings.team_mode and not has_users,
        "has_users": has_users,
        "insecure": insecure,
        "security_warnings": security_configuration_warnings(settings),
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
            "totp_enabled": getattr(u, "totp_enabled", False),
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
    username = _validate_username(body.username)

    # NIST: password length check
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if len(body.password) > 256:
        raise HTTPException(status_code=400, detail="Password must be at most 256 characters.")

    # NIST: breach checking
    if await is_password_breached(body.password):
        raise HTTPException(
            status_code=400,
            detail="This password has appeared in a known data breach.",
        )

    email_hash = hash_field(body.email)
    existing = await db.execute(
        select(User).where((User.username == username) | (User.email_hash == email_hash))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists")

    recovery_codes = generate_recovery_codes()
    actor = getattr(request.state, "user", {}) or {}

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=body.email,
        email_hash=email_hash,
        password_hash=hash_password(body.password),
        role="researcher",
        display_name=body.display_name or username,
    )
    db.add(user)
    await _replace_user_recovery_codes(
        db,
        user,
        recovery_codes,
        request,
        created_by_user_id=str(actor.get("id") or ""),
    )
    await db.commit()
    logger.info("Admin created user: %s", user.username)
    await record_auth_event(
        request,
        "auth.admin.user_created",
        user_id=str(actor.get("id") or ""),
        details={
            "created_user_id": user.id,
            "created_username": user.username,
            "role": "researcher",
        },
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": "researcher",
        "recovery_codes": recovery_codes,  # Admin must share these with the user
    }


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
    await _ensure_not_last_admin_demoted_or_deleted(db, user)
    await revoke_user_auth_sessions(db, user_id)
    actor = getattr(request.state, "user", {}) or {}
    deleted_username = user.username
    await db.delete(user)
    await db.commit()
    logger.info("Admin deleted user: %s (id=%s)", deleted_username, user_id)
    await record_auth_event(
        request,
        "auth.admin.user_deleted",
        user_id=str(actor.get("id") or ""),
        details={"deleted_user_id": user_id, "deleted_username": deleted_username},
    )
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
    await _ensure_not_last_admin_demoted_or_deleted(db, user, new_role=new_role)
    actor = getattr(request.state, "user", {}) or {}
    old_role = _role_value(user.role)
    user.role = new_role
    revoked_count = await revoke_user_auth_sessions(db, user_id)
    await db.commit()
    logger.info("Admin changed role for %s to %s", user.username, new_role)
    await record_auth_event(
        request,
        "auth.admin.role_changed",
        user_id=str(actor.get("id") or ""),
        details={
            "target_user_id": user.id,
            "target_username": user.username,
            "old_role": old_role,
            "new_role": new_role,
            "revoked_sessions": revoked_count,
        },
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": new_role,
        "revoked_sessions": revoked_count,
    }
