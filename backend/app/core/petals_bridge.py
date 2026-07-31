"""Petals bridge (CF-335 P0): consented donors as identity-pinned Pi endpoints.

Design: comparison-Istara-pi/2026-07-31-pi-petals-a2a-bridge-design.md.

The bridge is the data-plane shim that lets the Pi engine orchestrate donated
(petals-style) compute WITHOUT pi-ai learning the donor topology: each consented,
healthy donor node is projected into the PiModelManager catalog as an
identity-pinned ``pi-petals-<node_id>`` endpoint whose ``base_url`` is this app's
loopback shim route. pi-ai keeps its outbound-HTTP world; the shim owns the
reverse-websocket impedance mismatch.

Isolation contract (do not weaken):

- This module lives OUTSIDE ``pi_runtime`` — the invariant "pi_runtime never
  imports or mutates the ComputeRegistry" stays intact
  (``tests/pi_production/test_same_model_donor_isolation.py`` must stay green).
- Only ``source in {"relay", "browser"}`` nodes with explicit ``pi_served``
  consent and current health are ever projected or served. ``pi_served``
  defaults to False on every node.
- Fail-closed: unknown node, non-donor node, unconsented node, or unhealthy node
  -> :class:`PetalsUnavailable` -> HTTP 503 with ``error.type=petals_unavailable``.
  There is NEVER a silent fallback to a paid API route.
- Every response stamps ``_istara_route.route_kind="petals_bridge"`` so reports
  can always separate donated from API traffic.
- Projection is one-directional (registry -> read-only catalog entries); nothing
  here writes back to the registry, donors, or settings.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.config import settings

DONOR_SOURCES = ("relay", "browser")
PETALS_ROUTE_KIND = "petals_bridge"


class PetalsUnavailable(RuntimeError):
    """Typed fail-closed error: the requested petals route cannot serve."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"petals_unavailable:{reason}")


def endpoint_id_for(node_id: str) -> str:
    return f"pi-petals-{node_id}"


def node_id_for(endpoint_id: str) -> str:
    if not endpoint_id.startswith("pi-petals-"):
        raise PetalsUnavailable(f"not_a_petals_endpoint:{endpoint_id!r}")
    return endpoint_id.removeprefix("pi-petals-")


def _registry() -> Any:
    from app.core.llm_router import llm_router  # lazy: keeps import light

    return llm_router


def _is_servable(node: Any) -> bool:
    return (
        node is not None
        and getattr(node, "source", None) in DONOR_SOURCES
        and bool(getattr(node, "pi_served", False))
        and bool(getattr(node, "is_healthy", False))
    )


def consented_donor_nodes() -> list[Any]:
    """Healthy, consented donor nodes, in stable id order (projection source)."""
    registry = _registry()
    nodes = [
        node
        for node in getattr(registry, "_nodes", {}).values()
        if _is_servable(node)
    ]
    return sorted(nodes, key=lambda n: n.node_id)


def catalog_entries() -> list[dict[str, Any]]:
    """One-directional projection: donors -> PiModelManager catalog entry dicts.

    Entries are plain dicts (the model manager coerces them into its endpoint
    type) so this module never imports pi_runtime.
    """
    if not settings.petals_bridge_enabled:
        return []
    entries = []
    for node in consented_donor_nodes():
        models = list(getattr(node, "loaded_models", []) or [])
        entries.append({
            "endpoint_id": endpoint_id_for(node.node_id),
            "provider_kind": "openai_compat",
            "base_url": f"http://127.0.0.1:{getattr(settings, 'port', 8000)}{settings.petals_bridge_base_path}",
            "model": models[0] if models else "default",
            "kind": "petals",
            "node_id": node.node_id,
            "cost_class": "donated",
        })
    return entries


async def chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
    """Serve one OpenAI-shaped chat completion through a pinned donor node.

    The ``model`` field carries the petals endpoint identity (``pi-petals-<node>``
    or a bare node id); the route is pinned to exactly that node — never
    re-scheduled through registry capacity scoring.
    """
    started = time.perf_counter()
    requested = str(payload.get("model") or "")
    node_id = node_id_for(requested) if requested.startswith("pi-petals-") else requested
    registry = _registry()
    node = getattr(registry, "_nodes", {}).get(node_id)
    if node is None:
        raise PetalsUnavailable(f"unknown_node:{node_id}")
    if getattr(node, "source", None) not in DONOR_SOURCES:
        raise PetalsUnavailable(f"not_a_donor:{node_id}")
    if not bool(getattr(node, "pi_served", False)):
        raise PetalsUnavailable(f"donor_not_consented:{node_id}")
    if not bool(getattr(node, "is_healthy", False)):
        raise PetalsUnavailable(f"donor_unhealthy:{node_id}")

    messages = list(payload.get("messages") or [])
    if not messages:
        raise PetalsUnavailable("empty_messages")
    served_model = payload.get("served_model") or (
        list(getattr(node, "loaded_models", []) or ["default"])[0]
    )
    data = await node.chat(
        messages,
        model=served_model,
        temperature=float(payload.get("temperature", 0.7)),
        max_tokens=payload.get("max_tokens"),
        project_id=payload.get("project_id"),
    )

    message = (data.get("message") or {}) if isinstance(data, dict) else {}
    content = message.get("content", "") or ""
    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict) or not usage:
        # Donors rarely report usage; estimate honestly and mark it.
        usage = {
            "prompt_tokens": max(1, sum(len(str(m.get("content", ""))) for m in messages) // 4),
            "completion_tokens": max(1, len(content) // 4),
            "estimate": True,
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    else:
        usage = dict(usage)
        usage.setdefault("estimate", False)

    return {
        "id": f"chatcmpl-petals-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested or endpoint_id_for(node_id),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": message.get("finish_reason") or data.get("finish_reason") or "stop",
        }],
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "_istara_route": {
            "node_id": node_id,
            "node_source": getattr(node, "source", ""),
            "route_kind": PETALS_ROUTE_KIND,
            "model": served_model,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "usage_estimate": bool(usage.get("estimate")),
        },
    }
