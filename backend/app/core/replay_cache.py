"""Bounded in-memory replay cache for public ingress endpoints."""

from __future__ import annotations

import time
from collections import OrderedDict


class BoundedReplayCache:
    """Small TTL replay cache with bounded memory usage.

    The cache is intentionally process-local. It is sufficient for Istara's
    local-first runtime and tests, while keeping the API explicit enough to
    replace with Redis or another shared store for horizontally scaled team
    deployments later.
    """

    def __init__(self, *, max_entries: int = 8192) -> None:
        self.max_entries = max_entries
        self._entries: OrderedDict[str, float] = OrderedDict()

    def seen_or_store(self, key: str, *, ttl_seconds: int) -> bool:
        """Return True if *key* has already been seen in the active TTL window."""
        now = time.time()
        self._evict_expired(now, ttl_seconds)
        if key in self._entries:
            self._entries.move_to_end(key)
            return True
        self._entries[key] = now
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        return False

    def clear(self) -> None:
        self._entries.clear()

    def _evict_expired(self, now: float, ttl_seconds: int) -> None:
        cutoff = now - max(1, int(ttl_seconds))
        for key, timestamp in list(self._entries.items()):
            if timestamp >= cutoff:
                break
            self._entries.pop(key, None)
