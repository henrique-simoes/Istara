"""WebAuthn / Passkey routes for passwordless authentication.

Implements FIDO2/WebAuthn registration and authentication flows
using the webauthn package. Supports device attestation for
hardware authenticator verification.
"""

import json
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_token, verify_token
from app.core.client_identity import BoundedWindowRateLimiter, get_client_ip
from app.models.database import get_db
from app.models.user import User
from app.models.webauthn_credential import WebAuthnCredential

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WebAuthn configuration
# ---------------------------------------------------------------------------

try:
    from webauthn import (
        generate_authentication_options,
        generate_registration_options,
        options_to_json,
        verify_authentication_response,
        verify_registration_response,
    )
    from webauthn.helpers import (
        base64url_to_bytes,
        bytes_to_base64url,
    )
    from webauthn.helpers.structs import (
        AttestationConveyancePreference,
        AuthenticatorAttachment,
        AuthenticatorSelectionCriteria,
        AuthenticatorTransport,
        PublicKeyCredentialDescriptor,
        ResidentKeyRequirement,
        UserVerificationRequirement,
    )

    _WEBAUTHN_AVAILABLE = True
except ImportError:
    _WEBAUTHN_AVAILABLE = False
    logger.warning(
        "webauthn package not installed — passkey auth unavailable. "
        "Install with: pip install webauthn"
    )

# ---------------------------------------------------------------------------
# Challenge storage — in-memory with TTL for stateless HTTP
# ---------------------------------------------------------------------------

_challenges: dict[str, dict] = {}  # purpose:user_id -> {challenge, expires_at}
_CHALLENGE_TTL = 120  # seconds


def _challenge_key(purpose: str, user_id: str) -> str:
    return f"{purpose}:{user_id}"


def _store_challenge(purpose: str, user_id: str, challenge: bytes) -> None:
    """Store a challenge for a user with a TTL."""
    _challenges[_challenge_key(purpose, user_id)] = {
        "challenge": challenge,
        "expires_at": time.time() + _CHALLENGE_TTL,
    }


def _get_and_clear_challenge(purpose: str, user_id: str) -> bytes | None:
    """Retrieve and remove a challenge. Returns None if expired/missing."""
    entry = _challenges.pop(_challenge_key(purpose, user_id), None)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        return None
    return entry["challenge"]


_webauthn_limiter = BoundedWindowRateLimiter()
_WEBAUTHN_RATE_LIMIT = 20
_WEBAUTHN_RATE_WINDOW = 60


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class PasskeyRegistrationStartRequest(BaseModel):
    username: str
    display_name: str = ""


class PasskeyRegistrationFinishRequest(BaseModel):
    user_id: str  # Needed to retrieve the stored challenge
    id: str  # credential id from browser
    raw_id: str  # base64url(raw credential id)
    response_type: str  # "public-key"
    authenticator_attachment: str | None = None  # "platform" or "cross-platform"
    client_data_json: str  # base64url
    attestation_object: str  # base64url
    transports: list[str] = []


class PasskeyAuthenticationStartRequest(BaseModel):
    username: str


class PasskeyAuthenticationFinishRequest(BaseModel):
    user_id: str  # Needed to retrieve the stored challenge
    id: str  # credential id from browser
    raw_id: str  # base64url(raw credential id)
    response_type: str  # "public-key"
    authenticator_data: str  # base64url
    client_data_json: str  # base64url
    signature: str  # base64url
    user_handle: str | None = None


