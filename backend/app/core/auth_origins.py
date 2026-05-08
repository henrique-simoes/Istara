"""Browser origin and WebAuthn configuration helpers."""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from fastapi import Request

LOCALHOST_HOSTS = {"localhost"}
LOOPBACK_IPS = {"127.0.0.1", "::1"}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def normalize_origin(value: str) -> str:
    """Normalize a URL-like value to ``scheme://host[:port]``."""
    raw = (value or "").strip()
    if not raw or raw == "*":
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.hostname:
        return ""
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return ""
    host = parsed.hostname.lower().rstrip(".")
    port = f":{parsed.port}" if parsed.port is not None else ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{scheme}://{host}{port}"


def request_origin(request: Request) -> str:
    """Return the browser Origin or Referer origin for CSRF checks."""
    origin = request.headers.get("origin", "").strip()
    if origin:
        return normalize_origin(origin)
    referer = request.headers.get("referer", "").strip()
    if not referer:
        return ""
    return normalize_origin(referer)


def configured_trusted_origins(settings_obj: Any) -> set[str]:
    """Return exact browser origins trusted for auth and WebAuthn ceremonies."""
    origins: set[str] = set()
    for raw in _split_csv(getattr(settings_obj, "cors_origins", "")):
        normalized = normalize_origin(raw)
        if normalized:
            origins.add(normalized)
    for raw in _split_csv(getattr(settings_obj, "webauthn_origins", "")):
        normalized = normalize_origin(raw)
        if normalized:
            origins.add(normalized)
    return origins


def _host_is_loopback(host: str) -> bool:
    host = host.lower().strip("[]")
    if host in LOCALHOST_HOSTS or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in LOOPBACK_IPS


def webauthn_origin_has_secure_context(origin: str) -> bool:
    """Return whether the origin is usable for browser WebAuthn."""
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https":
        return True
    return parsed.scheme == "http" and (host == "localhost" or host.endswith(".localhost"))


def rp_id_matches_origin(rp_id: str, origin: str) -> bool:
    """Return whether a WebAuthn RP ID is in scope for an origin."""
    rp = (rp_id or "").strip().lower().rstrip(".")
    parsed = urlparse(origin)
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not rp or not host:
        return False
    if rp == "localhost":
        return host == "localhost" or host.endswith(".localhost")
    return host == rp or host.endswith(f".{rp}")


def webauthn_expected_origins(settings_obj: Any) -> list[str]:
    """Return configured WebAuthn origins, normalized and RP-compatible."""
    rp_id = (getattr(settings_obj, "webauthn_rp_id", "") or "localhost").strip()
    raw_origins = _split_csv(getattr(settings_obj, "webauthn_origins", ""))
    if not raw_origins:
        raw_origins = _split_csv(getattr(settings_obj, "cors_origins", ""))

    origins: list[str] = []
    for raw in raw_origins:
        origin = normalize_origin(raw)
        if not origin:
            continue
        if not webauthn_origin_has_secure_context(origin):
            continue
        if not rp_id_matches_origin(rp_id, origin):
            continue
        if origin not in origins:
            origins.append(origin)
    return origins or ["http://localhost:3000"]


def _valid_webauthn_origins(settings_obj: Any) -> list[str]:
    """Return valid configured WebAuthn origins without fallback defaults."""
    rp_id = (getattr(settings_obj, "webauthn_rp_id", "") or "localhost").strip()
    raw_origins = _split_csv(getattr(settings_obj, "webauthn_origins", ""))
    origins: list[str] = []
    for raw in raw_origins:
        origin = normalize_origin(raw)
        if (
            origin
            and webauthn_origin_has_secure_context(origin)
            and rp_id_matches_origin(rp_id, origin)
            and origin not in origins
        ):
            origins.append(origin)
    return origins


