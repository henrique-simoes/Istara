"""Tests for field-level encryption (Fernet symmetric encryption)."""

import pytest

from cryptography.fernet import Fernet

from app.core.field_encryption import (
    encrypt_field,
    decrypt_field,
    ensure_encryption_key,
    reset_field_encryption_for_tests,
    rotate_data_encryption_key,
    FieldEncryptionUnavailable,
    CRYPTO_AVAILABLE,
    encryption_health_snapshot,
    reset_encryption_health_for_tests,
)


@pytest.fixture(autouse=True)
def setup_encryption():
    """Set a test encryption key and reset cached ciphers."""
    import app.core.field_encryption as fe

    # Set a test key in settings
    from app.config import settings

    original_key = settings.data_encryption_key
    original_previous = settings.data_encryption_previous_keys
    settings.data_encryption_key = Fernet.generate_key().decode()
    settings.data_encryption_previous_keys = ""
    reset_field_encryption_for_tests()
    reset_encryption_health_for_tests()
    yield
    settings.data_encryption_key = original_key
    settings.data_encryption_previous_keys = original_previous
    reset_field_encryption_for_tests()
    reset_encryption_health_for_tests()


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

    def test_decrypt_invalid_encrypted_fails_closed(self):
        """Invalid ENC: values (tampered) fail closed without leaking ciphertext."""
        result = decrypt_field("ENC:invalid-base64-data!!!")
        assert result == ""
        health = encryption_health_snapshot()
        assert health["decryption_failures"] == 1
        assert health["healthy"] is False
        assert health["last_failure_at"]

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

        reset_field_encryption_for_tests()

        key = ensure_encryption_key()
        assert key is not None
        assert len(key) > 32  # Fernet keys are 44 chars base64

        # Verify the key works for encryption
        encrypted = encrypt_field("test")
        assert encrypted.startswith("ENC:")

        # Restore
        settings.data_encryption_key = original_key
        reset_field_encryption_for_tests()

    def test_encrypt_without_key_fails_closed(self):
        """Missing key raises instead of storing plaintext."""
        from app.config import settings

        original_key = settings.data_encryption_key
        settings.data_encryption_key = ""
        reset_field_encryption_for_tests()
        try:
            with pytest.raises(FieldEncryptionUnavailable):
                encrypt_field("must-not-persist")
        finally:
            settings.data_encryption_key = original_key
            reset_field_encryption_for_tests()

    def test_versioned_format_and_legacy_decrypt(self):
        original = "rotate-me"
        encrypted = encrypt_field(original)
        assert encrypted.count(":") >= 2
        assert decrypt_field(encrypted) == original
        # Legacy unversioned rows still decrypt.
        import app.core.field_encryption as fe

        from app.config import settings

        legacy_token = fe._fernet_for_material(settings.data_encryption_key).encrypt(
            original.encode()
        ).decode()
        assert decrypt_field("ENC:" + legacy_token) == original

    def test_rotation_keeps_old_rows_readable(self):
        from app.config import settings

        old_row = encrypt_field("long-lived-secret")
        old_key = settings.data_encryption_key
        result = rotate_data_encryption_key()
        assert result["previous_key_count"] == 1
        assert settings.data_encryption_key != old_key
        assert old_key in settings.data_encryption_previous_keys
        # Old row decrypts via retained previous key; new writes use new key.
        assert decrypt_field(old_row) == "long-lived-secret"
        assert decrypt_field(encrypt_field("fresh-secret")) == "fresh-secret"
