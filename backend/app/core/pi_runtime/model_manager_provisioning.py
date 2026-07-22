"""Local provisioner for Pi endpoints (master plan §5.2.3, W8).

Ensure-model / JIT-load for ``kind=local`` Pi endpoints, implemented by
calling the EXISTING helpers through a thin adapter — the Ollama client's
``ensure_model`` (list + pull) and the LM Studio client's ``ensure_model``
(loaded-model check; LM Studio model management stays operator-driven) —
never reimplemented here, and never routed through donated compute.

Remote endpoints serve their own models: provisioning them is a no-op.
Local endpoints that match neither the Ollama nor the LM Studio serving
plane fail closed with a typed resolution error.
"""

from __future__ import annotations

import logging

from app.config import settings

from .endpoints import PiEndpointResolutionError, ResolvedPiEndpoint

logger = logging.getLogger(__name__)


def _strip_v1(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


async def ensure_endpoint_model(endpoint: ResolvedPiEndpoint, model: str) -> bool:
    """Ensure ``model`` is available on a ``kind=local`` Pi endpoint.

    Returns True when the model is present (or was pulled), False for remote
    endpoints (nothing to provision). Raises ``PiEndpointResolutionError``
    for local endpoints on unknown serving planes — provisioning failures
    surface typed, never silently.
    """
    if endpoint.kind != "local":
        return False
    host = _strip_v1(endpoint.base_url)
    ollama_host = settings.ollama_host.rstrip("/")
    lmstudio_host = settings.lmstudio_host.rstrip("/")
    if endpoint.endpoint_id == "pi-local-ollama" or host == ollama_host:
        from app.core.ollama import OllamaClient

        return await OllamaClient(base_url=host).ensure_model(model)
    if endpoint.endpoint_id == "pi-local-lmstudio" or host == lmstudio_host:
        from app.core.lmstudio import LMStudioClient

        return await LMStudioClient(base_url=host).ensure_model(model)
    raise PiEndpointResolutionError(f"provision_unsupported_local_endpoint:{endpoint.endpoint_id}")
