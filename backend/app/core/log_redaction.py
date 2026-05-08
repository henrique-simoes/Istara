"""Sensitive-value redaction for application and access logs."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "code",
    "connection_string",
    "invite",
    "key",
    "password",
    "refresh_token",
    "secret",
    "session",
    "session_id",
    "token",
}

REDACTION = "[REDACTED]"

_URL_LIKE_RE = re.compile(r"(?P<url>(?:https?://|/)[^\s\"'<>]+)")
_BEARER_RE = re.compile(r"\bBearer\s+[-._~+/=A-Za-z0-9]+", re.IGNORECASE)
_AUTH_HEADER_RE = re.compile(r"\bAuthorization\s*:\s*(?!Bearer\b)[^\s,;&]+", re.IGNORECASE)
_CONNECTION_STRING_RE = re.compile(r"\brcl_[A-Za-z0-9._=-]+")
_KEY_VALUE_RE = re.compile(
    r"(?P<key>\b(?:access[_-]?token|api[_-]?key|client[_-]?secret|"
    r"connection[_-]?string|password|refresh[_-]?token|secret|session[_-]?id|token)\b)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\"'\s,;&\\%]+)",
    re.IGNORECASE,
)


def _sanitize_for_log(value: str) -> str:
    return value.replace("\r", "\\r").replace("\n", "\\n")


def redact_url(value: str) -> str:
    """Redact sensitive URL query parameters and embedded basic-auth secrets."""
    try:
        parts = urlsplit(value)
    except ValueError:
        return _sanitize_for_log(value)

    if not parts.query and "@" not in parts.netloc:
        return _sanitize_for_log(value)

    netloc = parts.netloc
    if "@" in netloc:
        _, host = netloc.rsplit("@", 1)
        netloc = f"{REDACTION}@{host}"

    query = urlencode(
        [
            (key, REDACTION if key.lower() in SENSITIVE_QUERY_KEYS else item_value)
            for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        ],
        doseq=True,
    )
    return _sanitize_for_log(urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment)))


def redact_text(value: str) -> str:
    """Redact sensitive tokens in a log message while preserving useful context."""
    value = _sanitize_for_log(value)
    value = _URL_LIKE_RE.sub(lambda match: redact_url(match.group("url")), value)
    value = _BEARER_RE.sub(f"Bearer {REDACTION}", value)
    value = _AUTH_HEADER_RE.sub(f"Authorization: {REDACTION}", value)
    value = _CONNECTION_STRING_RE.sub(f"rcl_{REDACTION}", value)

    def replace_key_value(match: re.Match[str]) -> str:
        return (
            f"{match.group('key')}{match.group('sep')}"
            f"{match.group('quote')}{REDACTION}{match.group('quote')}"
        )

    return _KEY_VALUE_RE.sub(replace_key_value, value)


def _redact_arg(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, tuple):
        return tuple(_redact_arg(item) for item in value)
    if isinstance(value, list):
        return [_redact_arg(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _redact_arg(item) for key, item in value.items()}
    return value


class SensitiveLogRedactionFilter(logging.Filter):
    """Logging filter that removes sensitive URL, token, and credential values."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            record.args = _redact_arg(record.args)
        return True


def install_sensitive_log_redaction() -> None:
    """Attach the redaction filter once to app and server loggers."""
    filter_name = SensitiveLogRedactionFilter.__name__
    for logger_name in ("", "app", "uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        if not any(existing.__class__.__name__ == filter_name for existing in logger.filters):
            logger.addFilter(SensitiveLogRedactionFilter())
