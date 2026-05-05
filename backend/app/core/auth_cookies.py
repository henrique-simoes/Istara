"""Authentication cookie helpers.

The session cookie is host-bound and HttpOnly. Keep the legacy cookie readable
for one transition window so existing desktop/browser sessions do not break
immediately after the hardening release.
"""

from __future__ import annotations

from fastapi import Request, Response

from app.config import settings

AUTH_COOKIE_NAME = "__Host-istara_session"
LEGACY_AUTH_COOKIE_NAME = "istara_session"
AUTH_COOKIE_PATH = "/"
LEGACY_AUTH_COOKIE_PATH = "/api"


def get_auth_cookie_token(request: Request) -> str:
    """Return the current or legacy session cookie token from a request."""
    return request.cookies.get(AUTH_COOKIE_NAME, "") or request.cookies.get(
        LEGACY_AUTH_COOKIE_NAME, ""
    )


def has_auth_cookie(request: Request) -> bool:
    """Return whether the request contains any recognised auth cookie."""
    return bool(get_auth_cookie_token(request))


def set_auth_cookie(response: Response, token: str) -> None:
    """Set the hardened host-only session cookie and expire the legacy cookie."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.jwt_expire_minutes * 60,
        path=AUTH_COOKIE_PATH,
    )
    response.delete_cookie(key=LEGACY_AUTH_COOKIE_NAME, path=LEGACY_AUTH_COOKIE_PATH)
    response.delete_cookie(key=LEGACY_AUTH_COOKIE_NAME, path=AUTH_COOKIE_PATH)


def clear_auth_cookies(response: Response) -> None:
    """Clear both current and legacy auth cookies."""
    response.delete_cookie(key=AUTH_COOKIE_NAME, path=AUTH_COOKIE_PATH)
    response.delete_cookie(key=LEGACY_AUTH_COOKIE_NAME, path=LEGACY_AUTH_COOKIE_PATH)
    response.delete_cookie(key=LEGACY_AUTH_COOKIE_NAME, path=AUTH_COOKIE_PATH)
