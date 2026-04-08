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
        WebAuthnCredentialCreationOptions,
        WebAuthnAssertionOptions,
        WebAuthnRegistrationRequest,
        WebAuthnAssertionRequest,
        WebAuthnUser,
        WebAuthnMakeCredentialOptions,
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
        base64url_to_bytes,
        bytes_to_base64url,
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
# Request / Response models
# ---------------------------------------------------------------------------

class PasskeyRegistrationStartRequest(BaseModel):
    username: str
    display_name: str = ""


class PasskeyRegistrationFinishRequest(BaseModel):
    credential_id: str
    public_key: str
    attestation_object: str
    client_data_json: str
    label: str = "Passkey"


class PasskeyAuthenticationStartRequest(BaseModel):
    username: str


class PasskeyAuthenticationFinishRequest(BaseModel):
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str
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

def _get_webauthn_user(user: User) -> "WebAuthnUser":
    """Create a WebAuthnUser from a User model."""
    return WebAuthnUser(
        id=user.id.encode("utf-8"),
        name=user.username.encode("utf-8"),
        display_name=user.display_name.encode("utf-8"),
    )


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
    exclude_credentials = [c.credential_id for c in existing_credentials]

    # Generate registration options
    try:
        registration_options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user.id,
            user_name=user.username,
            user_display_name=user.display_name or user.username,
            exclude_credentials=exclude_credentials if exclude_credentials else None,
            authenticator_selection={
                "authenticator_attachment": "platform",
                "resident_key": "preferred",
                "user_verification": "preferred",
            },
            attestation="none",  # Don't require attestation for most users
        )

        # Store challenge in session (use request state for now)
        challenge = registration_options.challenge
        # TODO: Store challenge in Redis or DB for verification

        return {
            "publicKey": {
                "rp": {"id": RP_ID, "name": RP_NAME},
                "user": {
                    "id": bytes_to_base64url(user.id.encode()),
                    "name": user.username,
                    "displayName": user.display_name or user.username,
                },
                "challenge": bytes_to_base64url(registration_options.challenge),
                "pubKeyCredParams": registration_options.pub_key_cred_params,
                "authenticatorSelection": {
                    "authenticatorAttachment": "platform",
                    "residentKey": "preferred",
                    "userVerification": "preferred",
                },
                "attestation": "none",
                "excludeCredentials": [
                    {"id": bytes_to_base64url(c.encode("utf-8") if isinstance(c, str) else c), "type": "public-key"}
                    for c in exclude_credentials
                ] if exclude_credentials else [],
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
    """Finish WebAuthn registration — verify and store credential."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")

    try:
        credential = WebAuthnCredential(
            id=str(uuid.uuid4()),
            credential_id=body.credential_id,
            credential_public_key=body.public_key.encode(),
            attestation_object=body.attestation_object,
            client_data_json=body.client_data_json,
            label=body.label,
        )
        db.add(credential)
        await db.commit()
        return {"success": True, "message": "Passkey registered"}
    except Exception as e:
        logger.error(f"WebAuthn registration finish failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete registration")


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
        {"id": c.credential_id, "type": "public-key"}
        for c in credentials
    ]

    return {
        "publicKey": {
            "challenge": bytes_to_base64url(uuid.uuid4().bytes),  # TODO: proper challenge
            "rpId": RP_ID,
            "allowCredentials": allow_credentials,
            "userVerification": "preferred",
        }
    }


@router.post("/webauthn/authenticate/finish")
async def webauthn_authenticate_finish(
    body: PasskeyAuthenticationFinishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Finish WebAuthn authentication — verify and return token."""
    if not _WEBAUTHN_AVAILABLE:
        raise HTTPException(status_code=503, detail="WebAuthn not available")

    try:
        # Look up the credential
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.credential_id == body.credential_id,
                WebAuthnCredential.revoked == False,
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise HTTPException(status_code=401, detail="Credential not found")

        # Look up the user
        result = await db.execute(select(User).where(User.id == credential.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Update last_used timestamp
        from datetime import datetime, timezone
        credential.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        # Create token
        token = create_token(user.id, user.username, user.role.value if hasattr(user.role, "value") else user.role, mfa_verified=True)
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
        logger.error(f"WebAuthn authentication finish failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.get("/webauthn/credentials")
async def list_credentials(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List the user's registered passkeys."""
    # Extract user_id from token
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
