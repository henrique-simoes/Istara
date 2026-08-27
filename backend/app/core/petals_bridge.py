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

import secrets
import time
import uuid
from typing import Any
from urllib.parse import quote

from app.config import settings

DONOR_SOURCES = ("relay", "browser")
PETALS_ROUTE_KIND = "petals_bridge"
_BRIDGE_TOKEN = secrets.token_urlsafe(32)


class PetalsUnavailable(RuntimeError):  # noqa: N818 - public bridge protocol name
    """Typed fail-closed error: the requested petals route cannot serve."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"petals_unavailable:{reason}")


def endpoint_id_for(node_id: str) -> str:
    return f"pi-petals-{node_id}"


def bridge_token() -> str:
    """Return the process-private credential used only by the Pi loopback hop."""
    return _BRIDGE_TOKEN


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
    nodes = [node for node in getattr(registry, "_nodes", {}).values() if _is_servable(node)]
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
        entries.append(
            {
                "endpoint_id": endpoint_id_for(node.node_id),
                "provider_kind": "openai_compat",
                "base_url": (
                    f"http://127.0.0.1:{getattr(settings, 'port', 8000)}"
                    f"{settings.petals_bridge_base_path}/nodes/{quote(node.node_id, safe='')}"
                ),
                "api_key": bridge_token(),
                "model": models[0] if models else "default",
                "kind": "petals",
                "node_id": node.node_id,
                "allowed_project_ids": tuple(
                    str(project_id).strip()
                    for project_id in (getattr(node, "allowed_project_ids", []) or [])
                    if str(project_id).strip()
                ),
                "cost_class": "donated",
            }
        )
    return entries


def _admit(
    payload: dict[str, Any],
    *,
    pinned_node_id: str | None = None,
    project_id: str | None = None,
) -> tuple[Any, str, list[dict], str]:
    """Shared admission: resolve the pinned node and enforce the fail-closed rules."""
    requested = str(payload.get("model") or "")
    node_id = pinned_node_id or (
        node_id_for(requested) if requested.startswith("pi-petals-") else requested
    )
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
    effective_project = project_id if project_id is not None else payload.get("project_id")
    purpose = str(payload.get("purpose") or "").strip().lower()
    if purpose.startswith("research") and effective_project is None:
        raise PetalsUnavailable("project_id_required")
    if effective_project is not None:
        requested_project = str(effective_project).strip()
        if not requested_project:
            raise PetalsUnavailable("project_id_required")
        allowed = {
            str(project_id).strip()
            for project_id in (getattr(node, "allowed_project_ids", []) or [])
            if str(project_id).strip()
        }
        if "*" not in allowed and requested_project not in allowed:
            raise PetalsUnavailable(f"donor_project_not_authorized:{node_id}")
    messages = list(payload.get("messages") or [])
    if not messages:
        raise PetalsUnavailable("empty_messages")
    served_model = (
        payload.get("served_model") or (list(getattr(node, "loaded_models", []) or ["default"])[0])
    )
    return node, node_id, messages, served_model


async def chat_completions(
    payload: dict[str, Any],
    *,
    pinned_node_id: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Serve one OpenAI-shaped chat completion through a pinned donor node.

    The ``model`` field carries the petals endpoint identity (``pi-petals-<node>``
    or a bare node id); the route is pinned to exactly that node — never
    re-scheduled through registry capacity scoring.
    """
    started = time.perf_counter()
    requested = str(payload.get("model") or "")
    node, node_id, messages, served_model = _admit(
        payload, pinned_node_id=pinned_node_id, project_id=project_id
    )
    data = await node.chat(
        messages,
        model=served_model,
        temperature=float(payload.get("temperature", 0.7)),
        max_tokens=payload.get("max_tokens"),
        project_id=project_id if project_id is not None else payload.get("project_id"),
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

    await _record_usage_row(
        ({**payload, "project_id": project_id} if project_id is not None else payload),
        node_id=node_id,
        served_model=served_model,
        usage=usage,
        started=started,
    )

    return {
        "id": f"chatcmpl-petals-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested or endpoint_id_for(node_id),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": message.get("finish_reason")
                or data.get("finish_reason")
                or "stop",
            }
        ],
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