class PasskeyCredentialInfo(BaseModel):
    id: str
    label: str
    created_at: str
    last_used_at: str | None
    authenticator_type: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token_from_request(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        token = request.cookies.get("istara_session", "")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data


def _rp_id() -> str:
    """Return the configured WebAuthn relying-party ID."""
    return settings.webauthn_rp_id.strip() or "localhost"


def _rp_name() -> str:
    """Return the configured WebAuthn relying-party name."""
    return settings.webauthn_rp_name.strip() or "Istara"


def _expected_origins() -> list[str]:
    """Return trusted origins for WebAuthn ceremony verification."""
    raw = settings.webauthn_origins.strip() or settings.cors_origins
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    return origins


def _check_webauthn_rate(request: Request, scope: str) -> None:
    """Apply a small per-client limiter to expensive passkey ceremony endpoints."""
    client_ip = get_client_ip(request, settings.trusted_proxy_hosts)
    client_key = f"{scope}:{client_ip}"
    if _webauthn_limiter.is_limited(
        client_key,
        limit=_WEBAUTHN_RATE_LIMIT,
        window_seconds=_WEBAUTHN_RATE_WINDOW,
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many passkey attempts. Try again in 60 seconds.",
        )


def _parse_transports(raw: str) -> list:
    """Parse stored WebAuthn transports from JSON or legacy comma-separated values."""
    if not raw:
        return []
    try:
        values = json.loads(raw)
        if isinstance(values, list):
            return [AuthenticatorTransport(item) for item in values if item]
    except Exception:
        pass
    transports = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            transports.append(AuthenticatorTransport(item))
        except ValueError:
            continue
    return transports


def _credential_descriptor(credential: WebAuthnCredential):
    return PublicKeyCredentialDescriptor(
        id=base64url_to_bytes(credential.credential_id),
        transports=_parse_transports(credential.transports) or None,
    )


def _registration_credential_from_body(body: PasskeyRegistrationFinishRequest) -> dict:
    return {
        "id": body.id,
        "rawId": body.raw_id,
        "type": body.response_type,
        "authenticatorAttachment": body.authenticator_attachment,
        "response": {
            "clientDataJSON": body.client_data_json,
            "attestationObject": body.attestation_object,
            "transports": body.transports,
        },
    }


def _authentication_credential_from_body(body: PasskeyAuthenticationFinishRequest) -> dict:
    response = {
        "authenticatorData": body.authenticator_data,
        "clientDataJSON": body.client_data_json,
        "signature": body.signature,
    }
    if body.user_handle:
        response["userHandle"] = body.user_handle
    return {
        "id": body.id,
        "rawId": body.raw_id,
        "type": body.response_type,
        "response": response,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/webauthn/register/start")
async def webauthn_register_start(
    body: PasskeyRegistrationStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Start WebAuthn registration — returns challenge options for the browser."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")
    _check_webauthn_rate(request, "register-start")
    token_data = _token_from_request(request)

    # Check if user exists
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if token_data.get("sub") != user.id:
        raise HTTPException(status_code=403, detail="Cannot register a passkey for another user")

    # Check for existing credentials
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked.is_(False),
        )
    )
    existing_credentials = result.scalars().all()
    exclude_credentials = [_credential_descriptor(c) for c in existing_credentials]

    try:
        options = generate_registration_options(
            rp_id=_rp_id(),
            rp_name=_rp_name(),
            user_id=user.id.encode("utf-8"),
            user_name=user.username,
            user_display_name=user.display_name or user.username,
            exclude_credentials=exclude_credentials if exclude_credentials else None,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            attestation=AttestationConveyancePreference.NONE,
        )

        # Store challenge for verification in finish step
        _store_challenge("registration", user.id, options.challenge)

        return {"publicKey": json.loads(options_to_json(options))}
    except Exception as e:
        logger.error(f"WebAuthn registration start failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start registration")


@router.post("/webauthn/register/finish")
async def webauthn_register_finish(
    body: PasskeyRegistrationFinishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Finish WebAuthn registration — verify cryptographic attestation and store credential."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")
    _check_webauthn_rate(request, "register-finish")
    token_data = _token_from_request(request)
    if token_data.get("sub") != body.user_id:
        raise HTTPException(status_code=403, detail="Cannot register a passkey for another user")

    # Retrieve the stored challenge
    challenge = _get_and_clear_challenge("registration", body.user_id)
    if challenge is None:
        raise HTTPException(
            status_code=400,
            detail="Registration expired or challenge not found. Please start again.",
        )

    try:
        # Verify the registration response cryptographically
        verification = verify_registration_response(
            credential=_registration_credential_from_body(body),
            expected_rp_id=_rp_id(),
            expected_origin=_expected_origins(),
            expected_challenge=challenge,
        )

        # Store the verified credential
        credential = WebAuthnCredential(
            id=str(uuid.uuid4()),
            user_id=body.user_id,
            credential_id=bytes_to_base64url(verification.credential_id),
            credential_public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=verification.aaguid,
            attestation_object=body.attestation_object,
            client_data_json=body.client_data_json,
            label=body.authenticator_attachment or "Passkey",
            authenticator_type=body.authenticator_attachment,
            transports=json.dumps(body.transports or []),
        )
        db.add(credential)
        await db.commit()

        # Mark user as having passkeys
        result = await db.execute(select(User).where(User.id == body.user_id))
        user = result.scalar_one_or_none()
        if user:
            user.passkey_enabled = True
            await db.commit()

        return {"success": True, "message": "Passkey registered and verified"}
    except Exception as e:
        logger.error(f"WebAuthn registration verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Credential verification failed: {str(e)}")


