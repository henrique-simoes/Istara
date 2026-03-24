"""Compute Pool — manages relay nodes and distributed LLM capacity.

Tracks connected relay nodes (via WebSocket), their hardware stats,
loaded models, and availability. Provides scoring for optimal node
selection when routing LLM requests.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RelayNode:
    """A connected relay node donating compute."""

    node_id: str
    user_id: str
    hostname: str
    ip_address: str = ""
    ram_total_gb: float = 0
    ram_available_gb: float = 0
    cpu_cores: int = 0
    cpu_load_pct: float = 0
    gpu_name: str = ""
    gpu_vram_mb: int = 0
    loaded_models: list[str] = field(default_factory=list)
    provider_type: str = "ollama"  # ollama | lmstudio
    provider_host: str = ""
    state: str = "idle"  # idle | donating | user_active | disconnected
    priority_level: int = 3  # P0=user chat, P1=user task, P2=agent, P3=bg validation
    last_heartbeat: float = 0
    connected_at: float = 0
    latency_ms: float = 0

    def is_alive(self, timeout: float = 90) -> bool:
        return (time.time() - self.last_heartbeat) < timeout

    def score(self) -> float:
        """Compute a selection score (higher = better)."""
        if not self.is_alive() or self.state == "disconnected":
            return 0
        if self.state == "user_active":
            return 0.1  # Available but user has priority

        model_cap = min(len(self.loaded_models) / 3, 1.0)
        load_score = 1 - (self.cpu_load_pct / 100)
        latency_score = 1 / max(self.latency_ms, 1) * 100
        ram_score = min(self.ram_available_gb / 8, 1.0)

        return (model_cap * 0.4) + (load_score * 0.3) + (latency_score * 0.2) + (ram_score * 0.1)


class ComputePool:
    """Registry of connected relay nodes with capacity tracking."""

    def __init__(self):
        self._nodes: dict[str, RelayNode] = {}

    def register_node(self, node: RelayNode) -> None:
        node.connected_at = time.time()
        node.last_heartbeat = time.time()
        self._nodes[node.node_id] = node
        logger.info(f"Compute pool: node registered — {node.hostname} ({node.node_id})")

    def unregister_node(self, node_id: str) -> None:
        node = self._nodes.pop(node_id, None)
        if node:
            logger.info(f"Compute pool: node disconnected — {node.hostname}")

    def update_heartbeat(self, node_id: str, stats: dict) -> None:
        node = self._nodes.get(node_id)
        if not node:
            return
        node.last_heartbeat = time.time()
        node.ram_available_gb = stats.get("ram_available_gb", node.ram_available_gb)
        node.cpu_load_pct = stats.get("cpu_load_pct", node.cpu_load_pct)
        node.loaded_models = stats.get("loaded_models", node.loaded_models)
        node.state = stats.get("state", node.state)

    def alive_nodes(self) -> list[RelayNode]:
        return [n for n in self._nodes.values() if n.is_alive()]

    def total_capacity(self) -> int:
        """Total number of available compute nodes."""
        return len(self.alive_nodes())

    def available_models(self) -> list[str]:
        """All models available across the compute pool."""
        models: set[str] = set()
        for node in self.alive_nodes():
            models.update(node.loaded_models)
        return sorted(models)

    def best_node_for(self, model: str | None = None) -> RelayNode | None:
        """Select the best node for a given model (or any model)."""
        candidates = self.alive_nodes()
        if model:
            candidates = [n for n in candidates if model in n.loaded_models] or candidates
        if not candidates:
            return None
        return max(candidates, key=lambda n: n.score())

    def get_stats(self) -> dict:
        alive = self.alive_nodes()
        return {
            "total_nodes": len(self._nodes),
            "alive_nodes": len(alive),
            "total_ram_gb": sum(n.ram_total_gb for n in alive),
            "available_ram_gb": sum(n.ram_available_gb for n in alive),
            "total_cpu_cores": sum(n.cpu_cores for n in alive),
            "available_models": self.available_models(),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "hostname": n.hostname,
                    "state": n.state,
                    "ram_available_gb": n.ram_available_gb,
                    "cpu_load_pct": n.cpu_load_pct,
                    "loaded_models": n.loaded_models,
                    "score": round(n.score(), 3),
                    "latency_ms": n.latency_ms,
                    "alive": n.is_alive(),
                }
                for n in self._nodes.values()
            ],
        }


# Singleton
compute_pool = ComputePool()
