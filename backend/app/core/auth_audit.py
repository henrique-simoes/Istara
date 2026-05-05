"""Auth/security audit event helpers."""

from __future__ import annotations

import json
from typing import Any

from fastapi import Request

from app.config import settings
from app.core.audit_middleware import write_audit_entry
from app.core.client_identity import get_client_ip


def _safe_details(details: dict[str, Any] | None) -> str:
    if not details:
        return "{}"
    safe: dict[str, Any] = {}
    for key, value in details.items():
        lower = str(key).lower()
        if any(secret in lower for secret in ("password", "secret", "token", "code", "key")):
            safe[key] = "[redacted]"
        else:
            safe[key] = value
    return json.dumps(safe, default=str, sort_keys=True)


async def record_auth_event(
    request: Request | None,
    event_type: str,
    *,
    user_id: str = "",
    status_code: int = 200,
    details: dict[str, Any] | None = None,
) -> None:
    """Write a structured auth event into the system audit log."""
    ip_address = ""
    user_agent = ""
    if request is not None:
        ip_address = get_client_ip(request, settings.trusted_proxy_hosts)
        user_agent = request.headers.get("user-agent", "")

    await write_audit_entry(
        user_id=user_id,
        method="AUTH",
        path=f"/auth/events/{event_type}"[:500],
        status_code=status_code,
        ip_address=ip_address,
        user_agent=user_agent[:500],
        details=_safe_details(details),
        event_type=event_type[:80],
    )
