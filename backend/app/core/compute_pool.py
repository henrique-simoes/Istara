"""Compute Pool — backward compatibility wrapper over ComputeRegistry.

All relay node management is now handled by ``compute_registry``.
This module re-exports the symbols that existing code imports:

- ``RelayNode`` -> alias for ``ComputeNode`` (relay-flavored)
- ``compute_pool`` -> the global ``compute_registry`` singleton

Existing code like::

    from app.core.compute_pool import RelayNode, compute_pool
    compute_pool.register_node(node)
    compute_pool.total_capacity()
    compute_pool.get_stats()

continues to work unchanged.
"""

from app.core.compute_registry import ComputeNode as RelayNode, compute_registry

# The pool IS the registry.
compute_pool = compute_registry

__all__ = ["RelayNode", "compute_pool"]
