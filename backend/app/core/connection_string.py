"""Connection string codec — tamper-proof bundles for client→server setup.

A connection string contains everything a client needs to connect:
server URL, WebSocket URL, network access token, and a pre-minted JWT.
Signed with HMAC-SHA256 so only the originating server can create valid strings.

Format:  rcl_<base64url(JSON payload)>.<base64url(HMAC-SHA256 signature)>
"""

import hashlib
import hmac
import json
import logging
import time

from app.config import settings
from app.core.auth import _b64decode, _b64encode, create_token

logger = logging.getLogger(__name__)

# Prefix makes connection strings visually identifiable
PREFIX = "rcl_"


def create_connection_string(
    server_url: str,
    label: str = "",
    expires_hours: int = 168,  # 7 days
    role: str = "researcher",
) -> str:
    """Generate a tamper-proof connection string.

    Bundles:
    - server_url: HTTPS URL for the web UI
    - ws_url: WSS URL for relay WebSocket (derived from server_url)
    - network_token: NETWORK_ACCESS_TOKEN for relay auth
    - jwt: pre-minted JWT for web UI login
    - expires_at: Unix timestamp
    - label: human-readable label (e.g. "Alice's laptop")
    """
    expires_at = int(time.time()) + (expires_hours * 3600)

    # Derive WebSocket URL from server URL
    ws_url = server_url.replace("https://", "wss://").replace("http://", "ws://")
    if not ws_url.endswith("/ws/relay"):
        ws_url = ws_url.rstrip("/") + "/ws/relay"

    # Mint a JWT for the invited user (pre-auth)
    # The JWT sub is "invite-<timestamp>" — redeemed when user registers
    jwt_token = create_token(
        user_id=f"invite-{int(time.time())}",
        username=label or "invited",
        role=role,
    )

    payload = {
        "v": 1,
        "server_url": server_url.rstrip("/"),
        "ws_url": ws_url,
        "network_token": settings.network_access_token or "",
        "jwt": jwt_token,
        "expires_at": expires_at,
        "label": label,
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = _b64encode(payload_json.encode())

    # Sign with HMAC-SHA256 using the same secret as JWT
    sig = hmac.new(
        settings.jwt_secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode(sig)

    return f"{PREFIX}{payload_b64}.{sig_b64}"


def decode_connection_string(conn_str: str) -> dict | None:
    """Decode and verify a connection string.

    Returns the payload dict or None if invalid/expired/tampered.
    """
    try:
        if not conn_str.startswith(PREFIX):
            return None

        body = conn_str[len(PREFIX):]
        parts = body.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts

        # Verify HMAC signature
        expected_sig = hmac.new(
            settings.jwt_secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("Connection string HMAC verification failed")
            return None

        # Decode payload
        payload = json.loads(_b64decode(payload_b64))

        # Check version
        if payload.get("v") != 1:
            return None

        # Check expiry
        if payload.get("expires_at", 0) < time.time():
            logger.info("Connection string expired")
            return None

        return payload
    except Exception as e:
        logger.warning(f"Connection string decode error: {e}")
        return None
