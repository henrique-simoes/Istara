"""Local provisioner for Pi endpoints (master plan §5.2.3, W8).

Ensure-model / JIT-load for ``kind=local`` Pi endpoints, implemented by
calling the EXISTING provider helpers through a thin adapter — the Ollama
client's ``ensure_model`` (list + pull) and the ComputeNode LM Studio
``load_model`` contract — never reimplemented here, and never routed through
donated compute.

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
        if not settings.lmstudio_auto_load_enabled:
            raise PiEndpointResolutionError("provision_lmstudio_auto_load_disabled")
        from app.core.compute_node import ComputeNode

        node = ComputeNode(
            node_id=endpoint.endpoint_id,
            name="Pi local LM Studio",
            host=host,
            source="local",
            provider_type="lmstudio",
            is_local=True,
            is_healthy=True,
            api_key=endpoint.api_key,
        )
        try:
            loaded = await node.load_model(model, force=False)
        except Exception as exc:
            raise PiEndpointResolutionError(
                f"provision_lmstudio_failed:{endpoint.endpoint_id}"
            ) from exc
        if not loaded:
            raise PiEndpointResolutionError(
                f"provision_lmstudio_failed:{endpoint.endpoint_id}"
            )
        return True
    raise PiEndpointResolutionError(f"provision_unsupported_local_endpoint:{endpoint.endpoint_id}")
