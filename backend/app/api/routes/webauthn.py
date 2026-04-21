"""WebAuthn / Passkey routes for passwordless authentication.

Implements FIDO2/WebAuthn registration and authentication flows
using the webauthn package. Supports device attestation for
hardware authenticator verification.
"""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_token
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
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
        base64url_to_bytes,
        bytes_to_base64url,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialCreationOptions,
        PublicKeyCredentialRequestOptions,
        UserVerificationRequirement,
        ResidentKeyRequirement,
        AuthenticatorAttachment,
        AttestationConveyancePreference,
    )
    _WEBAUTHN_AVAILABLE = True
except ImportError:
    _WEBAUTHN_AVAILABLE = False
    logger.warning(
        "webauthn package not installed — passkey auth unavailable. "
        "Install with: pip install webauthn"
    )

RP_ID = "localhost"  # Set to actual domain in production
RP_NAME = "Istara"
ORIGIN = "http://localhost:3000"  # Set to actual origin in production

# ---------------------------------------------------------------------------
# Challenge storage — in-memory with TTL for stateless HTTP
# ---------------------------------------------------------------------------

_challenges: dict[str, dict] = {}  # user_id -> {challenge, expires_at}
_CHALLENGE_TTL = 120  # seconds


def _store_challenge(user_id: str, challenge: bytes) -> None:
    """Store a challenge for a user with a TTL."""
    _challenges[user_id] = {
        "challenge": challenge,
        "expires_at": time.time() + _CHALLENGE_TTL,
    }


def _get_and_clear_challenge(user_id: str) -> bytes | None:
    """Retrieve and remove a challenge. Returns None if expired/missing."""
    entry = _challenges.pop(user_id, None)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        return None
    return entry["challenge"]


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/webauthn/register/start")
async def webauthn_register_start(
    body: PasskeyRegistrationStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start WebAuthn registration — returns challenge options for the browser."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")

    # Check if user exists
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for existing credentials
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked == False,
        )
    )
    existing_credentials = result.scalars().all()
    exclude_credentials = [
        {"id": c.credential_id, "type": "public-key"}
        for c in existing_credentials
    ]

    try:
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user.id,
            user_name=user.username,
            user_display_name=user.display_name or user.username,
            exclude_credentials=exclude_credentials if exclude_credentials else None,
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
            attestation=AttestationConveyancePreference.NONE,
        )

        # Store challenge for verification in finish step
        _store_challenge(user.id, options.challenge)

        return {
            "publicKey": {
                "rp": {"id": RP_ID, "name": RP_NAME},
                "user": {
                    "id": bytes_to_base64url(user.id.encode()),
                    "name": user.username,
                    "displayName": user.display_name or user.username,
                },
                "challenge": bytes_to_base64url(options.challenge),
                "pubKeyCredParams": options.pub_key_cred_params,
                "authenticatorSelection": {
                    "authenticatorAttachment": "platform",
                    "residentKey": "preferred",
                    "userVerification": "preferred",
                },
                "attestation": "none",
                "excludeCredentials": exclude_credentials,
            }
        }
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

    # Retrieve the stored challenge
    challenge = _get_and_clear_challenge(body.user_id)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Registration expired or challenge not found. Please start again.")

    try:
        # Verify the registration response cryptographically
        verification = verify_registration_response(
            credential_id=base64url_to_bytes(body.raw_id) if body.raw_id else base64url_to_bytes(body.id),
            client_data_json=base64url_to_bytes(body.client_data_json),
            attestation_object=base64url_to_bytes(body.attestation_object),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            expected_challenge=challenge,
        )

        # Store the verified credential
        credential = WebAuthnCredential(
            id=str(uuid.uuid4()),
            user_id=body.user_id,
            credential_id=body.id,
            credential_public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            attestation_object=body.attestation_object,
            client_data_json=body.client_data_json,
            label=body.authenticator_attachment or "Passkey",
            authenticator_type=body.authenticator_attachment,
            transports=",".join(body.transports) if body.transports else "",
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
    db: AsyncSession = Depends(get_db),
):
    """Start WebAuthn authentication — returns challenge options."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.revoked == False,
        )
    )
    credentials = result.scalars().all()
    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered for this user")

    allow_credentials = [
        {
            "id": c.credential_id,
            "type": "public-key",
            "transports": c.transports.split(",") if c.transports else [],
        }
        for c in credentials
    ]

    try:
        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge for verification in finish step
        _store_challenge(user.id, options.challenge)

        return {
            "publicKey": {
                "challenge": bytes_to_base64url(options.challenge),
                "rpId": RP_ID,
                "allowCredentials": allow_credentials,
                "userVerification": "preferred",
            }
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

    # Retrieve the stored challenge
    challenge = _get_and_clear_challenge(body.user_id)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Authentication expired or challenge not found. Please start again.")

    try:
        # Look up the credential to get the stored public key
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.credential_id == body.id,
                WebAuthnCredential.revoked == False,
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise HTTPException(status_code=401, detail="Credential not found")

        # Verify the authentication response cryptographically
        verify_authentication_response(
            credential_id=base64url_to_bytes(body.raw_id) if body.raw_id else base64url_to_bytes(body.id),
            client_data_json=base64url_to_bytes(body.client_data_json),
            authenticator_data=base64url_to_bytes(body.authenticator_data),
            signature=base64url_to_bytes(body.signature),
            credential_public_key=credential.credential_public_key,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            expected_challenge=challenge,
            sign_count=credential.sign_count,
        )

        # Update sign count and last_used timestamp
        from datetime import datetime, timezone
        credential.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        # Look up the user
        result = await db.execute(select(User).where(User.id == credential.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Create token with MFA verified (WebAuthn counts as MFA)
        token = create_token(
            user.id, user.username,
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
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.core.auth import verify_token
    token_data = verify_token(auth_header[7:])
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = token_data.get("sub")
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user_id,
            WebAuthnCredential.revoked == False,
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
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.core.auth import verify_token
    token_data = verify_token(auth_header[7:])
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.revoked == False,
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    from datetime import datetime, timezone
    credential.revoked = True
    credential.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Passkey revoked"}
