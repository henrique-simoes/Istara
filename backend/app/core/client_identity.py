"""Client identity helpers for proxy-aware request controls."""

from __future__ import annotations

import time
from collections import OrderedDict
from ipaddress import ip_address, ip_network

from fastapi import Request


def get_client_ip(request: Request, trusted_proxy_hosts: str = "") -> str:
    """Return the best-effort client IP for request controls.

    Istara deployments may sit behind Caddy, Nginx, or another reverse proxy.
    In that topology ``request.client.host`` is often the proxy IP, which would
    collapse all users into the same rate-limit bucket.

    Forwarded headers are only honored when the immediate socket peer is in the
    configured trusted proxy allowlist. Direct clients can otherwise spoof
    ``X-Forwarded-For`` to evade login or invite-validation limits.
    """
    socket_host = request.client.host if request.client else "unknown"
    headers = request.headers if hasattr(request, "headers") else {}

    if _is_trusted_proxy(socket_host, trusted_proxy_hosts):
        forwarded = headers.get("x-forwarded-for", "")
        if isinstance(forwarded, str) and forwarded:
            first_ip = forwarded.split(",")[0].strip()
            if first_ip:
                return first_ip

        real_ip = headers.get("x-real-ip", "")
        if isinstance(real_ip, str) and real_ip.strip():
            return real_ip.strip()

    return socket_host


def _is_trusted_proxy(socket_host: str, trusted_proxy_hosts: str) -> bool:
    """Return true when socket_host matches an exact host or CIDR allowlist."""
    if not socket_host or socket_host == "unknown":
        return False

    for raw_entry in trusted_proxy_hosts.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        if entry == "*":
            return True
        if entry == socket_host:
            return True
        try:
            host_ip = ip_address(socket_host)
            if "/" in entry and host_ip in ip_network(entry, strict=False):
                return True
            if "/" not in entry and host_ip == ip_address(entry):
                return True
        except ValueError:
            continue
    return False


class BoundedWindowRateLimiter:
    """Small in-memory fixed-window limiter with bounded client buckets."""

    def __init__(self, *, max_clients: int = 4096):
        self.max_clients = max_clients
        self.attempts: OrderedDict[str, list[float]] = OrderedDict()

    def is_limited(self, client_id: str, *, limit: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        attempts = [ts for ts in self.attempts.get(client_id, []) if ts >= window_start]
        attempts.append(now)
        self.attempts[client_id] = attempts
        self.attempts.move_to_end(client_id)
        self._evict_empty(window_start)
        while len(self.attempts) > self.max_clients:
            self.attempts.popitem(last=False)
        return len(attempts) > limit

    def clear(self) -> None:
        self.attempts.clear()

    def _evict_empty(self, window_start: float) -> None:
        for client_id in list(self.attempts.keys()):
            attempts = [ts for ts in self.attempts[client_id] if ts >= window_start]
            if attempts:
                self.attempts[client_id] = attempts
            else:
                self.attempts.pop(client_id, None)