@router.post("/webauthn/authenticate/start")
async def webauthn_authenticate_start(
    body: PasskeyAuthenticationStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Start WebAuthn authentication — returns challenge options."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")
    _check_webauthn_rate(request, "authenticate-start")

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked.is_(False),
        )
    )
    credentials = result.scalars().all()
    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered for this user")

    allow_credentials = [_credential_descriptor(c) for c in credentials]

    try:
        options = generate_authentication_options(
            rp_id=_rp_id(),
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge for verification in finish step
        _store_challenge("authentication", user.id, options.challenge)

        return {
            "user_id": user.id,
            "publicKey": json.loads(options_to_json(options)),
        }
    except Exception as e:
        logger.error(f"WebAuthn authentication start failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start authentication")


@router.post("/webauthn/authenticate/finish")
async def webauthn_authenticate_finish(
    body: PasskeyAuthenticationFinishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Finish WebAuthn authentication — verify cryptographic signature and return token."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")
    _check_webauthn_rate(request, "authenticate-finish")

    # Retrieve the stored challenge
    challenge = _get_and_clear_challenge("authentication", body.user_id)
    if challenge is None:
        raise HTTPException(
            status_code=400,
            detail="Authentication expired or challenge not found. Please start again.",
        )

    try:
        # Look up the credential to get the stored public key
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.credential_id == body.id,
                WebAuthnCredential.revoked.is_(False),
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise HTTPException(status_code=401, detail="Credential not found")
        if credential.user_id != body.user_id:
            raise HTTPException(status_code=401, detail="Credential does not match challenge user")

        # Verify the authentication response cryptographically
        verification = verify_authentication_response(
            credential=_authentication_credential_from_body(body),
            credential_public_key=credential.credential_public_key,
            expected_rp_id=_rp_id(),
            expected_origin=_expected_origins(),
            expected_challenge=challenge,
            credential_current_sign_count=credential.sign_count,
        )

        # Update sign count and last_used timestamp
        credential.last_used_at = datetime.now(UTC)
        credential.sign_count = verification.new_sign_count
        await db.commit()

        # Look up the user
        result = await db.execute(select(User).where(User.id == credential.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Create token with MFA verified (WebAuthn counts as MFA)
        token = create_token(
            user.id,
            user.username,
            user.role.value if hasattr(user.role, "value") else user.role,
            mfa_verified=True,
        )
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
                "display_name": user.display_name,
                "totp_enabled": user.totp_enabled,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WebAuthn authentication verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication verification failed: {str(e)}")


@router.get("/webauthn/credentials")
async def list_credentials(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List the user's registered passkeys."""
    token_data = _token_from_request(request)

    user_id = token_data.get("sub")
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user_id,
            WebAuthnCredential.revoked.is_(False),
        )
    )
    credentials = result.scalars().all()

    return [
        PasskeyCredentialInfo(
            id=c.id,
            label=c.label,
            created_at=c.created_at.isoformat() if c.created_at else None,
            last_used_at=c.last_used_at.isoformat() if c.last_used_at else None,
            authenticator_type=c.authenticator_type,
        )
        for c in credentials
    ]


@router.delete("/webauthn/credentials/{credential_id}")
async def revoke_credential(
    credential_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a passkey."""
    token_data = _token_from_request(request)

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == token_data.get("sub"),
            WebAuthnCredential.revoked.is_(False),
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    credential.revoked = True
    credential.revoked_at = datetime.now(UTC)
    await db.commit()
    return {"success": True, "message": "Passkey revoked"}
