"""Version-proof FastAPI route enumeration.

FastAPI >= 0.141 defers include_router into lazy `_IncludedRouter` wrappers
whose `.path` is "" until materialized, and whose nested routers carry their
include prefix separately. Introspection code that scans `app.routes`
directly silently misses every included route on those versions.

Use `iter_route_paths(app)` (HTTP + WebSocket paths, prefixes applied).
"""

from __future__ import annotations

from collections.abc import Iterator


def _unwrap(routes, prefix: str = "") -> Iterator[tuple[object, str]]:
    for route in routes:
        original = getattr(route, "original_router", None)
        ctx = getattr(route, "include_context", None)
        if original is not None:
            sub_prefix = prefix + (getattr(ctx, "prefix", "") or "")
            yield from _unwrap(getattr(original, "routes", []), sub_prefix)
        else:
            yield route, prefix + getattr(route, "path", "")


def iter_route_paths(app) -> set[str]:
    """All registered paths (HTTP and WebSocket), include prefixes applied."""
    return {path for _, path in _unwrap(getattr(app, "routes", [])) if path}
