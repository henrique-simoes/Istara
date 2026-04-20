"""Tests for field-level encryption (Fernet symmetric encryption)."""

import pytest
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet

from app.core.field_encryption import (
    encrypt_field,
    decrypt_field,
    ensure_encryption_key,
    CRYPTO_AVAILABLE,
    _get_fernet,
)


@pytest.fixture(autouse=True)
def setup_encryption():
    """Set a test encryption key and reset the Fernet instance."""
    import app.core.field_encryption as fe
    # Set a test key in settings
    from app.config import settings
    original_key = settings.data_encryption_key
    settings.data_encryption_key = Fernet.generate_key().decode()
    fe._fernet_instance = None  # Force re-creation with new key
    yield
    settings.data_encryption_key = original_key
    fe._fernet_instance = None


@pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
class TestFieldEncryption:
    """Test encrypt/decrypt field functionality."""

    def test_encrypt_produces_enc_prefix(self):
        result = encrypt_field("secret-value")
        assert result.startswith("ENC:")

    def test_decrypt_reverses_encryption(self):
        original = "my-secret-api-key"
        encrypted = encrypt_field(original)
        decrypted = decrypt_field(encrypted)
        assert decrypted == original

    def test_round_trip_various_values(self):
        test_values = [
            "simple",
            "with spaces",
            "special!@#$%^&*()",
            "unicode: \u00e9\u00e0\u00fc",
            "",
            "a" * 1000,
        ]
        for val in test_values:
            encrypted = encrypt_field(val)
            assert encrypted.startswith("ENC:") if val else True
            decrypted = decrypt_field(encrypted)
            assert decrypted == val, f"Round-trip failed for: {val!r}"

    def test_empty_string_returns_empty(self):
        result = encrypt_field("")
        assert result == ""

    def test_none_returns_none(self):
        result = encrypt_field(None)
        assert result is None

    def test_decrypt_non_encrypted_returns_as_is(self):
        """Non-ENC: prefixed values are returned unchanged."""
        result = decrypt_field("plain-text-value")
        assert result == "plain-text-value"

    def test_decrypt_invalid_encrypted_returns_as_is(self):
        """Invalid ENC: values (tampered) are returned unchanged, not crashed."""
        result = decrypt_field("ENC:invalid-base64-data!!!")
        assert "invalid" in result  # Returns ciphertext on failure

    def test_different_encryptions_produce_different_ciphertext(self):
        """Same plaintext should produce different ciphertext (random IV)."""
        val = "same-secret"
        enc1 = encrypt_field(val)
        enc2 = encrypt_field(val)
        assert enc1 != enc2  # Fernet includes random IV

    def test_ensure_encryption_key_generates_valid_key(self):
        """ensure_encryption_key generates a valid Fernet key."""
        from app.config import settings
        # Clear the existing key to force generation
        original_key = settings.data_encryption_key
        settings.data_encryption_key = ""
        import app.core.field_encryption as fe
        fe._fernet_instance = None

        key = ensure_encryption_key()
        assert key is not None
        assert len(key) > 32  # Fernet keys are 44 chars base64

        # Verify the key works for encryption
        encrypted = encrypt_field("test")
        assert encrypted.startswith("ENC:")

        # Restore
        settings.data_encryption_key = original_key
        fe._fernet_instance = None
