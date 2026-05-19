"""Compute registry node lifecycle, health, and status management."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings
from app.core.compute_node import ComputeNode
from app.core.compute_registry_helpers import (
    TRANSIENT_CHAT_BASE_DELAY_S,
    TRANSIENT_CHAT_MAX_ATTEMPTS,
    TRANSIENT_CHAT_MAX_DELAY_S,
    TRANSIENT_HTTP_STATUS_CODES,
    _hydrate_local_resources,
    _looks_like_context_length_error,
    _looks_like_model_availability_error,
    _positive_number,
    _redacted_endpoint_for_log,
    _server_endpoint_identity,
    _unique_model_names,
)
from app.core.llm_output import ThinkingContentFilter, visible_assistant_content
from app.core.llm_thinking import apply_thinking_control
from app.core.token_counter import count_tokens

logger = logging.getLogger("app.core.compute_registry")

class ComputeRegistryLifecycleMixin:
    def __init__(self):
        self._nodes: dict[str, ComputeNode] = {}
        # LLMRouter used ``_servers`` — point it at the same dict so that
        # code like ``llm_router._servers.values()`` keeps working.
        self._servers = self._nodes
        self._health_task: asyncio.Task | None = None
        self._chat_ready_cache: dict[str, tuple[float, bool]] = {}

    def _invalidate_chat_ready_cache(self) -> None:
        self._chat_ready_cache.clear()

    # ================================================================
    # LLM Availability (Circuit Breaker Integration)
    # ================================================================

    def has_available_node(self) -> bool:
        """Check if at least one compute node is available for LLM calls."""
        return bool(self._select_candidates())

    async def broadcast_llm_status(self, status: str, detail: str = "") -> None:
        """Broadcast LLM availability changes to frontend."""
        try:
            from app.api.websocket import manager as ws_manager

            await ws_manager.broadcast(status, {"message": detail})
        except Exception:
            pass

    # ================================================================
    # Node Management
    # ================================================================

    def register_node(self, node: ComputeNode) -> None:
        """Register a ComputeNode."""
        _hydrate_local_resources(node)
        if node.host:
            new_identity = _server_endpoint_identity(node.host, source=node.source)
            for existing_id, existing in list(self._nodes.items()):
                if existing_id == node.node_id or not existing.host:
                    continue
                if _server_endpoint_identity(existing.host, source=existing.source) != new_identity:
                    continue
                if self._should_keep_duplicate_node(existing, node):
                    self._merge_duplicate_node(existing, node)
                    logger.info(
                        "ComputeRegistry: skipped duplicate node '%s' (%s @ %s); "
                        "existing node '%s' already owns that endpoint as %s.",
                        node.name,
                        node.provider_type,
                        _redacted_endpoint_for_log(node.host),
                        existing.name,
                        existing.provider_type,
                    )
                    return
                self._merge_duplicate_node(node, existing)
                removed = self._nodes.pop(existing_id, None)
                if removed:
                    asyncio.ensure_future(removed.close())
                    logger.info(
                        "ComputeRegistry: replaced duplicate node '%s' (%s) with '%s' (%s).",
                        removed.name,
                        removed.provider_type,
                        node.name,
                        node.provider_type,
                    )
        if not node.connected_at:
            node.connected_at = time.time()
        if not node.last_heartbeat:
            node.last_heartbeat = time.time()
        self._nodes[node.node_id] = node
        self._invalidate_chat_ready_cache()
        logger.info(
            "ComputeRegistry: registered %s node '%s' (%s)",
            node.source,
            node.name,
            _redacted_endpoint_for_log(node.host),
        )

    @staticmethod
    def _duplicate_source_rank(node: ComputeNode) -> int:
        if node.source == "local":
            return 30
        if node.source in {"relay", "browser"}:
            return 20
        if node.source == "network":
            return 10
        return 0

    @classmethod
    def _should_keep_duplicate_node(
        cls,
        existing: ComputeNode,
        incoming: ComputeNode,
    ) -> bool:
        existing_rank = cls._duplicate_source_rank(existing)
        incoming_rank = cls._duplicate_source_rank(incoming)
        if existing_rank != incoming_rank:
            return existing_rank > incoming_rank
        return existing.priority <= incoming.priority

    @staticmethod
    def _merge_duplicate_node(target: ComputeNode, incoming: ComputeNode) -> None:
        """Preserve useful runtime metadata when duplicate endpoints collapse."""
        target.loaded_models = _unique_model_names(
            tuple(list(target.loaded_models or []) + list(incoming.loaded_models or []))
        )
        if incoming.model_capabilities:
            target.model_capabilities = {
                **incoming.model_capabilities,
                **target.model_capabilities,
            }
        if incoming.is_healthy and not target.is_healthy:
            target.is_healthy = True
            target.health_state = incoming.health_state
            target.health_error = incoming.health_error
        for field in ("ram_total_gb", "ram_available_gb", "cpu_cores", "gpu_vram_mb"):
            if not getattr(target, field, 0) and getattr(incoming, field, 0):
                setattr(target, field, getattr(incoming, field))
        if not target.gpu_name and incoming.gpu_name:
            target.gpu_name = incoming.gpu_name
        if not target.provider_host and incoming.provider_host:
            target.provider_host = incoming.provider_host
        if not target.ip_address and incoming.ip_address:
            target.ip_address = incoming.ip_address
        if incoming.last_heartbeat > target.last_heartbeat:
            target.last_heartbeat = incoming.last_heartbeat

    def register_server(self, entry) -> None:
        """Backward compat: accepts LLMServerEntry-like objects.

        Converts them to ComputeNode so the registry is the single store.
        """
        node = ComputeNode(
            node_id=getattr(entry, "server_id", str(id(entry))),
            name=getattr(entry, "name", "Unknown"),
            host=getattr(entry, "host", "").rstrip("/"),
            source="local" if getattr(entry, "is_local", False) else "network",
            provider_type=getattr(entry, "provider_type", "lmstudio"),
            priority=getattr(entry, "priority", 10),
            is_local=getattr(entry, "is_local", False),
            api_key=getattr(entry, "api_key", ""),
            is_relay=getattr(entry, "is_relay", False),
            is_healthy=getattr(entry, "is_healthy", False),
            latency_ms=getattr(entry, "last_latency_ms", 0),
            loaded_models=list(getattr(entry, "available_models", [])),
            model_capabilities=dict(getattr(entry, "model_capabilities", {})),
        )
        self.register_node(node)

    def remove_node(self, node_id: str) -> None:
        node = self._nodes.pop(node_id, None)
        if node:
            self._invalidate_chat_ready_cache()
            asyncio.ensure_future(node.close())
            logger.info(f"ComputeRegistry: removed node '{node.name}'")

    # Backward compat aliases
    def unregister_server(self, server_id: str) -> None:
        self.remove_node(server_id)

    def unregister_node(self, node_id: str) -> None:
        self.remove_node(node_id)

    def remove_duplicate_network_nodes(self, relay_node: ComputeNode) -> None:
        """Remove network-discovered nodes that point to the same LLM
        provider as a newly registered relay node.  The relay is the
        preferred connection path, so keeping both is confusing."""
        if not relay_node.host:
            return
        from urllib.parse import urlparse

        relay_parsed = urlparse(relay_node.host)
        relay_key = (relay_parsed.hostname, relay_parsed.port)

        to_remove = []
        for nid, n in list(self._nodes.items()):
            if n.source != "network":
                continue
            n_parsed = urlparse(n.host)
            if (n_parsed.hostname, n_parsed.port) == relay_key:
                # Same machine — transfer capabilities before removing
                if n.model_capabilities and not relay_node.model_capabilities:
                    relay_node.model_capabilities = dict(n.model_capabilities)
                to_remove.append(nid)
        for nid in to_remove:
            name = self._nodes[nid].name
            self.remove_node(nid)
            logger.info(
                f"ComputeRegistry: removed duplicate network node "
                f"'{name}' (covered by relay '{relay_node.name}')"
            )

    def update_heartbeat(self, node_id: str, stats: dict) -> None:
        node = self._nodes.get(node_id)
        if not node:
            return
        ram_total = _positive_number(stats.get("ram_total_gb"))
        ram_available = _positive_number(stats.get("ram_available_gb"))
        cpu_cores = int(_positive_number(stats.get("cpu_cores")))
        gpu_vram_mb = int(_positive_number(stats.get("gpu_vram_mb")))
        if ram_total:
            node.ram_total_gb = ram_total
        if ram_available:
            node.ram_available_gb = ram_available
        if cpu_cores:
            node.cpu_cores = cpu_cores
        if gpu_vram_mb:
            node.gpu_vram_mb = gpu_vram_mb
        if stats.get("gpu_name"):
            node.gpu_name = str(stats["gpu_name"])
        node.cpu_load_pct = stats.get("cpu_load_pct", node.cpu_load_pct)
        node.loaded_models = stats.get("loaded_models", node.loaded_models)
        model_capabilities = stats.get("model_capabilities")
        if isinstance(model_capabilities, dict):
            node.model_capabilities = {**node.model_capabilities, **model_capabilities}
        node.state = stats.get("state", node.state)
        health_error = stats.get("health_error") or stats.get("llm_probe_error") or ""
        if health_error:
            node.health_error = str(health_error)[:200]
            node.health_state = "no_model_server" if not node.loaded_models else "degraded"
        elif node.loaded_models or node.model_capabilities:
            node.health_error = ""
            node.health_state = "ready"
        node.last_heartbeat = time.time()
        node.is_healthy = True
        self._invalidate_chat_ready_cache()

    # ================================================================
    # Health Checking
    # ================================================================

    async def check_all_health(self) -> dict[str, bool]:
        """Check health of all nodes and detect model capabilities.

        Returns a dict mapping node_id -> is_healthy (backward compat
        with LLMRouter.check_all_health).
        """
        results: dict[str, bool] = {}
        for nid, node in list(self._nodes.items()):
            if node.source in ("relay", "browser"):
                # Relay/browser health is based on heartbeat timeout. Browser
                # donors are not reachable by backend HTTP, so cached models and
                # websocket liveness are the source of truth.
                if node.last_heartbeat and (time.time() - node.last_heartbeat) > 90:
                    node.is_healthy = False
                    node.health_state = "unhealthy"
                results[nid] = node.is_healthy
                # Detect capabilities for healthy relay nodes via HTTP
                # to their resolved provider address.
                if (
                    node.source == "relay"
                    and node.is_healthy
                    and not node.model_capabilities
                    and node.host
                ):
                    try:
                        from app.core.model_capabilities import detect_capabilities_generic

                        caps = await detect_capabilities_generic(
                            node.host,
                            api_key=node.api_key,
                            provider_type=node.provider_type,
                            active_probe=False,
                        )
                        detected = {k: v.to_dict() for k, v in caps.items()}
                        node.model_capabilities = {**node.model_capabilities, **detected}
                        logger.info(
                            f"Detected capabilities for relay {node.name}: "
                            f"{len(node.model_capabilities)} models"
                        )
                    except Exception as e:
                        logger.debug(f"Relay capability detection failed for {node.name}: {e}")
                continue

            # HTTP-based health check
            healthy = await node.check_health()
            results[nid] = healthy

            # Detect capabilities for online nodes, even when LM Studio has no
            # model loaded yet. This is passive metadata discovery; readiness
            # still stays false until chat has a loaded or explicitly loaded model.
            if healthy or node.health_state == "no_model_loaded":
                try:
                    from app.core.model_capabilities import detect_capabilities_generic

                    caps = await detect_capabilities_generic(
                        node.host,
                        api_key=node.api_key,
                        provider_type=node.provider_type,
                        active_probe=False,
                    )
                    detected = {k: v.to_dict() for k, v in caps.items()}
                    node.model_capabilities = {**node.model_capabilities, **detected}

                    # Sync detected context window to global config
                    for model_name, cap in caps.items():
                        if cap.context_length and cap.context_length > 0:
                            from app.config import settings

                            settings.update_context_window(cap.context_length)
                            break  # Use first model with a context length
                except Exception as e:
                    logger.debug(f"Model capability detection failed for {node.name}: {e}")

        return results

    async def health(self) -> bool:
        """True if any node is healthy."""
        return any(n.is_healthy for n in self._nodes.values())

    async def ensure_chat_ready(
        self,
        model: str | None = None,
        *,
        require_vision: bool = False,
        probe_lmstudio: bool = True,
        allow_model_load: bool = True,
        force: bool = False,
        positive_cache_ttl_s: float = 300.0,
        negative_cache_ttl_s: float = 10.0,
        refresh_health: bool = True,
    ) -> bool:
        """Return true only when at least one node can serve the real chat path.

        Health endpoints prove that a server is reachable. Chat readiness also
        accounts for loaded model state, LM Studio's load contract, and the
        same model selection logic used by normal user requests.
        """
        cache_key = (
            f"{model or 'default'}:{require_vision}:{probe_lmstudio}:{allow_model_load}"
        )
        now = time.time()
        cached = self._chat_ready_cache.get(cache_key)
        if not force and cached:
            cached_at, cached_ready = cached
            ttl = positive_cache_ttl_s if cached_ready else negative_cache_ttl_s
            if now - cached_at < ttl:
                return cached_ready

        if refresh_health:
            await self.check_all_health()
        for node in self._select_candidates(
            require_vision=require_vision,
            model=model,
            strict_model=settings.strict_auto_routing,
            include_unhealthy=True,
        ):
            if (
                require_vision
                and model
                and model != "default"
                and not self._node_supports_vision_model(node, model)
            ):
                continue
            try:
                resolved_model = node._resolve_model(model, require_vision=require_vision)
                resolved_model = await self._ensure_node_model_ready(
                    node,
                    resolved_model,
                    require_vision=require_vision,
                    allow_model_load=allow_model_load,
                )
                if probe_lmstudio and node.provider_type == "lmstudio":
                    try:
                        await node.chat(
                            [{"role": "user", "content": "Reply ok."}],
                            model=resolved_model,
                            temperature=0,
                            max_tokens=1,
                        )
                    except Exception as exc:
                        if not _looks_like_model_availability_error(exc):
                            raise
                        recovered = None
                        if allow_model_load:
                            recovered = await self._recover_unloaded_node_model(
                                node,
                                resolved_model,
                                require_vision=require_vision,
                            )
                        if not recovered:
                            raise
                        await node.chat(
                            [{"role": "user", "content": "Reply ok."}],
                            model=recovered,
                            temperature=0,
                            max_tokens=1,
                )
                self._record_success(node)
                self._chat_ready_cache[cache_key] = (time.time(), True)
                return True
            except Exception as exc:
                self._record_failure(node, exc)
                logger.warning(
                    "ComputeRegistry: chat readiness failed on %s: %s",
                    node.name,
                    exc,
                )
        self._chat_ready_cache[cache_key] = (time.time(), False)
        return False

    async def start_health_loop(self, interval: int = 60):
        """Background health check loop."""
        while True:
            try:
                await self.check_all_health()
            except Exception as e:
                logger.error(f"ComputeRegistry health check error: {e}")
            await asyncio.sleep(interval)

    # ================================================================
    # Server listing (backward compat with LLMRouter)
    # ================================================================

    def list_servers(self) -> list[dict]:
        """Backward compat with LLMRouter.list_servers()."""
        return [
            {
                "id": n.node_id,
                "name": n.name,
                "provider_type": n.provider_type,
                "host": n.host,
                "is_local": n.is_local,
                "is_healthy": n.is_healthy,
                "priority": n.priority,
                "last_latency_ms": n.latency_ms,
            }
            for n in sorted(self._nodes.values(), key=lambda n: n.priority)
        ]
