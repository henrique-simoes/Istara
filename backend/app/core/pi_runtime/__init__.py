"""Private, opt-in Pi runtime contracts.

The package must never import or mutate the donated-compute registry.  Pi
provider selection is exact by endpoint identity and is resolved only for a
validated Pi request.
"""

from .endpoints import PiEndpointResolver, ResolvedPiEndpoint

__all__ = ["PiEndpointResolver", "ResolvedPiEndpoint"]