def security_configuration_warnings(settings_obj: Any) -> list[str]:
    """Return actionable auth/WebAuthn configuration warnings."""
    warnings: list[str] = []
    cors_origins = [
        normalize_origin(raw) for raw in _split_csv(getattr(settings_obj, "cors_origins", ""))
    ]
    cors_origins = [origin for origin in cors_origins if origin]
    trusted_origins = sorted(configured_trusted_origins(settings_obj))
    rp_id = (getattr(settings_obj, "webauthn_rp_id", "") or "localhost").strip()
    explicit_webauthn = bool((getattr(settings_obj, "webauthn_origins", "") or "").strip())
    team_mode = bool(getattr(settings_obj, "team_mode", False))

    if (
        team_mode
        and trusted_origins
        and all(_host_is_loopback(urlparse(origin).hostname or "") for origin in trusted_origins)
    ):
        warnings.append(
            "Team mode only trusts localhost origins. Configure CORS_ORIGINS and "
            "WEBAUTHN_ORIGINS with exact production HTTPS origins before remote use."
        )

    cors_regex = (getattr(settings_obj, "cors_origin_regex", "") or "").strip()
    if cors_regex:
        if cors_regex == r"https?://[^/]+:3000":
            warnings.append(
                "CORS_ORIGIN_REGEX allows arbitrary hosts on port 3000. Prefer exact "
                "CORS_ORIGINS for production."
            )
        else:
            warnings.append(
                "CORS_ORIGIN_REGEX is enabled. Ensure auth-capable browser origins are "
                "also listed exactly in CORS_ORIGINS or WEBAUTHN_ORIGINS."
            )

    candidate_origins = (
        [normalize_origin(raw) for raw in _split_csv(getattr(settings_obj, "webauthn_origins", ""))]
        if explicit_webauthn
        else cors_origins
    )
    candidate_origins = [origin for origin in candidate_origins if origin]
    for origin in candidate_origins:
        if not webauthn_origin_has_secure_context(origin):
            warnings.append(f"WebAuthn origin {origin} is not HTTPS or localhost.")
        if not rp_id_matches_origin(rp_id, origin):
            warnings.append(
                f"WebAuthn origin {origin} does not match RP ID {rp_id}; passkeys "
                "will fail from that origin."
            )

    if explicit_webauthn and not _valid_webauthn_origins(settings_obj):
        warnings.append("No configured WebAuthn origins are valid for the current RP ID.")

    return warnings


def production_security_configuration_issues(settings_obj: Any) -> list[str]:
    """Return fail-closed issues for production/team auth configuration."""
    issues: list[str] = []
    runtime_profile = (getattr(settings_obj, "istara_runtime_profile", "") or "").lower()
    production_like = runtime_profile in {"public", "production"}
    team_mode = bool(getattr(settings_obj, "team_mode", False))
    if not production_like:
        return issues

    trusted_origins = sorted(configured_trusted_origins(settings_obj))
    jwt_secret = str(getattr(settings_obj, "jwt_secret", "") or "")
    rp_id = (getattr(settings_obj, "webauthn_rp_id", "") or "localhost").strip().lower()
    cors_regex = (getattr(settings_obj, "cors_origin_regex", "") or "").strip()

    if not team_mode:
        issues.append("Production/public profile must enable TEAM_MODE.")
    if not jwt_secret or jwt_secret == "istara-dev-secret-change-in-production" or len(jwt_secret) < 32:
        issues.append("Production/public profile requires a strong JWT_SECRET.")
    if not trusted_origins:
        issues.append("Production/public profile requires exact trusted browser origins.")
    for origin in trusted_origins:
        parsed = urlparse(origin)
        host = parsed.hostname or ""
        if parsed.scheme != "https":
            issues.append(f"Production trusted origin must use HTTPS: {origin}")
        if _host_is_loopback(host):
            issues.append(f"Production trusted origin must not be loopback-only: {origin}")
    if rp_id == "localhost" or _host_is_loopback(rp_id):
        issues.append("Production WebAuthn RP ID must be the deployed domain, not localhost.")
    if cors_regex:
        issues.append("Production/public profile must use exact CORS_ORIGINS, not regex.")

    return issues
