"""HTTP security header contract and validation helpers."""

from __future__ import annotations

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self';"
    ),
}

REQUIRED_CSP_DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
)


def apply_security_headers(headers) -> None:
    """Apply Istara's security header contract to a mutable headers object."""
    for key, value in SECURITY_HEADERS.items():
        headers[key] = value


def validate_security_headers(headers: dict[str, str]) -> list[str]:
    """Return validation issues for production security headers."""
    normalized = {key.lower(): value for key, value in headers.items()}
    issues: list[str] = []

    if normalized.get("x-content-type-options", "").lower() != "nosniff":
        issues.append("X-Content-Type-Options must be nosniff")
    if normalized.get("x-frame-options", "").upper() != "DENY":
        issues.append("X-Frame-Options must be DENY")

    hsts = normalized.get("strict-transport-security", "")
    if "max-age=31536000" not in hsts or "includesubdomains" not in hsts.lower():
        issues.append("Strict-Transport-Security must include one-year max-age and subdomains")

    csp = normalized.get("content-security-policy", "")
    for directive in REQUIRED_CSP_DIRECTIVES:
        if directive not in csp:
            issues.append(f"Content-Security-Policy missing directive: {directive}")
    if "*" in csp:
        issues.append("Content-Security-Policy must not contain wildcard sources")

    permissions = normalized.get("permissions-policy", "")
    for feature in ("camera=()", "microphone=()", "geolocation=()"):
        if feature not in permissions:
            issues.append(f"Permissions-Policy missing {feature}")

    return issues
