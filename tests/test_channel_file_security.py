"""Channel attachment storage hardening tests."""

import pytest

from app.channels.telegram import TelegramAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.config import settings


def test_telegram_filename_and_instance_id_cannot_escape_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))

    adapter = TelegramAdapter(instance_id="../tenant//alpha")
    storage_dir = adapter._channel_storage_dir("channel_files")
    filename = adapter._safe_download_filename("../../.ssh/id_rsa", "../evil", ".bin")
    file_path = storage_dir / filename

    assert storage_dir.name == "tenant_alpha"
    assert "/" not in filename
    assert "\\" not in filename
    assert filename.endswith(".bin")
    file_path.resolve().relative_to(storage_dir.resolve())


def test_telegram_declared_size_limit_blocks_download(monkeypatch):
    monkeypatch.setattr(settings, "channel_attachment_max_bytes", 4)
    adapter = TelegramAdapter(instance_id="default")

    with pytest.raises(ValueError):
        adapter._ensure_download_size(5, "Telegram document")


@pytest.mark.asyncio
async def test_telegram_download_size_limit_checks_actual_bytes(monkeypatch):
    class FakeTelegramFile:
        async def download_to_memory(self, buf):
            buf.write(b"12345")

    monkeypatch.setattr(settings, "channel_attachment_max_bytes", 4)
    adapter = TelegramAdapter(instance_id="default")

    with pytest.raises(ValueError):
        await adapter._download_telegram_file(
            FakeTelegramFile(),
            declared_size=None,
            label="Telegram document",
        )


def test_whatsapp_filename_and_instance_id_cannot_escape_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))

    adapter = WhatsAppAdapter(instance_id="../tenant//alpha")
    storage_dir = adapter._channel_storage_dir("channel_audio")
    filename = adapter._safe_download_filename("../../.ssh/id_rsa", "../evil", ".ogg")
    file_path = storage_dir / filename

    assert storage_dir.name == "tenant_alpha"
    assert "/" not in filename
    assert "\\" not in filename
    assert filename.endswith(".ogg")
    file_path.resolve().relative_to(storage_dir.resolve())


def test_whatsapp_declared_size_limit_blocks_download(monkeypatch):
    monkeypatch.setattr(settings, "channel_attachment_max_bytes", 4)
    adapter = WhatsAppAdapter(instance_id="default")

    with pytest.raises(ValueError):
        adapter._ensure_download_size(5, "WhatsApp audio")
