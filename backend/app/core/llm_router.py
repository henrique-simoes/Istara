"""LLM Router — backward compatibility wrapper over ComputeRegistry.

All actual routing is handled by compute_registry. This module exists
so that existing imports like ``from app.core.llm_router import llm_router``
and ``from app.core.llm_router import LLMServerEntry`` continue to work
without changes.

The ``LLMServerEntry`` class is still needed for startup registration code
in ``ollama.py``, ``network_discovery.py``, and ``llm_servers.py``.  When
passed to ``llm_router.register_server(entry)``, it gets converted to a
``ComputeNode`` internally.
"""

from dataclasses import dataclass, field

from app.core.compute_registry import compute_registry


@dataclass
class LLMServerEntry:
    """A registered LLM server (kept for backward compat with startup code).

    Instances of this class are passed to ``llm_router.register_server()``,
    which converts them to ``ComputeNode`` objects inside the unified
    ``ComputeRegistry``.
    """

    server_id: str = ""
    name: str = ""
    host: str = ""
    provider_type: str = "lmstudio"
    api_key: str = ""
    priority: int = 10
    is_local: bool = False
    is_relay: bool = False
    is_healthy: bool = False
    last_latency_ms: float = 0
    available_models: list = field(default_factory=list)
    model_capabilities: dict = field(default_factory=dict)

    async def check_health(self) -> bool:
        """Probe server health — delegates to the registry node."""
        node = compute_registry._nodes.get(self.server_id)
        if node:
            result = await node.check_health()
            # Sync back so callers that read entry attributes get updates
            self.is_healthy = node.is_healthy
            self.last_latency_ms = node.latency_ms
            self.available_models = node.loaded_models
            self.model_capabilities = node.model_capabilities
            return result
        return False

    async def _get_client(self):
        """Get HTTP client — delegates to the registry node."""
        node = compute_registry._nodes.get(self.server_id)
        if node:
            return await node._get_client()
        return None

    async def close(self):
        """Close HTTP client — delegates to the registry node."""
        node = compute_registry._nodes.get(self.server_id)
        if node:
            await node.close()


# The router IS the registry — all methods (chat, chat_stream, embed,
# check_all_health, register_server, _servers, health, etc.) are
# provided by ComputeRegistry.
llm_router = compute_registry
