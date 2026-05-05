"""Connection string codec — tamper-proof bundles for client-to-server setup.

A connection string contains everything a client needs to connect:
server URL, WebSocket URL, type, nonce, and expiration. User invite strings
never mint a login token; redemption creates the server-backed session.

Format:  rcl_<base64url(JSON payload)>.<base64url(HMAC-SHA256 signature)>
"""

import hashlib
import hmac
import json
import logging
import secrets
import time

from app.config import settings
from app.core.auth import _b64decode, _b64encode

logger = logging.getLogger(__name__)

# Prefix makes connection strings visually identifiable
PREFIX = "rcl_"


def hash_connection_string(conn_str: str) -> str:
    """Create a deterministic one-way hash for exact connection-string lookup."""
    if not conn_str:
        return ""
    return hashlib.sha256(conn_str.encode("utf-8")).hexdigest()


def preview_connection_string(conn_str: str) -> str:
    """Return a non-secret preview suitable for logs and admin lists."""
    if not conn_str:
        return ""
    digest = hash_connection_string(conn_str)
    return f"{PREFIX}{digest[:12]}...{digest[-8:]}"


def create_connection_string(
    server_url: str,
    ws_url: str | None = None,
    label: str = "",
    expires_hours: int = 168,  # 7 days
    role: str = "researcher",
) -> str:
    """Generate a tamper-proof user invite connection string.

    Bundles:
    - server_url: HTTPS URL for the web UI
    - ws_url: WSS URL for relay WebSocket (derived from server_url)
    - expires_at: Unix timestamp
    - label: human-readable label (e.g. "Alice's laptop")
    """
    expires_at = int(time.time()) + (expires_hours * 3600)
    issued_at = int(time.time())

    # Derive WebSocket URL from server URL
    relay_ws_url = ws_url or server_url.replace("https://", "wss://").replace("http://", "ws://")
    if not relay_ws_url.endswith("/ws/relay"):
        relay_ws_url = relay_ws_url.rstrip("/") + "/ws/relay"

    payload = {
        "v": 1,
        "kind": "user_invite",
        "server_url": server_url.rstrip("/"),
        "ws_url": relay_ws_url,
        "nonce": secrets.token_urlsafe(18),
        "role": role,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "label": label,
    }

    return _encode_payload(payload)


def create_compute_donation_string(
    server_url: str,
    ws_url: str | None = None,
    label: str = "",
    expires_hours: int = 168,
) -> str:
    """Generate a tamper-proof compute donation string.

    Compute donation strings intentionally carry relay connection data only.
    They never carry or mint a user JWT.
    """
    expires_at = int(time.time()) + (expires_hours * 3600)
    relay_ws_url = ws_url or server_url.replace("https://", "wss://").replace("http://", "ws://")
    if not relay_ws_url.endswith("/ws/relay"):
        relay_ws_url = relay_ws_url.rstrip("/") + "/ws/relay"

    payload = {
        "v": 1,
        "kind": "compute_donation",
        "server_url": server_url.rstrip("/"),
        "ws_url": relay_ws_url,
        "network_token": settings.network_access_token or "",
        "expires_at": expires_at,
        "label": label,
    }

    return _encode_payload(payload)


def _encode_payload(payload: dict) -> str:
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

        body = conn_str[len(PREFIX) :]
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

        # Legacy strings predate explicit kinds and bundled both invite and
        # relay data. Keep validation compatible while new strings stay split.
        payload.setdefault("kind", "user_invite")

        # Check expiry
        if payload.get("expires_at", 0) < time.time():
            logger.info("Connection string expired")
            return None

        return payload
    except Exception as e:
        logger.warning(f"Connection string decode error: {e}")
        return None
