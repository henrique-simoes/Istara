"""Field-level encryption for sensitive database fields.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) from the
cryptography library. The encryption key is derived from a master key
stored in .env (DATA_ENCRYPTION_KEY).

Fields encrypted:
- ChannelInstance.config_json (Telegram tokens, Slack secrets, WhatsApp tokens)
- SurveyIntegration.config_json (OAuth tokens, API keys)
- MCPServerConfig.headers_json (auth headers)
- User.email (PII)

Usage:
    from app.core.field_encryption import encrypt_field, decrypt_field

    # Encrypt before storing
    encrypted = encrypt_field("my-secret-api-key")

    # Decrypt after reading
    plaintext = decrypt_field(encrypted)
"""

from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning(
        "cryptography library not installed — field encryption disabled. "
        "Install: pip install cryptography"
    )

_fernet_instance: object | None = None


def _get_fernet():
    """Get or create the Fernet instance using the master key."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    if not CRYPTO_AVAILABLE:
        return None

    from app.config import settings

    key = settings.data_encryption_key
    if not key:
        return None

    # Fernet requires a 32-byte base64url-encoded key.
    # If the user provides a raw Fernet key it will work directly;
    # otherwise derive a proper key via PBKDF2.
    try:
        _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        import hashlib

        derived = hashlib.pbkdf2_hmac(
            "sha256", key.encode(), b"reclaw-field-encryption", 100_000
        )
        fernet_key = base64.urlsafe_b64encode(derived[:32])
        _fernet_instance = Fernet(fernet_key)

    return _fernet_instance


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string field. Returns the ciphertext as a string.

    If encryption is not available (no key or no cryptography lib),
    returns the plaintext unchanged (backward-compatible).
    """
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        return plaintext
    try:
        encrypted = f.encrypt(plaintext.encode())
        return "ENC:" + encrypted.decode()  # Prefix marks encrypted data
    except Exception:
        logger.warning("Field encryption failed — storing plaintext")
        return plaintext


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a string field. Returns plaintext.

    If the field is not encrypted (no ``ENC:`` prefix), returns as-is.
    If decryption fails, returns the ciphertext unchanged.
    """
    if not ciphertext or not ciphertext.startswith("ENC:"):
        return ciphertext  # Not encrypted — return as-is
    f = _get_fernet()
    if f is None:
        logger.warning("Cannot decrypt — no encryption key configured")
        return ciphertext
    try:
        encrypted_bytes = ciphertext[4:].encode()  # Strip "ENC:" prefix
        return f.decrypt(encrypted_bytes).decode()
    except Exception:
        logger.warning("Field decryption failed — returning ciphertext")
        return ciphertext


def ensure_encryption_key() -> str:
    """Generate and persist a data encryption key if none exists.

    Called during startup. The key is persisted to ``.env``.
    Returns the key string (empty if cryptography is not installed).
    """
    from app.config import settings

    if settings.data_encryption_key:
        return settings.data_encryption_key

    if not CRYPTO_AVAILABLE:
        return ""

    # Generate a new Fernet key
    key = Fernet.generate_key().decode()
    settings.data_encryption_key = key

    # Persist to .env
    try:
        from pathlib import Path

        env_path = Path(__file__).parent.parent.parent / ".env"
        lines = env_path.read_text().splitlines() if env_path.exists() else []
        # Replace existing line or append
        found = False
        for i, line in enumerate(lines):
            if line.startswith("DATA_ENCRYPTION_KEY="):
                lines[i] = f"DATA_ENCRYPTION_KEY={key}"
                found = True
                break
        if not found:
            lines.append(f"DATA_ENCRYPTION_KEY={key}")
        env_path.write_text("\n".join(lines) + "\n")
        logger.info("Generated and persisted data encryption key")
    except Exception:
        logger.warning("Could not persist encryption key to .env")

    return key
