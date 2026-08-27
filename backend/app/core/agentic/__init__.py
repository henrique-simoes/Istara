"""The governed entry point for Istara agentic invocations.

Product migrations land in later waves.  W1 deliberately exposes the contract
without moving a legacy call site, so the count-to-zero inventory remains 87.
"""

from .dispatcher import AgenticDispatcher, agentic

__all__ = ["AgenticDispatcher", "agentic"]
