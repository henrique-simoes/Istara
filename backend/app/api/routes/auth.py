"""Authentication API routes for team mode.

Supports:
- Password-based login with Argon2id hashing (NIST SP 800-63B Rev.4)
- Breach password checking via Have I Been Pwned k-anonymity API
- TOTP (RFC 6238) two-factor authentication
- Cryptographically secure recovery codes
- Cookie-based auth (HttpOnly, Secure, SameSite=Strict)
- WebAuthn/Passkey integration (via webauthn.py routes)
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    create_token,
    generate_recovery_codes,
    generate_totp_provisioning_uri,
    generate_totp_secret,
    hash_password,
    hash_recovery_code,
    is_password_breached,
    needs_rehash,
    verify_password,
    verify_recovery_code,
    verify_totp,
)
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
from app.core.security_middleware import browser_origin_denial, require_admin_from_request
from app.models.database import async_session, get_db
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory login rate limiter
# ---------------------------------------------------------------------------
_login_limiter = BoundedWindowRateLimiter()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 60  # seconds


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
    response.set_cookie(
        key="istara_session",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.jwt_expire_minutes * 60,
        path="/api",
    )


def _clear_auth_cookie(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie(key="istara_session", path="/api")


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
        token_str = request.cookies.get("istara_session", "")
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


def _require_trusted_auth_origin(request: Request) -> None:
    """Reject browser login/register attempts from untrusted origins."""
    denial = browser_origin_denial(request)
    if denial:
        raise HTTPException(status_code=403, detail=denial)


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

    async with async_session() as db:
        email_hash = hash_field(req.email)
        existing = await db.execute(
            select(User).where((User.username == req.username) | (User.email_hash == email_hash))
        )
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="Username or email already exists.")

        count_result = await db.execute(select(User))
        is_first = len(count_result.scalars().all()) == 0

        # Generate recovery codes
        recovery_codes = generate_recovery_codes()
        recovery_codes_hashed = "\n".join(hash_recovery_code(c) for c in recovery_codes)

        user = User(
            id=str(uuid.uuid4()),
            username=req.username,
            email=req.email,
            email_hash=email_hash,
            password_hash=hash_password(req.password),
            role="admin" if is_first else "researcher",
            display_name=req.display_name or req.username,
            recovery_codes_hashed=recovery_codes_hashed,
        )
        db.add(user)
        await db.commit()

        token = await issue_auth_session_token(
            db,
            user,
            request,
            auth_method="register",
        )
        _set_auth_cookie(response, token)
        logger.info(f"User registered: {user.username} (role={user.role})")

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
            if not user.recovery_codes_hashed:
                raise HTTPException(status_code=401, detail="No recovery codes configured.")
            codes = user.recovery_codes_hashed.split("\n")
            matched = False
            for i, hashed in enumerate(codes):
                if verify_recovery_code(req.recovery_code, hashed):
                    # Remove used code
                    codes.pop(i)
                    user.recovery_codes_hashed = "\n".join(codes)
                    matched = True
                    break
            if not matched:
                raise HTTPException(status_code=401, detail="Invalid recovery code.")
            mfa_verified = True
            logger.info(f"User {user.username} logged in with recovery code")
        elif req.totp_code:
            if not verify_totp(user.totp_secret, req.totp_code):
                raise HTTPException(status_code=401, detail="Invalid TOTP code.")
            mfa_verified = True
        else:
            # No TOTP code or recovery code provided — return 401 with 2FA required flag
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
    await db.commit()

    return {
        "secret": secret,
        "provisioning_uri": uri,
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

    if not verify_totp(user.totp_secret, req.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")

    user.totp_enabled = True
    await db.commit()

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
    await db.commit()

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
    codes_hashed = "\n".join(hash_recovery_code(c) for c in codes)
    user.recovery_codes_hashed = codes_hashed
    await db.commit()

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

    codes = (user.recovery_codes_hashed or "").split("\n")
    remaining = len([c for c in codes if c.strip()])
    return {"remaining": remaining, "total": 8}


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
        token = request.cookies.get("istara_session", "")
    if not token:
        token = request.query_params.get("token", "")

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
        "registration_enabled": settings.team_mode,
        "has_users": has_users,
        "insecure": insecure,
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
        select(User).where((User.username == body.username) | (User.email_hash == email_hash))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists")

    # Generate recovery codes for the new user
    recovery_codes = generate_recovery_codes()
    recovery_codes_hashed = "\n".join(hash_recovery_code(c) for c in recovery_codes)

    user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        email_hash=email_hash,
        password_hash=hash_password(body.password),
        role="researcher",
        display_name=body.display_name or body.username,
        recovery_codes_hashed=recovery_codes_hashed,
    )
    db.add(user)
    await db.commit()
    logger.info("Admin created user: %s", user.username)
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
    await revoke_user_auth_sessions(db, user_id)
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
