"""Public ComputeRegistry class assembled from focused implementation slices."""

from __future__ import annotations

from app.core.compute_registry_invocation import ComputeRegistryInvocationMixin
from app.core.compute_registry_lifecycle import ComputeRegistryLifecycleMixin
from app.core.compute_registry_routing import ComputeRegistryRoutingMixin


class ComputeRegistry(
    ComputeRegistryLifecycleMixin,
    ComputeRegistryRoutingMixin,
    ComputeRegistryInvocationMixin,
):
    """Single source of truth for all compute resources."""

    pass
