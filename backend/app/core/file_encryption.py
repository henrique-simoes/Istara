"""Application-level encryption for uploaded research files and backup archives."""

from __future__ import annotations

import contextlib
import hashlib
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

from app.config import settings

try:
    from cryptography.fernet import Fernet, InvalidToken

    CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover - covered by deployment security checks
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    CRYPTO_AVAILABLE = False

FILE_MAGIC = b"ISTARA-FILE-ENC-V1\n"
TEXT_PREFIX = "ENCFILE:"


def file_encryption_enabled() -> bool:
    return bool(settings.file_encryption_enabled)


def _read_macos_keychain_secret(service: str) -> str:
    if not service or not Path("/usr/bin/security").exists():
        return ""
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _write_macos_keychain_secret(service: str, key: str) -> bool:
    if not service or not Path("/usr/bin/security").exists():
        return False
    account = os.environ.get("USER") or "istara"
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "add-generic-password",
                "-U",
                "-s",
                service,
                "-a",
                account,
                "-w",
                key,
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0 and _read_macos_keychain_secret(service) == key


def _key_file_path() -> Path:
    return Path(settings.file_encryption_key_file).expanduser()


def _read_key_file() -> str:
    path = _key_file_path()
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_key_file(key: str) -> None:
    path = _key_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def resolve_file_encryption_key(*, create: bool = False) -> str:
    """Return the active file encryption key, optionally creating one.

    Priority is explicit environment/config key, macOS Keychain, then an
    owner-only local key file. The fallback file is intentional for portable
    local deployments and tests; production operators should prefer Keychain or
    a secrets manager mounted through ``FILE_ENCRYPTION_KEY``.
    """
    configured = (settings.file_encryption_key or "").strip()
    if configured:
        return configured

    keychain_key = _read_macos_keychain_secret(settings.file_encryption_keychain_service)
    if keychain_key:
        return keychain_key

    file_key = _read_key_file()
    if file_key:
        return file_key

    if not create:
        return ""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography is required for file encryption")
    key = Fernet.generate_key().decode()  # type: ignore[union-attr]
    if not _write_macos_keychain_secret(settings.file_encryption_keychain_service, key):
        _write_key_file(key)
    return key


def replace_file_encryption_key(key: str) -> None:
    """Persist a replacement master key using the configured storage strategy."""
    if settings.file_encryption_key:
        settings.file_encryption_key = key
        return
    if not _write_macos_keychain_secret(settings.file_encryption_keychain_service, key):
        _write_key_file(key)


def _fernet_for_key(key: str | None = None, *, create: bool = True):
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography is required for file encryption")
    active_key = key or resolve_file_encryption_key(create=create)
    if not active_key:
        raise RuntimeError("file encryption key is not configured")
    return Fernet(active_key.encode() if isinstance(active_key, str) else active_key)  # type: ignore[operator]


def key_fingerprint(key: str | None = None) -> str:
    active_key = key or resolve_file_encryption_key(create=False)
    if not active_key:
        return ""
    return hashlib.sha256(active_key.encode("utf-8")).hexdigest()[:12]


def is_encrypted_bytes(data: bytes) -> bool:
    return data.startswith(FILE_MAGIC)


def encrypt_bytes(data: bytes, *, key: str | None = None) -> bytes:
    if is_encrypted_bytes(data):
        return data
    return FILE_MAGIC + _fernet_for_key(key).encrypt(data)


def decrypt_bytes(data: bytes, *, key: str | None = None) -> bytes:
    if not is_encrypted_bytes(data):
        return data
    return _fernet_for_key(key, create=False).decrypt(data[len(FILE_MAGIC) :])


def is_encrypted_file(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        with open(p, "rb") as handle:
            return handle.read(len(FILE_MAGIC)) == FILE_MAGIC
    except OSError:
        return False


def read_file_bytes(path: str | Path) -> bytes:
    data = Path(path).read_bytes()
    return decrypt_bytes(data)


def read_file_text(path: str | Path, *, errors: str = "replace") -> str:
    return read_file_bytes(path).decode("utf-8", errors=errors)


def encrypt_file_in_place(path: str | Path, *, force: bool = False) -> bool:
    """Encrypt a file if file encryption is enabled.

    Returns True when the file is encrypted after the call.
    """
    if not force and not file_encryption_enabled():
        return False
    p = Path(path)
    if not p.exists() or not p.is_file() or is_encrypted_file(p):
        return is_encrypted_file(p)
    encrypted = encrypt_bytes(p.read_bytes())
    p.write_bytes(encrypted)
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return True


def decrypt_file_to_path(src: str | Path, dest: str | Path) -> None:
    Path(dest).write_bytes(read_file_bytes(src))


def encrypt_file_to_path(src: str | Path, dest: str | Path, *, force: bool = False) -> bool:
    """Encrypt a source file into a destination path.

    The destination is only written when file encryption is enabled or ``force``
    is true. This is used for backup archives so the plaintext archive can be
    deleted immediately after the encrypted copy is written.
    """
    if not force and not file_encryption_enabled():
        return False
    source = Path(src)
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encrypt_bytes(source.read_bytes()))
    try:
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return True


@contextlib.contextmanager
def decrypted_file_path(path: str | Path) -> Iterator[Path]:
    """Yield a plaintext path for processors that require a filesystem path."""
    p = Path(path)
    if not is_encrypted_file(p):
        yield p
        return
    with tempfile.NamedTemporaryFile(suffix=p.suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(read_file_bytes(p))
    try:
        yield tmp_path
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def encrypt_text_value(value: str, *, key: str | None = None) -> str:
    if not value or value.startswith(TEXT_PREFIX):
        return value
    token = _fernet_for_key(key).encrypt(value.encode("utf-8")).decode("utf-8")
    return TEXT_PREFIX + token


def decrypt_text_value(value: str, *, key: str | None = None) -> str:
    if not value or not value.startswith(TEXT_PREFIX):
        return value
    token = value[len(TEXT_PREFIX) :].encode("utf-8")
    try:
        return _fernet_for_key(key, create=False).decrypt(token).decode("utf-8")
    except InvalidToken:
        raise


def protect_document_text(value: str) -> str:
    if not file_encryption_enabled():
        return value
    return encrypt_text_value(value)


def reveal_document_text(value: str) -> str:
    if not value or not value.startswith(TEXT_PREFIX):
        return value
    return decrypt_text_value(value)


def rewrite_encrypted_file(path: str | Path, *, old_key: str, new_key: str) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    data = p.read_bytes()
    plaintext = decrypt_bytes(data, key=old_key)
    p.write_bytes(encrypt_bytes(plaintext, key=new_key))
    return True


def rewrite_encrypted_text(value: str, *, old_key: str, new_key: str) -> str:
    plaintext = decrypt_text_value(value, key=old_key) if value.startswith(TEXT_PREFIX) else value
    return encrypt_text_value(plaintext, key=new_key) if plaintext else plaintext


def managed_upload_files() -> list[Path]:
    root = Path(settings.upload_dir).expanduser()
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]

