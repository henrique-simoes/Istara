"""Unified Compute Registry — single source of truth for ALL LLM compute.

Replaces both LLMRouter and ComputePool. All LLM request routing goes
through this registry. If a node isn't registered here, it doesn't exist.

Architecture:
- Local node: auto-registered at startup
- Network nodes: added by network_discovery
- Relay nodes: added by WebSocket connections

Routing: capability filter -> score -> retry 3x -> cooldown -> failover
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ComputeNode:
    """A single compute resource.

    Backward-compatible with LLMServerEntry — exposes the same attribute
    names so code that accesses ``llm_router._servers[id].host`` etc.
    keeps working.
    """

    node_id: str
    name: str
    host: str
    source: str  # "local" | "network" | "relay" | "browser"
    provider_type: str  # "lmstudio" | "ollama" | "openai_compat"

    # Health
    is_healthy: bool = False
    health_state: str = "unknown"
    health_error: str = ""
    last_health_check: float = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0

    # Hardware
    ram_total_gb: float = 0
    ram_available_gb: float = 0
    cpu_cores: int = 0
    cpu_load_pct: float = 0
    gpu_name: str = ""
    gpu_vram_mb: int = 0

    # Models
    loaded_models: list = field(default_factory=list)
    model_capabilities: dict = field(default_factory=dict)

    # Routing
    priority: int = 10
    latency_ms: float = 0
    active_requests: int = 0
    is_local: bool = False
    is_relay: bool = False

    # Connection (relay nodes)
    websocket: Any = None
    last_heartbeat: float = 0

    # Relay-specific fields (backward compat with RelayNode)
    user_id: str = ""
    ip_address: str = ""
    provider_host: str = ""
    state: str = "idle"
    priority_level: int = 3
    connected_at: float = 0

    # LLM client (cached)
    _client: Any = None
    api_key: str = ""

    # --- Backward-compatibility aliases for LLMServerEntry ---

    @property
    def server_id(self) -> str:
        return self.node_id

    @property
    def last_latency_ms(self) -> float:
        return self.latency_ms

    @last_latency_ms.setter
    def last_latency_ms(self, value: float) -> None:
        self.latency_ms = value

    @property
    def available_models(self) -> list:
        return self.loaded_models

    @available_models.setter
    def available_models(self, value: list) -> None:
        self.loaded_models = value

    @property
    def hostname(self) -> str:
        return self.name

    def score(self) -> float:
        if not self.is_healthy:
            return -1
        if self.health_state == "cooldown" and time.time() < self.cooldown_until:
            return -1
        s = 100.0
        s -= self.active_requests * 15
        if self.latency_ms:
            s -= min(self.latency_ms / 10, 30)
        s -= self.priority
        if self.ram_available_gb:
            s += min(self.ram_available_gb * 2, 20)
        return s

    def is_alive(self, timeout: float = 90) -> bool:
        """Backward compat with RelayNode.is_alive()."""
        if self.source == "relay":
            return self.last_heartbeat > 0 and (time.time() - self.last_heartbeat) < timeout
        return self.is_healthy

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client for this node."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.host, timeout=300.0, headers=headers
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def check_health(self) -> bool:
        """Probe the server health endpoint and discover available models.

        Backward compat with LLMServerEntry.check_health().
        """
        try:
            client = await self._get_client()
            start = time.time()
            if self.provider_type == "ollama":
                resp = await client.get("/api/tags", timeout=10.0)
            else:
                resp = await client.get("/v1/models", timeout=10.0)
            self.latency_ms = (time.time() - start) * 1000
            self.is_healthy = resp.status_code == 200
            if self.is_healthy:
                try:
                    data = resp.json()
                    if self.provider_type == "ollama":
                        self.loaded_models = [m.get("name", "") for m in data.get("models", [])]
                    else:
                        self.loaded_models = [m.get("id", "") for m in data.get("data", [])]
                except Exception:
                    pass
                self.health_state = "ready"
                self.health_error = ""
                self.consecutive_failures = 0
                self.last_health_check = time.time()
            elif resp.status_code in (401, 403):
                # Auth failure — server requires an API key
                self.health_state = "auth_required"
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("error", {})
                    if isinstance(err_msg, dict):
                        self.health_error = err_msg.get("message", "API key required")
                    else:
                        self.health_error = str(err_msg) or "API key required"
                except Exception:
                    self.health_error = "API key required by this server"
            else:
                self.health_state = "unhealthy"
                self.health_error = f"Server returned HTTP {resp.status_code}"
        except httpx.ConnectError:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "unreachable"
            self.health_error = "Cannot connect — check the host URL"
        except httpx.TimeoutException:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "timeout"
            self.health_error = "Connection timed out"
        except Exception as e:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "unhealthy"
            self.health_error = str(e)[:200] if str(e) else "Unknown error"
        return self.is_healthy

    def _resolve_model(self, model: str | None) -> str:
        """Resolve the model name — use what's available on this node."""
        models = self.loaded_models or []
        non_embed = [m for m in models if "embed" not in m.lower()]

        if model and model != "default":
            if models and model not in models:
                if non_embed:
                    return non_embed[0]
            return model
        if non_embed:
            return non_embed[0]
        if self.provider_type == "ollama":
            return settings.ollama_model
        return settings.lmstudio_model

    def _resolve_embed_model(self, model: str | None) -> str:
        """Resolve embedding model — prefer embedding-specific models."""
        if model and model != "default":
            return model
        if self.loaded_models:
            embed_models = [m for m in self.loaded_models if "embed" in m.lower()]
            if embed_models:
                return embed_models[0]
        if self.provider_type == "ollama":
            return settings.ollama_embed_model
        return settings.lmstudio_embed_model

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """Direct chat on this specific node (backward compat with LLMServerEntry.chat)."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]

        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": self._resolve_model(model),
                "messages": msgs,
                "stream": False,
                "options": options,
            }
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
        else:
            payload = {
                "model": self._resolve_model(model),
                "messages": msgs,
                "temperature": temperature,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = tools
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
            result: dict = {
                "message": {
                    "role": "assistant",
                    "content": message.get("content") or "",
                }
            }
            if message.get("tool_calls"):
                result["message"]["tool_calls"] = message["tool_calls"]
                result["finish_reason"] = choice.get("finish_reason", "tool_calls")
            return result

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str | dict, None]:
        """Direct streaming chat on this specific node (backward compat)."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]

        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": model or settings.ollama_model,
                "messages": msgs,
                "stream": True,
                "options": options,
            }
            async with client.stream(
                "POST", "/api/chat", json=payload, timeout=None
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            return
        else:
            payload = {
                "model": self._resolve_model(model),
                "messages": msgs,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = tools

            accumulated_tool_calls: list[dict] = []
            tool_call_mode = False

            async with client.stream(
                "POST", "/v1/chat/completions", json=payload, timeout=None
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish = choice.get("finish_reason")

                        if delta.get("tool_calls"):
                            tool_call_mode = True
                            for tc_delta in delta["tool_calls"]:
                                idx = tc_delta.get("index", 0)
                                while len(accumulated_tool_calls) <= idx:
                                    accumulated_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    })
                                tc = accumulated_tool_calls[idx]
                                if tc_delta.get("id"):
                                    tc["id"] = tc_delta["id"]
                                fn = tc_delta.get("function", {})
                                if fn.get("name"):
                                    tc["function"]["name"] = fn["name"]
                                if fn.get("arguments"):
                                    tc["function"]["arguments"] += fn["arguments"]
                            continue

                        content = delta.get("content", "")
                        if content:
                            yield content

                        if finish == "tool_calls" or (
                            finish == "stop" and tool_call_mode
                        ):
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            if accumulated_tool_calls and any(
                tc["function"]["name"] for tc in accumulated_tool_calls
            ):
                yield {
                    "tool_calls": accumulated_tool_calls,
                    "finish_reason": "tool_calls",
                }

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Direct embedding on this specific node (backward compat)."""
        client = await self._get_client()
        embed_model = self._resolve_embed_model(model)

        if self.provider_type == "ollama":
            resp = await client.post(
                "/api/embed", json={"model": embed_model, "input": text}
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])
            return embeddings[0] if embeddings else []
        else:
            resp = await client.post(
                "/v1/embeddings", json={"model": embed_model, "input": text}
            )
            resp.raise_for_status()
            items = resp.json().get("data", [])
            return items[0].get("embedding", []) if items else []

    async def embed_batch(
        self, texts: list[str], model: str | None = None
    ) -> list[list[float]]:
        """Direct batch embedding on this specific node (backward compat)."""
        client = await self._get_client()
        embed_model = self._resolve_embed_model(model)

        if self.provider_type == "ollama":
            resp = await client.post(
                "/api/embed", json={"model": embed_model, "input": texts}
            )
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
        else:
            resp = await client.post(
                "/v1/embeddings", json={"model": embed_model, "input": texts}
            )
            resp.raise_for_status()
            return [
                item.get("embedding", [])
                for item in resp.json().get("data", [])
            ]

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "hostname": self.name,
            "name": self.name,
            "host": self.host,
            "source": self.source,
            "provider_type": self.provider_type,
            "state": self.health_state,
            "is_healthy": self.is_healthy,
            "is_local": self.is_local,
            "priority": self.priority,
            "latency_ms": self.latency_ms,
            "active_requests": self.active_requests,
            "score": round(self.score(), 1) if self.score() >= 0 else 0,
            "alive": self.is_healthy,
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "cpu_cores": self.cpu_cores,
            "cpu_load_pct": self.cpu_load_pct,
            "gpu_name": self.gpu_name,
            "loaded_models": self.loaded_models,
            "model_capabilities": self.model_capabilities,
        }


class ComputeRegistry:
    """Single source of truth for all compute resources.

    Provides the full interface of both LLMRouter and ComputePool so all
    existing imports keep working via thin wrappers.
    """

    def __init__(self):
        self._nodes: dict[str, ComputeNode] = {}
        # LLMRouter used ``_servers`` — point it at the same dict so that
        # code like ``llm_router._servers.values()`` keeps working.
        self._servers = self._nodes
        self._health_task: asyncio.Task | None = None

    # ================================================================
    # Node Management
    # ================================================================

    def register_node(self, node: ComputeNode) -> None:
        """Register a ComputeNode."""
        if not node.connected_at:
            node.connected_at = time.time()
        if not node.last_heartbeat:
            node.last_heartbeat = time.time()
        self._nodes[node.node_id] = node
        logger.info(
            f"ComputeRegistry: registered {node.source} node "
            f"'{node.name}' ({node.host})"
        )

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
        node.ram_available_gb = stats.get("ram_available_gb", node.ram_available_gb)
        node.cpu_load_pct = stats.get("cpu_load_pct", node.cpu_load_pct)
        node.loaded_models = stats.get("loaded_models", node.loaded_models)
        node.state = stats.get("state", node.state)
        node.last_heartbeat = time.time()
        node.is_healthy = True
        node.health_state = "ready"

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
            if node.source == "relay":
                # Relay health is based on heartbeat timeout
                if node.last_heartbeat and (time.time() - node.last_heartbeat) > 90:
                    node.is_healthy = False
                    node.health_state = "unhealthy"
                results[nid] = node.is_healthy
                # Detect capabilities for healthy relay nodes via HTTP
                # to their resolved provider address.
                if node.is_healthy and not node.model_capabilities and node.host:
                    try:
                        from app.core.model_capabilities import (
                            detect_capabilities_lmstudio,
                            detect_capabilities_ollama,
                        )
                        if node.provider_type == "ollama":
                            caps = await detect_capabilities_ollama(node.host)
                        else:
                            caps = await detect_capabilities_lmstudio(node.host)
                        node.model_capabilities = {
                            k: v.to_dict() for k, v in caps.items()
                        }
                        logger.info(
                            f"Detected capabilities for relay {node.name}: "
                            f"{len(node.model_capabilities)} models"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Relay capability detection failed for {node.name}: {e}"
                        )
                continue

            # HTTP-based health check
            healthy = await node.check_health()
            results[nid] = healthy

            # Detect capabilities for healthy nodes
            if healthy:
                try:
                    from app.core.model_capabilities import (
                        detect_capabilities_lmstudio,
                        detect_capabilities_ollama,
                    )
                    if node.provider_type == "ollama":
                        caps = await detect_capabilities_ollama(node.host)
                    else:
                        caps = await detect_capabilities_lmstudio(node.host)
                    node.model_capabilities = {
                        k: v.to_dict() for k, v in caps.items()
                    }
                except Exception as e:
                    logger.debug(
                        f"Model capability detection failed for {node.name}: {e}"
                    )

        return results

    async def health(self) -> bool:
        """True if any node is healthy."""
        return any(n.is_healthy for n in self._nodes.values())

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

    # ================================================================
    # Request Routing
    # ================================================================

    def _sorted_servers(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
    ) -> list[ComputeNode]:
        """Get nodes sorted by priority (lower = better), healthy first.

        Backward compat with LLMRouter._sorted_servers().
        """
        servers = list(self._nodes.values())
        if require_tools:
            # Nodes with detected tool support
            tool_nodes = [
                s for s in servers
                if any(
                    c.get("supports_tools") for c in s.model_capabilities.values()
                )
            ]
            # Nodes whose capabilities haven't been detected yet —
            # don't exclude them; they may well support tools.
            unknown_nodes = [
                s for s in servers
                if s.is_healthy and not s.model_capabilities
            ]
            filtered = tool_nodes + [
                n for n in unknown_nodes if n not in tool_nodes
            ]
            if filtered:
                servers = filtered
        if require_vision:
            filtered = [
                s for s in servers
                if any(
                    c.get("supports_vision") for c in s.model_capabilities.values()
                )
            ]
            if filtered:
                servers = filtered
        if min_context > 0:
            filtered = [
                s for s in servers
                if any(
                    c.get("context_length", 0) >= min_context
                    for c in s.model_capabilities.values()
                )
            ]
            if filtered:
                servers = filtered
        return sorted(
            servers,
            key=lambda s: (not s.is_healthy, s.priority, s.latency_ms or 999),
        )

    def _select_candidates(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
    ) -> list[ComputeNode]:
        """Get candidate nodes sorted by score, filtered by capabilities."""
        candidates = [n for n in self._nodes.values() if n.score() > 0]

        if require_tools and candidates:
            tool_capable = [
                n for n in candidates
                if any(
                    c.get("supports_tools") for c in n.model_capabilities.values()
                )
            ]
            # Include nodes with unknown capabilities (not yet detected)
            unknown_capable = [
                n for n in candidates
                if not n.model_capabilities and n not in tool_capable
            ]
            combined = tool_capable + unknown_capable
            if combined:
                candidates = combined

        if require_vision and candidates:
            vision_capable = [
                n for n in candidates
                if any(
                    c.get("supports_vision") for c in n.model_capabilities.values()
                )
            ]
            if vision_capable:
                candidates = vision_capable

        candidates.sort(key=lambda n: n.score(), reverse=True)
        return candidates

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        """Clean messages for LLM API compatibility."""
        sanitized = []
        for msg in messages:
            role = msg.get("role", "")

            # Pass through tool-result messages verbatim
            if role == "tool":
                entry: dict = {"role": "tool", "content": str(msg.get("content", ""))}
                if msg.get("tool_call_id"):
                    entry["tool_call_id"] = msg["tool_call_id"]
                sanitized.append(entry)
                continue

            # Pass through assistant messages that carry tool_calls
            if role == "assistant" and msg.get("tool_calls"):
                entry_a: dict = {
                    "role": "assistant",
                    "content": msg.get("content") or "",
                }
                entry_a["tool_calls"] = msg["tool_calls"]
                sanitized.append(entry_a)
                continue

            if role not in ("system", "user", "assistant"):
                continue
            content = msg.get("content")
            if content is None or (isinstance(content, str) and not content.strip()):
                continue
            sanitized.append({"role": role, "content": str(content)})

        # Merge consecutive system messages
        merged: list[dict] = []
        for msg in sanitized:
            if merged and msg["role"] == "system" and merged[-1]["role"] == "system":
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg)
        return merged

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """Route a chat request to the best available node."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for node in self._sorted_servers(require_tools=bool(tools)):
            if not node.is_healthy:
                continue
            resolved_model = node._resolve_model(model)
            logger.info(
                f"ComputeRegistry: routing chat to {node.name} "
                f"({node.host}) model={resolved_model}"
            )
            node.active_requests += 1
            try:
                client = await node._get_client()

                if node.provider_type == "ollama":
                    options: dict = {"temperature": temperature}
                    if max_tokens:
                        options["num_predict"] = max_tokens
                    payload = {
                        "model": resolved_model,
                        "messages": msgs,
                        "stream": False,
                        "options": options,
                    }
                    resp = await client.post("/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    node.consecutive_failures = 0
                    node.health_state = "ready"
                    return data
                else:
                    payload = {
                        "model": resolved_model,
                        "messages": msgs,
                        "temperature": temperature,
                        "stream": False,
                    }
                    if max_tokens:
                        payload["max_tokens"] = max_tokens
                    if tools:
                        payload["tools"] = tools
                    resp = await client.post("/v1/chat/completions", json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                    choice = data["choices"][0]
                    message = choice["message"]

                    result: dict = {
                        "message": {
                            "role": "assistant",
                            "content": message.get("content") or "",
                        }
                    }
                    if message.get("tool_calls"):
                        result["message"]["tool_calls"] = message["tool_calls"]
                        result["finish_reason"] = choice.get(
                            "finish_reason", "tool_calls"
                        )

                    node.consecutive_failures = 0
                    node.health_state = "ready"
                    return result

            except Exception as e:
                logger.warning(
                    f"ComputeRegistry: chat failed on {node.name}: {e}"
                )
                node.consecutive_failures += 1
                if node.consecutive_failures >= 3:
                    node.health_state = "cooldown"
                    node.cooldown_until = time.time() + 60
                    node.is_healthy = False
                else:
                    node.is_healthy = False
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for chat")

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str | dict, None]:
        """Streaming chat -- yields str chunks and dict for tool calls."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for node in self._sorted_servers(require_tools=bool(tools)):
            if not node.is_healthy:
                continue
            resolved_model = node._resolve_model(model)
            logger.info(
                f"ComputeRegistry: routing stream to {node.name} "
                f"({node.host}) model={resolved_model}"
            )
            node.active_requests += 1
            try:
                client = await node._get_client()

                if node.provider_type == "ollama":
                    options: dict = {"temperature": temperature}
                    if max_tokens:
                        options["num_predict"] = max_tokens
                    payload = {
                        "model": resolved_model,
                        "messages": msgs,
                        "stream": True,
                        "options": options,
                    }
                    async with client.stream(
                        "POST", "/api/chat", json=payload, timeout=None
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if line.strip():
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                if data.get("done", False):
                                    break
                else:
                    payload = {
                        "model": resolved_model,
                        "messages": msgs,
                        "temperature": temperature,
                        "stream": True,
                    }
                    if max_tokens:
                        payload["max_tokens"] = max_tokens
                    if tools:
                        payload["tools"] = tools

                    accumulated_tool_calls: list[dict] = []
                    tool_call_mode = False

                    async with client.stream(
                        "POST", "/v1/chat/completions", json=payload, timeout=None
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choice = data.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                finish = choice.get("finish_reason")

                                if delta.get("tool_calls"):
                                    tool_call_mode = True
                                    for tc_delta in delta["tool_calls"]:
                                        idx = tc_delta.get("index", 0)
                                        while len(accumulated_tool_calls) <= idx:
                                            accumulated_tool_calls.append(
                                                {
                                                    "id": "",
                                                    "type": "function",
                                                    "function": {
                                                        "name": "",
                                                        "arguments": "",
                                                    },
                                                }
                                            )
                                        tc = accumulated_tool_calls[idx]
                                        if tc_delta.get("id"):
                                            tc["id"] = tc_delta["id"]
                                        fn = tc_delta.get("function", {})
                                        if fn.get("name"):
                                            tc["function"]["name"] = fn["name"]
                                        if fn.get("arguments"):
                                            tc["function"]["arguments"] += fn[
                                                "arguments"
                                            ]
                                    continue

                                content = delta.get("content", "")
                                if content:
                                    yield content

                                if finish == "tool_calls" or (
                                    finish == "stop" and tool_call_mode
                                ):
                                    break
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue

                    if accumulated_tool_calls and any(
                        tc["function"]["name"] for tc in accumulated_tool_calls
                    ):
                        yield {
                            "tool_calls": accumulated_tool_calls,
                            "finish_reason": "tool_calls",
                        }

                node.consecutive_failures = 0
                node.health_state = "ready"
                return

            except Exception as e:
                logger.warning(
                    f"ComputeRegistry: stream failed on {node.name}: {e}"
                )
                node.consecutive_failures += 1
                if node.consecutive_failures >= 3:
                    node.health_state = "cooldown"
                    node.cooldown_until = time.time() + 60
                    node.is_healthy = False
                else:
                    node.is_healthy = False
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for streaming")

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Route an embedding request."""
        for node in self._sorted_servers():
            if not node.is_healthy:
                continue
            node.active_requests += 1
            try:
                client = await node._get_client()
                embed_model = node._resolve_embed_model(model)

                if node.provider_type == "ollama":
                    resp = await client.post(
                        "/api/embed",
                        json={"model": embed_model, "input": text},
                    )
                else:
                    resp = await client.post(
                        "/v1/embeddings",
                        json={"model": embed_model, "input": text},
                    )

                resp.raise_for_status()
                data = resp.json()

                if node.provider_type == "ollama":
                    embeddings = data.get("embeddings", [])
                    return embeddings[0] if embeddings else []
                else:
                    items = data.get("data", [])
                    return items[0].get("embedding", []) if items else []

            except Exception as e:
                logger.warning(
                    f"ComputeRegistry: embed failed on {node.name}: {e}"
                )
                node.is_healthy = False
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for embedding")

    async def embed_batch(
        self, texts: list[str], model: str | None = None
    ) -> list[list[float]]:
        """Route a batch embedding request."""
        for node in self._sorted_servers():
            if not node.is_healthy:
                continue
            node.active_requests += 1
            try:
                client = await node._get_client()
                embed_model = node._resolve_embed_model(model)

                if node.provider_type == "ollama":
                    resp = await client.post(
                        "/api/embed",
                        json={"model": embed_model, "input": texts},
                    )
                    resp.raise_for_status()
                    return resp.json().get("embeddings", [])
                else:
                    resp = await client.post(
                        "/v1/embeddings",
                        json={"model": embed_model, "input": texts},
                    )
                    resp.raise_for_status()
                    return [
                        item.get("embedding", [])
                        for item in resp.json().get("data", [])
                    ]

            except Exception as e:
                logger.warning(
                    f"ComputeRegistry: embed_batch failed on {node.name}: {e}"
                )
                node.is_healthy = False
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for batch embedding")

    async def list_models(self) -> list[dict]:
        """Aggregate models from all healthy nodes."""
        all_models: list[dict] = []
        for node in self._sorted_servers():
            if not node.is_healthy:
                continue
            try:
                client = await node._get_client()
                if node.provider_type == "ollama":
                    resp = await client.get("/api/tags", timeout=10.0)
                    data = resp.json()
                    models = data.get("models", [])
                else:
                    resp = await client.get("/v1/models", timeout=10.0)
                    data = resp.json()
                    models = [
                        {"name": m.get("id", ""), **m}
                        for m in data.get("data", [])
                    ]
                for m in models:
                    m["_server"] = node.name
                    m["_server_id"] = node.node_id
                all_models.extend(models)
            except Exception:
                pass
        return all_models

    async def list_models_async(self) -> list[dict]:
        """Async alias for list_models (backward compat)."""
        return await self.list_models()

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """Pull model on the first healthy Ollama node."""
        for node in self._sorted_servers():
            if node.is_healthy and node.provider_type == "ollama":
                client = await node._get_client()
                async with client.stream(
                    "POST", "/api/pull", json={"name": model_name}, timeout=None
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.strip():
                            yield json.loads(line)
                return
        yield {"status": "No Ollama server available for model pull."}

    async def ensure_model(self, model_name: str) -> bool:
        """Ensure a model is available, pull if not."""
        models = await self.list_models()
        for m in models:
            name = m.get("name", "")
            if name == model_name or name.startswith(model_name.split(":")[0]):
                return True
        async for _ in self.pull_model(model_name):
            pass
        return True

    async def close(self) -> None:
        """Close all HTTP clients."""
        for node in self._nodes.values():
            await node.close()

    # ================================================================
    # ComputePool backward-compat methods
    # ================================================================

    def alive_nodes(self) -> list[ComputeNode]:
        """Return all alive nodes (backward compat with ComputePool)."""
        return [n for n in self._nodes.values() if n.is_alive()]

    def total_capacity(self) -> int:
        """Total number of alive relay nodes (backward compat with ComputePool)."""
        return len([
            n for n in self._nodes.values()
            if n.source == "relay" and n.is_alive()
        ])

    def available_models_list(self) -> list[str]:
        """All models available across the pool (backward compat)."""
        models: set[str] = set()
        for node in self.alive_nodes():
            models.update(node.loaded_models)
        return sorted(models)

    def best_node_for(self, model: str | None = None) -> ComputeNode | None:
        """Select the best node for a given model (backward compat)."""
        candidates = self.alive_nodes()
        if model:
            candidates = [
                n for n in candidates if model in n.loaded_models
            ] or candidates
        if not candidates:
            return None
        return max(candidates, key=lambda n: n.score())

    # ================================================================
    # Unified Stats
    # ================================================================

    def get_stats(self) -> dict:
        nodes = [n.to_dict() for n in self._nodes.values()]
        alive = sum(1 for n in self._nodes.values() if n.is_healthy)
        all_models: set[str] = set()
        for n in self._nodes.values():
            all_models.update(n.loaded_models or [])
        total_ram = sum(n.ram_total_gb for n in self._nodes.values())
        avail_ram = sum(n.ram_available_gb for n in self._nodes.values())
        total_cpu = sum(n.cpu_cores for n in self._nodes.values())

        if alive >= 8:
            tier = "full_swarm"
        elif alive >= 4:
            tier = "standard"
        elif alive >= 2:
            tier = "conservative"
        elif alive >= 1:
            tier = "minimal"
        else:
            tier = "local_only"

        return {
            "total_nodes": len(nodes),
            "alive_nodes": alive,
            "total_ram_gb": round(total_ram, 1),
            "available_ram_gb": round(avail_ram, 1),
            "total_cpu_cores": total_cpu,
            "available_models": sorted(all_models),
            "swarm_tier": tier,
            "nodes": nodes,
        }

    def get_warnings(self) -> list[dict]:
        warnings = []
        for node in self._nodes.values():
            for model_name, caps in node.model_capabilities.items():
                if "embed" in model_name.lower():
                    continue
                if not caps.get("supports_tools", False):
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} does not support native tool calling. "
                                "Chat will use text-based tools (less reliable)."
                            ),
                            "severity": "medium",
                        }
                    )
                ctx = caps.get("context_length", 4096)
                if ctx < 4096:
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} has a small context window "
                                f"({ctx} tokens). Complex conversations may "
                                "be truncated."
                            ),
                            "severity": "high",
                        }
                    )
                param = caps.get("parameter_count", "")
                if param in ("0.5B", "0.8B", "1B", "1.5B", "2B"):
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} ({param}) is very small for "
                                "research tasks. Consider using a 4B+ model."
                            ),
                            "severity": "low",
                        }
                    )
        return warnings


# Singleton
compute_registry = ComputeRegistry()
