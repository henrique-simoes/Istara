"""Tests for proxy-aware client identity and bounded rate limiting."""

from unittest.mock import MagicMock

from app.core.client_identity import BoundedWindowRateLimiter, get_client_ip


def test_get_client_ip_prefers_x_forwarded_for():
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.10, 10.0.0.2"}
    request.client.host = "127.0.0.1"

    assert get_client_ip(request, "127.0.0.1") == "203.0.113.10"


def test_get_client_ip_falls_back_to_x_real_ip():
    request = MagicMock()
    request.headers = {"x-real-ip": "203.0.113.11"}
    request.client.host = "127.0.0.1"

    assert get_client_ip(request, "127.0.0.1") == "203.0.113.11"


def test_get_client_ip_ignores_forwarded_header_from_untrusted_socket():
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.12"}
    request.client.host = "198.51.100.20"

    assert get_client_ip(request, "127.0.0.1") == "198.51.100.20"


def test_get_client_ip_accepts_trusted_proxy_cidr():
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.13"}
    request.client.host = "10.10.4.9"

    assert get_client_ip(request, "10.10.0.0/16") == "203.0.113.13"


def test_bounded_rate_limiter_evicts_oldest_client_bucket():
    limiter = BoundedWindowRateLimiter(max_clients=2)

    assert limiter.is_limited("client-a", limit=10, window_seconds=60) is False
    assert limiter.is_limited("client-b", limit=10, window_seconds=60) is False
    assert limiter.is_limited("client-c", limit=10, window_seconds=60) is False

    assert list(limiter.attempts.keys()) == ["client-b", "client-c"]
