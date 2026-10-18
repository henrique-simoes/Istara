"""The single entry point to a decider: ``open_decider``.

It loads the configured endpoint, enforces the project's egress authorization, resolves the API key,
and returns a :class:`SystemOneClient`. Deciders triage research items for human review; they never
accept or promote evidence.
"""

from __future__ import annotations

from typing import Any

from app.core.decider.client import SystemOneClient
from app.core.decider.credentials import resolve_api_key
from app.core.decider.registry import (
    DeciderEndpoint,
    DeciderUnavailable,
    configured_endpoints,
    require_egress_authorization,
)


async def authorized_hosted_endpoint_ids(session: Any, project_id: str) -> list[str]:
    """Hosted decider endpoints the project has opted in to (empty when it has no policy row)."""
    from app.models.decision_policy import DecisionModelProjectPolicy

    policy = await session.get(DecisionModelProjectPolicy, project_id)
    return policy.hosted_egress_endpoint_ids() if policy is not None else []


async def open_decider(
    endpoint_id: str,
    project_id: str,
    *,
    session: Any = None,
    endpoints: dict[str, DeciderEndpoint] | None = None,
    transport: Any = None,
) -> SystemOneClient:
    """A client for ``endpoint_id`` that this project may use, or :class:`DeciderUnavailable`."""
    catalog = configured_endpoints() if endpoints is None else endpoints
    endpoint = catalog.get(endpoint_id)
    if endpoint is None:
        raise DeciderUnavailable("unknown_endpoint")
    authorized: list[str] = []
    if endpoint.is_hosted and str(project_id or "").strip():
        if session is None:
            from app.models.database import async_session

            async with async_session() as owned:
                authorized = await authorized_hosted_endpoint_ids(owned, project_id)
        else:
            authorized = await authorized_hosted_endpoint_ids(session, project_id)
    require_egress_authorization(endpoint, project_id, authorized)
    api_key = resolve_api_key(
        keychain_service=endpoint.keychain_service,
        keychain_account=endpoint.keychain_account,
        env_var=endpoint.api_key_env,
    )
    if endpoint.is_hosted and not api_key:
        raise DeciderUnavailable("missing_api_key")
    return SystemOneClient(endpoint, api_key=api_key, transport=transport)
