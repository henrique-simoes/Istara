"""Compute node data model assembled from focused behavior mixins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.compute_node_invocation import ComputeNodeInvocationMixin
from app.core.compute_node_models import ComputeNodeModelMixin
from app.core.compute_node_transport import ComputeNodeTransportMixin
from app.core.compute_registry_helpers import infer_provider_type


@dataclass
class ComputeNode(ComputeNodeTransportMixin, ComputeNodeModelMixin, ComputeNodeInvocationMixin):
    """A single compute resource.

    Backward-compatible with LLMServerEntry — exposes the same attribute
    names so code that accesses ``llm_router._servers[id].host`` etc.
    keeps working.
    """

    node_id: str
    name: str
    host: str
    source: str  # "local" | "network" | "relay" | "browser"
    provider_type: str  # "lmstudio" | "ollama" | "openai_compat" | "gemini_openai"

    # Health
    is_healthy: bool = False
    health_state: str = "unknown"
    health_error: str = ""
    last_health_check: float = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0

    # Circuit breaker (three-state: closed → open → half_open)
    cb_state: str = "closed"  # closed | open | half_open
    cb_failure_count: int = 0
    cb_last_trip: float = 0
    cb_cooldown: float = 60  # seconds before probing
    CB_FAILURE_THRESHOLD: int = 5
    CB_SLOW_THRESHOLD_MS: float = 10000  # 10s for local models

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

    # Petals bridge (DEC-11): donor consent to serve Pi-engine traffic through the
    # A2A-bridged loopback shim. Default OFF — a donor never serves Pi traffic
    # unless explicitly opted in.
    pi_served: bool = False
    max_active_requests: int = 4
    is_local: bool = False
    is_relay: bool = False
    selected_request_count: int = 0
    served_request_count: int = 0
    failed_request_count: int = 0
    last_selected_at: float = 0
    last_served_at: float = 0
    last_failed_at: float = 0
    last_route_kind: str = ""
    last_selected_project_id: str = ""
    last_served_project_id: str = ""
    last_selected_model: str = ""
    last_served_model: str = ""
    last_failure_error: str = ""

    # Connection (relay nodes)
    websocket: Any = None
    pending_requests: dict = field(default_factory=dict)
    last_heartbeat: float = 0
    relay_request_timeout_s: float = 300

    # Relay-specific fields (backward compat with RelayNode)
    user_id: str = ""
    ip_address: str = ""
    provider_host: str = ""
    allowed_project_ids: list[str] = field(default_factory=list)
    state: str = "idle"
    priority_level: int = 3
    connected_at: float = 0

    # LLM client (cached)
    _client: Any = None
    api_key: str = ""

    def __post_init__(self) -> None:
        self.provider_type = infer_provider_type(self.provider_type, self.host)
