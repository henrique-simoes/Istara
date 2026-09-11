"""Private, opt-in Pi runtime contracts.

The package must never import or mutate the donated-compute registry.  Pi
provider selection is exact by endpoint identity and is resolved only for a
validated Pi request.
"""

from .endpoints import (
    PiEndpointResolutionError,
    PiEndpointResolver,
    PiRuntimeTurnError,
    ResolvedPiEndpoint,
)
from .engine import (
    AUTORESEARCH_TOOLS,
    CHANNEL_TOOLS,
    DELEGATION_TOOLS,
    PiExecutionService,
    SteeringBinding,
)
from .supervisor import PiRuntimeSupervisor, PiWorkerError, get_supervisor, shutdown_supervisor
from .tools import build_tool_catalog

__all__ = [
    "PiEndpointResolutionError",
    "PiEndpointResolver",
    "PiRuntimeTurnError",
    "ResolvedPiEndpoint",
    "PiExecutionService",
    "SteeringBinding",
    "AUTORESEARCH_TOOLS",
    "CHANNEL_TOOLS",
    "DELEGATION_TOOLS",
    "PiRuntimeSupervisor",
    "PiWorkerError",
    "get_supervisor",
    "shutdown_supervisor",
    "build_tool_catalog",
]
