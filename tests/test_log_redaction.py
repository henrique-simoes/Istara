from __future__ import annotations

import logging

from app.core.log_redaction import SensitiveLogRedactionFilter, redact_text, redact_url


def test_redact_url_masks_sensitive_query_values() -> None:
    redacted = redact_url("/ws/relay?token=super-secret&project_id=p1")

    assert "super-secret" not in redacted
    assert "token=%5BREDACTED%5D" in redacted
    assert "project_id=p1" in redacted


def test_redact_text_masks_urls_bearer_tokens_and_connection_strings() -> None:
    message = (
        "GET /ws?token=abc HTTP/1.1 Authorization: Bearer secret-token "
        "connection_string=rcl_sensitive.invite.value"
    )

    redacted = redact_text(message)

    assert "abc" not in redacted
    assert "secret-token" not in redacted
    assert "rcl_sensitive" not in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "connection_string=[REDACTED]" in redacted


def test_redaction_filter_masks_uvicorn_access_args() -> None:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:54321", "GET", "/ws?token=s3cr3t", "1.1", 101),
        exc_info=None,
    )

    assert SensitiveLogRedactionFilter().filter(record) is True
    rendered = record.getMessage()

    assert "s3cr3t" not in rendered
    assert "token=%5BREDACTED%5D" in rendered


def test_redact_text_neutralizes_log_injection_newlines() -> None:
    redacted = redact_text("token=abc\r\nforged=true")

    assert "\n" not in redacted
    assert "\r" not in redacted
    assert "\\r\\n" in redacted
    assert "abc" not in redacted
