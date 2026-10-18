"""Configured decider endpoints and the per-project egress rule.

Endpoints come from the ``decider_endpoints_json`` setting: a JSON list of objects with
``endpoint_id``, ``base_url`` and ``model``, plus optional ``keychain_service``,
``keychain_account``, ``api_key_env``, ``timeout_s`` and ``max_retries``. The JSON holds no secret.

Locality follows the URL host (``endpoint_security.classify_host_scope``): loopback and private
addresses are local, and anything else, including hosts given by name, is hosted. Sending research
data to a hosted decider is cloud egress, which a project must authorize explicitly (owner decision
DEC-1); without that authorization the call is refused before any request is built.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.core.decider.contract import SYSTEMONE_PATH
from app.core.endpoint_security import EndpointPolicy, classify_host_scope, normalized_service_url

_POLICY = EndpointPolicy(service_name="Decision model")
_LOCAL_SCOPES = frozenset({"loopback", "private"})
MAX_RETRIES_LIMIT = 5


class DeciderUnavailableError(RuntimeError):
    """A decider cannot be used for this call; ``reason`` is a stable code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class DeciderEndpoint:
    endpoint_id: str
    base_url: str
    model: str
    keychain_service: str = ""
    keychain_account: str = ""
    api_key_env: str = ""
    timeout_s: float = 30.0
    max_retries: int = 2
    locality: str = field(init=False, default="hosted")

    def __post_init__(self) -> None:
        if not self.endpoint_id.strip() or not self.model.strip():
            raise ValueError("decider endpoint_id and model must be non-empty")
        url = normalized_service_url(self.base_url, _POLICY)
        object.__setattr__(self, "base_url", url)
        scope = classify_host_scope((urlparse(url).hostname or "").lower().strip("[]"))
        object.__setattr__(self, "locality", "local" if scope in _LOCAL_SCOPES else "hosted")
        if not 0 < self.timeout_s <= 600:
            raise ValueError("decider timeout_s must be in (0, 600]")
        if not 0 <= self.max_retries <= MAX_RETRIES_LIMIT:
            raise ValueError(f"decider max_retries must be in [0, {MAX_RETRIES_LIMIT}]")

    @property
    def request_url(self) -> str:
        if self.base_url.endswith(SYSTEMONE_PATH):
            return self.base_url
        return self.base_url + SYSTEMONE_PATH

    @property
    def is_hosted(self) -> bool:
        return self.locality == "hosted"

    def __repr__(self) -> str:
        return (
            f"DeciderEndpoint(endpoint_id={self.endpoint_id!r}, model={self.model!r}, "
            f"locality={self.locality!r})"
        )


_FIELDS = (
    "endpoint_id",
    "base_url",
    "model",
    "keychain_service",
    "keychain_account",
    "api_key_env",
    "timeout_s",
    "max_retries",
)


def parse_endpoints(raw: str) -> dict[str, DeciderEndpoint]:
    """Parse the setting. Malformed configuration raises ``ValueError``; it never half-loads."""
    if not raw or not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("decider_endpoints_json must be a JSON list")
    endpoints: dict[str, DeciderEndpoint] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each decider endpoint must be a JSON object")
        unknown = set(item) - set(_FIELDS)
        if unknown:
            raise ValueError("unknown decider endpoint fields: " + ", ".join(sorted(unknown)))
        endpoint = DeciderEndpoint(**item)
        if endpoint.endpoint_id in endpoints:
            raise ValueError(f"duplicate decider endpoint_id {endpoint.endpoint_id!r}")
        endpoints[endpoint.endpoint_id] = endpoint
    return endpoints


def configured_endpoints() -> dict[str, DeciderEndpoint]:
    from app.config import settings

    return parse_endpoints(getattr(settings, "decider_endpoints_json", ""))


def require_egress_authorization(
    endpoint: DeciderEndpoint, project_id: str, authorized_endpoint_ids: Iterable[str]
) -> None:
    """Raise unless this project may send data to this endpoint.

    Every call must name its project. Local endpoints keep data on the user's hardware and need no
    opt-in; hosted endpoints need the project to list the endpoint id.
    """
    if not str(project_id or "").strip():
        raise DeciderUnavailableError("project_required")
    if endpoint.is_hosted and endpoint.endpoint_id not in set(authorized_endpoint_ids):
        raise DeciderUnavailableError("hosted_egress_not_authorized")
