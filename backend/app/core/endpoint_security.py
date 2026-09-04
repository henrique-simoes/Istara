"""Shared validation for user-configured service endpoints."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

from app.core.log_redaction import SENSITIVE_QUERY_KEYS, redact_url

LOCAL_HOSTNAMES = {"localhost"}
LOCAL_SUFFIXES = (".localhost", ".local")


@dataclass(frozen=True)
class EndpointPolicy:
    """Policy for validating a configured network service URL."""

    service_name: str
    allow_http_private: bool = True
    allow_http_loopback: bool = True
    require_https_for_public: bool = True
    allow_query: bool = False
    allow_userinfo: bool = False


def normalized_service_url(raw_url: str, policy: EndpointPolicy) -> str:
    """Validate and normalize a user-provided endpoint URL.

    Istara accepts local and donated compute endpoints, but those URLs must not
    smuggle credentials, metadata-service targets, or public plaintext endpoints
    unless the policy explicitly allows them.
    """
    value = (raw_url or "").strip().rstrip("/")
    parsed = urlparse(value if "://" in value else f"http://{value}")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ValueError(f"{policy.service_name} URL must be an absolute http(s) URL")
    if (parsed.username or parsed.password) and not policy.allow_userinfo:
        raise ValueError(f"{policy.service_name} URL must not include embedded credentials")
    if parsed.query and not policy.allow_query:
        raise ValueError(f"{policy.service_name} URL must not include query parameters")
    if parsed.query:
        sensitive_keys = {
            key.lower()
            for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() in SENSITIVE_QUERY_KEYS
        }
        if sensitive_keys:
            raise ValueError(
                f"{policy.service_name} URL must not include sensitive query keys: "
                + ", ".join(sorted(sensitive_keys))
            )

    host = parsed.hostname.lower().strip("[]")
    host_scope = classify_host_scope(host)
    if host_scope in {"metadata", "blocked"}:
        raise ValueError(f"{policy.service_name} URL host is not allowed")
    if parsed.scheme == "http":
        if host_scope == "loopback" and policy.allow_http_loopback:
            return value
        if host_scope == "private" and policy.allow_http_private:
            return value
        if policy.require_https_for_public:
            raise ValueError(f"{policy.service_name} URL must use HTTPS for non-local endpoints")
    return value


def classify_host_scope(host: str) -> str:
    """Classify a host for endpoint policy decisions."""
    if not host:
        return "blocked"
    if host in LOCAL_HOSTNAMES or host.endswith(LOCAL_SUFFIXES):
        return "loopback"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "public"
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return "metadata" if str(ip).startswith("169.254.") else "blocked"
    if ip.is_private:
        return "private"
    return "public"


def redacted_endpoint_label(raw_url: str) -> str:
    """Return a URL-safe label for logs and security evidence."""
    return redact_url(raw_url or "")
