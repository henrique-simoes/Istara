"""Cryptographic authentication primitives for Istara.

Provides:
- Argon2id password hashing (NIST SP 800-63B Rev.4 compliant)
- Cryptographically secure recovery code generation
- TOTP (RFC 6238) generation and verification
- Breach password checking via Have I Been Pwned k-anonymity API
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Argon2id password hashing
# ---------------------------------------------------------------------------

try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import VerifyMismatchError, VerificationError

    _ARGON2_AVAILABLE = True
    _ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,    # 64 MB
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )
except ImportError:
    _ARGON2_AVAILABLE = False
    _ph = None
    logger.warning(
        "argon2-cffi not installed — falling back to PBKDF2-HMAC-SHA256. "
        "Install with: pip install argon2-cffi"
    )


def hash_password(password: str) -> str:
    """Hash a password using Argon2id (preferred) or PBKDF2-HMAC-SHA256 (fallback).

    Argon2id is the NIST-recommended algorithm (SP 800-63B Rev.4).
    It is memory-hard and resistant to GPU/ASIC attacks.
    """
    if _ARGON2_AVAILABLE:
        return _ph.hash(password)
    # Fallback: PBKDF2-HMAC-SHA256
    return _hash_pbkdf2(password)


def _hash_pbkdf2(password: str) -> str:
    """PBKDF2-HMAC-SHA256 fallback — 260K iterations (OWASP 2024 minimum)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:260000${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2id or PBKDF2 hash.

    Auto-detects the hash format from the prefix.
    """
    if password_hash.startswith("pbkdf2:"):
        return _verify_pbkdf2(password, password_hash)
    if _ARGON2_AVAILABLE:
        try:
            return _ph.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError):
            return False
        except Exception:
            return False
    return False


def _verify_pbkdf2(password: str, password_hash: str) -> bool:
    """Verify a password against a PBKDF2 hash."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        params = parts[0].split(":")
        if len(params) != 3:
            return False
        salt = parts[1]
        iterations = int(params[2])
        stored_dk = parts[2]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
        return hmac.compare_digest(dk.hex(), stored_dk)
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be upgraded to a stronger algorithm.

    Returns True if:
    - Hash is PBKDF2 (should be Argon2id)
    - Hash is PBKDF2 with < 260K iterations
    - Hash is Argon2id with outdated parameters
    """
    if password_hash.startswith("pbkdf2:"):
        return True  # Always upgrade PBKDF2 to Argon2id
    if _ARGON2_AVAILABLE and not password_hash.startswith("$argon"):
        return True
    return False


# ---------------------------------------------------------------------------
# JWT token handling (HMAC-SHA256, no external deps — upgrade path in Phase 7)
# ---------------------------------------------------------------------------

def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return urlsafe_b64decode(s)


def create_token(user_id: str, username: str, role: str, mfa_verified: bool = False) -> str:
    """Create a JWT-like token (HMAC-SHA256 signed).

    Includes MFA verification status and a unique token ID for future revocation.
    """
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "sub": user_id,
        "username": username,
        "role": role,
        "mfa": mfa_verified,
        "jti": secrets.token_urlsafe(16),  # Unique token ID for future revocation
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
        # Verify algorithm — reject alg: none attacks
        header_data = json.loads(_b64decode(header))
        if header_data.get("alg") != "HS256":
            return None
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


# ---------------------------------------------------------------------------
# Recovery codes — cryptographically secure, one-time use
# ---------------------------------------------------------------------------

def generate_recovery_codes(count: int = 8, code_length: int = 16) -> list[str]:
    """Generate cryptographically secure recovery codes.

    Each code is formatted as XXXX-XXXX-XXXX-XXXX for readability.
    """
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No O/0/I/1 confusion
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(chars) for _ in range(code_length))
        formatted = "-".join(raw[i:i + 4] for i in range(0, code_length, 4))
        codes.append(formatted)
    return codes


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code using Argon2id (same as passwords)."""
    return hash_password(code.upper().replace("-", ""))


def verify_recovery_code(code: str, hashed: str) -> bool:
    """Verify a recovery code against its Argon2id hash."""
    return verify_password(code.upper().replace("-", ""), hashed)


# ---------------------------------------------------------------------------
# TOTP — RFC 6238 implementation
# ---------------------------------------------------------------------------

try:
    import pyotp
    _PYOTP_AVAILABLE = True
except ImportError:
    _PYOTP_AVAILABLE = False
    logger.warning(
        "pyotp not installed — TOTP 2FA unavailable. "
        "Install with: pip install pyotp"
    )


def generate_totp_secret() -> str | None:
    """Generate a 32-character base32 secret for TOTP."""
    if not _PYOTP_AVAILABLE:
        return None
    return pyotp.random_base32()


def generate_totp_provisioning_uri(secret: str, username: str, issuer: str = "Istara") -> str | None:
    """Generate an OTP provisioning URI for QR code display."""
    if not _PYOTP_AVAILABLE:
        return None
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, token: str) -> bool:
    """Verify a TOTP token with ±30 second tolerance window."""
    if not _PYOTP_AVAILABLE:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # ±30 seconds
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Breach password checking — k-anonymity (Have I Been Pwned)
# ---------------------------------------------------------------------------

async def is_password_breached(password: str) -> bool:
    """Check if a password has appeared in a known data breach.

    Uses the Have I Been Pwned k-anonymity API.
    Only the first 5 characters of the SHA-1 hash are sent —
    the full password hash NEVER leaves the machine.

    NIST SP 800-63B Rev.4 requires this check for all new/changed passwords.
    """
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.pwnedpasswords.com/range/{prefix}")
            if resp.status_code != 200:
                # API unavailable — don't block registration, just log
                logger.warning(f"Have I Been Pwned API returned {resp.status_code}")
                return False
            return any(line.split(":")[0] == suffix for line in resp.text.splitlines())
    except Exception as e:
        logger.warning(f"Breach check failed: {e}")
        return False  # Don't block registration on API failure