async def chat_completions_stream(
    payload: dict[str, Any],
    *,
    pinned_node_id: str | None = None,
    project_id: str | None = None,
):
    """Stream one chat completion as OpenAI-shaped chunk dicts (CF-336 P1).

    Same admission as the non-streaming path. Relay/browser donors currently
    yield a single aggregated chunk (the node falls back to non-streaming
    internally); the SSE shape stays correct regardless, so pi-ai streaming
    clients work unchanged when donors gain true streaming later.
    """
    started = time.perf_counter()
    requested = str(payload.get("model") or "")
    node, node_id, messages, served_model = _admit(
        payload, pinned_node_id=pinned_node_id, project_id=project_id
    )
    chunk_id = f"chatcmpl-petals-{uuid.uuid4().hex[:24]}"
    # Donor nodes are relay/browser resources.  Use the node's non-streaming
    # contract for this compatibility shim: it preserves provider usage and
    # route evidence, while this function still emits a valid two-chunk SSE
    # sequence to the Pi OpenAI client.  Calling ``chat_stream`` here would
    # discard the provider's terminal usage receipt at the generic node seam.
    data = await node.chat(
        messages,
        model=served_model,
        temperature=float(payload.get("temperature", 0.7)),
        max_tokens=payload.get("max_tokens"),
        project_id=project_id if project_id is not None else payload.get("project_id"),
    )
    message = (data.get("message") or {}) if isinstance(data, dict) else {}
    text = str(message.get("content", "") or "")
    if text:
        yield {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": requested or endpoint_id_for(node_id),
            "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
        }
    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict) or not usage:
        usage = {
            "prompt_tokens": max(1, sum(len(str(m.get("content", ""))) for m in messages) // 4),
            "completion_tokens": max(1, len(text) // 4),
            "estimate": True,
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    else:
        usage = dict(usage)
        usage.setdefault("estimate", False)
    await _record_usage_row(
        ({**payload, "project_id": project_id} if project_id is not None else payload),
        node_id=node_id,
        served_model=served_model,
        usage=usage,
        started=started,
    )
    yield {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": requested or endpoint_id_for(node_id),
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "_istara_route": {
            "node_id": node_id,
            "node_source": getattr(node, "source", ""),
            "route_kind": PETALS_ROUTE_KIND,
            "model": served_model,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "streamed_chars": len(text),
            "usage_estimate": bool(usage.get("estimate")),
        },
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def set_donor_consent(node_id: str, pi_served: bool) -> dict[str, Any]:
    """Admin-managed consent flip (CF-336 P1). Returns the resulting state."""
    registry = _registry()
    node = getattr(registry, "_nodes", {}).get(node_id)
    if node is None:
        raise PetalsUnavailable(f"unknown_node:{node_id}")
    if getattr(node, "source", None) not in DONOR_SOURCES:
        raise PetalsUnavailable(f"not_a_donor:{node_id}")
    node.pi_served = bool(pi_served)
    try:
        from app.core.pi_runtime.model_manager import reset_live_db_projections

        reset_live_db_projections()
    except Exception:
        # Consent is enforced again at dispatch, so catalog invalidation is an
        # availability refresh rather than the security boundary.
        pass
    return {
        "node_id": node_id,
        "source": getattr(node, "source", ""),
        "pi_served": node.pi_served,
        "is_healthy": bool(getattr(node, "is_healthy", False)),
    }


def bridge_status() -> dict[str, Any]:
    """Bridge-visible donor inventory (consent + serve state)."""
    registry = _registry()
    donors = []
    for node in sorted(getattr(registry, "_nodes", {}).values(), key=lambda n: n.node_id):
        if getattr(node, "source", None) not in DONOR_SOURCES:
            continue
        donors.append(
            {
                "node_id": node.node_id,
                "source": getattr(node, "source", ""),
                "pi_served": bool(getattr(node, "pi_served", False)),
                "is_healthy": bool(getattr(node, "is_healthy", False)),
                "models": list(getattr(node, "loaded_models", []) or []),
                "endpoint_id": endpoint_id_for(node.node_id) if _is_servable(node) else None,
            }
        )
    return {"enabled": settings.petals_bridge_enabled, "donors": donors}


async def _record_usage_row(
    payload: dict[str, Any],
    *,
    node_id: str,
    served_model: str,
    usage: dict[str, Any],
    started: float,
    error_type: str | None = None,
) -> None:
    """One usage-ledger row per bridge dispatch (CF-337 P2, dispatcher §5.5 contract).

    engine="pi" because all bridge traffic is Pi-engine traffic (DEC-11: donors can
    see the serving engine through these rows); estimate flag propagates from the
    bridge's usage honesty rules; cost stays 0 (donated) — rows are accounting
    evidence, never billing. Fail-soft inside record_agentic_usage.
    """
    try:
        from app.core.agentic.usage_ledger import record_agentic_usage

        await record_agentic_usage(
            engine="pi",
            purpose=str(payload.get("purpose") or "petals_bridge"),
            project_id=str(payload.get("project_id") or ""),
            agent_id=str(payload.get("agent_id") or "pi-petals"),
            outcome={"usage": usage},
            model=served_model,
            started_at=started,
            node_id=node_id,
            error_type=error_type,
        )
    except Exception:  # pragma: no cover - telemetry is never load-bearing
        pass


def build_petals_capabilities() -> dict[str, Any]:
    """A2A agent-card capability section for consented donors (CF-337 P2).

    Content-free: node ids, endpoint identities, models, cost class, consent and
    health — never hosts, prompts, or secrets.
    """
    if not settings.petals_bridge_enabled:
        return {}
    donors = bridge_status()["donors"]
    return {
        "petals": [
            {
                "id": f"compute.petals.{d['node_id']}",
                "endpoint_id": d["endpoint_id"],
                "models": d["models"],
                "cost_class": "donated",
                "consent": "pi_served" if d["pi_served"] else "none",
                "healthy": d["is_healthy"],
                "engine_visibility": True,  # DEC-11: donors see the serving engine
            }
            for d in donors
        ]
    }
