"""JWT authentication service for team mode."""

import hashlib
import hmac
import json
import logging
import time
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import settings

logger = logging.getLogger(__name__)


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return urlsafe_b64decode(s)


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 (no external deps)."""
    salt = uuid.uuid4().hex
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a PBKDF2 hash."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        stored_dk = parts[2]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(dk.hex(), stored_dk)
    except Exception:
        return False


def create_token(user_id: str, username: str, role: str) -> str:
    """Create a JWT-like token (HMAC-SHA256 signed, no external deps)."""
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_expire_minutes * 60,
    }
    payload = _b64encode(json.dumps(payload_data).encode())
    signature_input = f"{header}.{payload}".encode()
    signature = hmac.new(settings.jwt_secret.encode(), signature_input, hashlib.sha256).digest()
    sig = _b64encode(signature)
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token. Returns payload dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        # Verify signature
        signature_input = f"{header}.{payload}".encode()
        expected = hmac.new(settings.jwt_secret.encode(), signature_input, hashlib.sha256).digest()
        actual = _b64decode(sig)
        if not hmac.compare_digest(expected, actual):
            return None
        # Decode payload
        payload_data = json.loads(_b64decode(payload))
        # Check expiration
        if payload_data.get("exp", 0) < time.time():
            return None
        return payload_data
    except Exception:
        return None
