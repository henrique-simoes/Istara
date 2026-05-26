"""Tests for managed file, document text, and backup archive encryption."""

import json
import tarfile
from io import BytesIO

import pytest

from app.config import settings
from app.core.backup_manager import BackupManager
from app.core.file_encryption import (
    FILE_MAGIC,
    TEXT_PREFIX,
    decrypt_file_to_path,
    encrypt_bytes,
    encrypt_file_in_place,
    is_encrypted_file,
    protect_document_text,
    read_file_text,
    reveal_document_text,
    resolve_file_encryption_key,
)


@pytest.fixture(autouse=True)
def file_encryption_settings(tmp_path, monkeypatch):
    original_enabled = settings.file_encryption_enabled
    original_key = settings.file_encryption_key
    original_key_file = settings.file_encryption_key_file
    original_keychain = settings.file_encryption_keychain_service
    monkeypatch.setattr(settings, "file_encryption_enabled", True)
    monkeypatch.setattr(settings, "file_encryption_key", "")
    monkeypatch.setattr(settings, "file_encryption_key_file", str(tmp_path / "file-encryption.key"))
    monkeypatch.setattr(settings, "file_encryption_keychain_service", "")
    yield
    settings.file_encryption_enabled = original_enabled
    settings.file_encryption_key = original_key
    settings.file_encryption_key_file = original_key_file
    settings.file_encryption_keychain_service = original_keychain


def test_managed_file_encryption_round_trip(tmp_path):
    source = tmp_path / "research-note.txt"
    source.write_text("participant quote with sensitive details", encoding="utf-8")

    assert encrypt_file_in_place(source) is True
    assert source.read_bytes().startswith(FILE_MAGIC)
    assert is_encrypted_file(source)
    assert read_file_text(source) == "participant quote with sensitive details"

    restored = tmp_path / "restored.txt"
    decrypt_file_to_path(source, restored)
    assert restored.read_text(encoding="utf-8") == "participant quote with sensitive details"


def test_document_text_encryption_round_trip():
    protected = protect_document_text("interview transcript text")
    assert protected.startswith(TEXT_PREFIX)
    assert reveal_document_text(protected) == "interview transcript text"


def test_encrypted_backup_archive_verifies_with_configured_key(tmp_path):
    resolve_file_encryption_key(create=True)
    plain_archive = tmp_path / "backup.tar.gz"
    encrypted_archive = tmp_path / "backup.tar.gz.enc"

    with tarfile.open(plain_archive, "w:gz") as tar:
        manifest = json.dumps({"version": "1.0", "checksums": {}, "components": {}}).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        tar.addfile(info, BytesIO(manifest))

    encrypted_archive.write_bytes(encrypt_bytes(plain_archive.read_bytes()))
    plain_archive.unlink()

    assert is_encrypted_file(encrypted_archive)
    result = BackupManager()._verify_sync(str(encrypted_archive))
    assert result["valid"] is True
