"""Upload scanning and quarantine helpers."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.core.content_guard import ContentGuard

_guard = ContentGuard()

_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".wav": (b"RIFF",),
    ".ogg": (b"OggS",),
    ".mp4": (b"\x00\x00\x00",),
    ".webm": (b"\x1a\x45\xdf\xa3",),
    ".mov": (b"\x00\x00\x00",),
}


@dataclass
class UploadSecurityVerdict:
    """Security verdict for an uploaded artifact."""

    allowed: bool
    quarantine: bool
    reason: str = ""
    sha256: str = ""
    size_bytes: int = 0
    extension: str = ""
    declared_content_type: str = ""
    scanner_enabled: bool = False
    scanner_exit_code: int | None = None
    scanner_output: str = ""
    warnings: list[str] = field(default_factory=list)
    threat_level: str = "none"
    threats: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        return {
            "allowed": self.allowed,
            "quarantine": self.quarantine,
            "reason": self.reason,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "extension": self.extension,
            "declared_content_type": self.declared_content_type,
            "scanner_enabled": self.scanner_enabled,
            "scanner_exit_code": self.scanner_exit_code,
            "scanner_output": self.scanner_output[:500],
            "warnings": self.warnings,
            "threat_level": self.threat_level,
            "threats": self.threats,
        }


def scan_upload_file(
    file_path: Path,
    *,
    declared_content_type: str = "",
    extracted_text: str = "",
    run_external_scanner: bool = True,
) -> UploadSecurityVerdict:
    """Run deterministic upload checks and an optional scanner command."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    data_head = path.read_bytes()[:512]
    stat = path.stat()
    verdict = UploadSecurityVerdict(
        allowed=True,
        quarantine=False,
        sha256=_sha256(path),
        size_bytes=stat.st_size,
        extension=suffix,
        declared_content_type=declared_content_type or "",
    )

    expected = _MAGIC_SIGNATURES.get(suffix)
    if (
        expected
        and data_head
        and not any(data_head.startswith(signature) for signature in expected)
    ):
        verdict.allowed = False
        verdict.quarantine = True
        verdict.reason = f"{suffix} file signature did not match its extension"
        verdict.warnings.append("file_signature_mismatch")

    scanner_command = (
        (settings.upload_scanner_command or "").strip() if run_external_scanner else ""
    )
    if scanner_command:
        verdict.scanner_enabled = True
        scanner_result = _run_scanner(scanner_command, path)
        verdict.scanner_exit_code = scanner_result.returncode
        verdict.scanner_output = (scanner_result.stdout + scanner_result.stderr).strip()
        if scanner_result.returncode != 0:
            verdict.allowed = False
            verdict.quarantine = True
            verdict.reason = verdict.reason or "upload scanner rejected the file"
            verdict.warnings.append("scanner_rejected")

    if extracted_text:
        scan = _guard.scan_text(extracted_text)
        verdict.threat_level = scan.threat_level
        verdict.threats = scan.threats
        if scan.threat_level in ("medium", "high"):
            verdict.warnings.append("prompt_injection_indicators")
            if settings.upload_quarantine_on_prompt_injection:
                verdict.allowed = False
                verdict.quarantine = True
                verdict.reason = verdict.reason or "prompt injection indicators detected"

    return verdict


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_scanner(command: str, path: Path) -> subprocess.CompletedProcess[str]:
    if "{path}" in command:
        argv = [part.format(path=str(path)) for part in shlex.split(command)]
    else:
        argv = [*shlex.split(command), str(path)]
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=max(1, int(settings.upload_scanner_timeout_seconds)),
        check=False,
    )


def security_metadata_json(verdict: UploadSecurityVerdict) -> str:
    return json.dumps({"upload_security": verdict.to_metadata()}, sort_keys=True)
