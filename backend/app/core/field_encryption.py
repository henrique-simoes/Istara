"""Field-level encryption for sensitive database fields.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) from the
cryptography library. The encryption key is derived from a master key
stored in .env (DATA_ENCRYPTION_KEY).

Fields encrypted:
- ChannelInstance.config_json (Telegram tokens, Slack secrets, WhatsApp tokens)
- SurveyIntegration.config_json (OAuth tokens, API keys)
- MCPServerConfig.headers_json (auth headers)
- ProjectInterfaceConfig.* (Stitch and Figma credentials)
- User.email (PII) — encrypted value; equality checks use email_hash

Usage:
    from app.core.field_encryption import encrypt_field, decrypt_field, hash_field

    # Encrypt before storing
    encrypted = encrypt_field("my-secret-api-key")

    # Decrypt after reading
    plaintext = decrypt_field(encrypted)

    # Hash for uniqueness/search (one-way, deterministic)
    hashed = hash_field("user@example.com")
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import Text, TypeDecorator

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning(
        "cryptography library not installed — field encryption disabled. "
        "Install: pip install cryptography"
    )

_fernet_instance: object | None = None
_fernet_cache: dict[str, object] = {}
_decryption_failures = 0
_last_decryption_failure_at: str | None = None


class FieldEncryptionUnavailable(RuntimeError):  # noqa: N818 - public encryption protocol name
    """Field encryption was requested but no cipher is available."""


def _key_id(key_material: str) -> str:
    """Stable short identifier for a configured key (not secret)."""
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:8]


def _build_fernet(key_material: str):
    """Build a Fernet from a raw key or a passphrase (PBKDF2 fallback)."""
    try:
        return Fernet(key_material.encode() if isinstance(key_material, str) else key_material)
    except Exception:
        derived = hashlib.pbkdf2_hmac(
            "sha256", key_material.encode(), b"istara-field-encryption", 100_000
        )
        fernet_key = base64.urlsafe_b64encode(derived[:32])
        return Fernet(fernet_key)


def _fernet_for_material(key_material: str):
    cached = _fernet_cache.get(key_material)
    if cached is None:
        cached = _build_fernet(key_material)
        _fernet_cache[key_material] = cached
    return cached


def _configured_keys() -> list[tuple[str, str]]:
    """Return [(key_id, key_material)] primary first, then previous rotation keys."""
    from app.config import settings

    keys: list[tuple[str, str]] = []
    seen: set[str] = set()
    candidates = [settings.data_encryption_key or ""]
    candidates.extend(
        part.strip() for part in (settings.data_encryption_previous_keys or "").split(",")
    )
    for material in candidates:
        if not material or material in seen:
            continue
        seen.add(material)
        keys.append((_key_id(material), material))
    return keys


def reset_field_encryption_for_tests() -> None:
    """Clear cached ciphers; production code must never call this helper."""
    global _fernet_instance
    _fernet_instance = None
    _fernet_cache.clear()


def rotate_data_encryption_key(*, max_previous: int = 3) -> dict[str, object]:
    """Rotate the primary data-encryption key with read-backward compatibility.

    Generates a fresh key, shifts the current primary onto the previous-keys
    list (bounded), and clears cipher caches. Old rows stay decryptable via
    their key id; new writes use the new primary. The new key is returned
    ONCE for operator custody — like other server secrets it is memory-only
    unless injected externally, so the caller must surface that warning.
    """
    if not CRYPTO_AVAILABLE:
        raise FieldEncryptionUnavailable("cryptography library is not installed")
    from cryptography.fernet import Fernet as _Fernet

    from app.config import settings

    old_primary = (settings.data_encryption_key or "").strip()
    new_key = _Fernet.generate_key().decode()
    previous = [
        part.strip()
        for part in (settings.data_encryption_previous_keys or "").split(",")
        if part.strip() and part.strip() != new_key
    ]
    if old_primary and old_primary not in previous:
        previous.insert(0, old_primary)
    previous = previous[:max_previous]
    settings.data_encryption_key = new_key
    settings.data_encryption_previous_keys = ",".join(previous)
    reset_field_encryption_for_tests()
    logger.info(
        "Data encryption key rotated (new id %s, %d previous retained)",
        _key_id(new_key),
        len(previous),
    )
    return {
        "key_id": _key_id(new_key),
        "new_key": new_key,
        "previous_key_count": len(previous),
        "fingerprint": hashlib.sha256(new_key.encode("utf-8")).hexdigest()[:12],
    }


def _record_decryption_failure() -> None:
    global _decryption_failures, _last_decryption_failure_at
    _decryption_failures += 1
    _last_decryption_failure_at = datetime.now(UTC).isoformat()


def encryption_health_snapshot() -> dict[str, object]:
    """Return process-local integrity signals without field or secret values."""
    return {
        "healthy": _decryption_failures == 0,
        "decryption_failures": _decryption_failures,
        "last_failure_at": _last_decryption_failure_at,
        "crypto_available": CRYPTO_AVAILABLE,
    }


def reset_encryption_health_for_tests() -> None:
    """Reset process counters; production code must never call this helper."""
    global _decryption_failures, _last_decryption_failure_at
    _decryption_failures = 0
    _last_decryption_failure_at = None


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string field. Returns ``ENC:<key-id>:<ciphertext>``.

    Fails closed with :class:`FieldEncryptionUnavailable` when no cipher is
    available (missing key or library) or encryption itself fails — callers
    must never persist the returned value as plaintext on this path.
    """
    if not plaintext:
        return plaintext
    if not CRYPTO_AVAILABLE:
        raise FieldEncryptionUnavailable("cryptography library is not installed")
    from app.config import settings

    primary = settings.data_encryption_key or ""
    if not primary:
        raise FieldEncryptionUnavailable("data encryption key is not configured")
    try:
        f = _fernet_for_material(primary)
        encrypted = f.encrypt(plaintext.encode())
        return f"ENC:{_key_id(primary)}:" + encrypted.decode()
    except FieldEncryptionUnavailable:
        raise
    except Exception as e:
        raise FieldEncryptionUnavailable(f"field encryption failed: {e}") from e


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a string field. Returns plaintext.

    If the field is not encrypted (no ``ENC:`` prefix), returns as-is.
    Versioned rows (``ENC:<key-id>:<token>``) resolve their key first, then
    fall back through previous rotation keys; legacy rows (``ENC:<token>``)
    try every configured key. If decryption fails, returns an empty
    unavailable value without exposing the encrypted blob.
    """
    if not ciphertext or not ciphertext.startswith("ENC:"):
        return ciphertext  # Not encrypted — return as-is
    if not CRYPTO_AVAILABLE:
        _record_decryption_failure()
        logger.warning("Cannot decrypt encrypted field — cryptography library missing")
        return ""
    payload = ciphertext[4:]
    kid, sep, token = payload.partition(":")
    if not sep:
        token = payload
        kid = ""
    materials = _configured_keys()
    if not materials:
        _record_decryption_failure()
        logger.warning("Cannot decrypt encrypted field — no encryption key configured")
        return ""
    ordered = [m for k, m in materials if sep and k == kid]
    ordered.extend(m for _, m in materials if m not in ordered)
    for material in ordered:
        try:
            return _fernet_for_material(material).decrypt(token.encode()).decode()
        except Exception:
            continue
    _record_decryption_failure()
    logger.warning("Field decryption failed — value unavailable")
    return ""


def safe_decrypt_field(value: object | None) -> str:
    """Return a user-safe plaintext value without ever exposing ciphertext.

    ORM result processing normally calls :func:`decrypt_field`, but API
    serializers can also receive stale or manually assigned model values
    during key rotation, database restore, or tests.  Keep this boundary
    defensive so an ``ENC:`` blob cannot cross into a user-facing response.
    """
    if value is None:
        return ""
    try:
        return decrypt_field(str(value))
    except Exception:
        _record_decryption_failure()
        logger.warning("Could not normalize encrypted field for API response")
        return ""


def hash_field(value: str) -> str:
    """Create a deterministic one-way hash of a value.

    Used for fields that need uniqueness constraints or equality lookups
    (e.g., email) while the plaintext is stored encrypted.

    Returns a SHA-256 hex digest. If the input is empty, returns empty.
    """
    if not value:
        return ""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# SQLAlchemy Encrypted Type
# ---------------------------------------------------------------------------


class EncryptedType(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts/decrypts string values."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_field(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_field(str(value))


def ensure_encryption_key() -> str:
    """Generate and persist a data encryption key if none exists.

    Called during startup. The key is persisted to ``.env``.
    Returns the key string (empty if cryptography is not installed).
    """
    from app.config import settings

    if settings.data_encryption_key:
        return settings.data_encryption_key

    if not CRYPTO_AVAILABLE:
        logger.warning(
            "SECURITY WARNING: 'cryptography' library not installed. "
            "Sensitive data (channel tokens, API keys) will be stored in PLAINTEXT. "
            "Install: pip install cryptography"
        )
        return ""

    # Generate a new Fernet key
    key = Fernet.generate_key().decode()
    settings.data_encryption_key = key

    # Persist to the runtime env file (ISTARA_ENV_FILE-aware, Phase 6)
    try:
        from app.core.env_persistence import persist_env_value

        if persist_env_value("DATA_ENCRYPTION_KEY", key):
            logger.info("Generated and persisted data encryption key")
        else:
            logger.warning(
                "Generated data encryption key kept in process memory only — "
                "provide DATA_ENCRYPTION_KEY externally to survive restarts"
            )
    except Exception:
        logger.warning("Could not persist encryption key to env file")

    return key
