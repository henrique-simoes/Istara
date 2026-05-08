"""Compute node health, model discovery, model loading, and resolution."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.core.compute_registry_helpers import (
    LMSTUDIO_MODEL_LOAD_LOCK,
    _ollama_model_names,
    _openai_model_ids,
    _unique_model_names,
)

logger = logging.getLogger("app.core.compute_registry")

class ComputeNodeModelMixin:
    async def check_health(self) -> bool:
        """Probe the server health endpoint and discover available models.

        Backward compat with LLMServerEntry.check_health().
        """
        try:
            client = await self._get_client()
            start = time.time()
            if self.provider_type == "ollama":
                resp = await client.get("/api/tags", timeout=10.0)
                self.latency_ms = (time.time() - start) * 1000
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        self.loaded_models = _ollama_model_names(data)
                    except Exception:
                        self.loaded_models = []
                    if self.loaded_models:
                        self.is_healthy = True
                        self.health_state = "ready"
                        self.health_error = ""
                        self.consecutive_failures = 0
                        self.last_health_check = time.time()
                        return True

                # A common misconfiguration is saving an LM Studio/OpenAI-compatible
                # server as Ollama. LM Studio may return 200 for unknown paths, so a
                # status-only check would keep routing the wrong endpoint forever.
                openai_start = time.time()
                openai_resp = await client.get(self._openai_endpoint("models"), timeout=10.0)
                self.latency_ms = (time.time() - openai_start) * 1000
                if openai_resp.status_code == 200:
                    try:
                        data = openai_resp.json()
                        self.loaded_models = _openai_model_ids(data)
                    except Exception:
                        self.loaded_models = []
                    if self.loaded_models:
                        self.provider_type = "openai_compat"
                        self.is_healthy = True
                        self.health_state = "ready"
                        self.health_error = ""
                        self.consecutive_failures = 0
                        self.last_health_check = time.time()
                        logger.info(
                            "ComputeRegistry: corrected %s provider from ollama to "
                            "openai_compat after /v1/models succeeded.",
                            self.name,
                        )
                        return True
                resp = openai_resp
            else:
                resp = await client.get(self._openai_endpoint("models"), timeout=10.0)
            self.latency_ms = (time.time() - start) * 1000
            self.is_healthy = resp.status_code == 200
            if self.is_healthy:
                try:
                    data = resp.json()
                    if self.provider_type == "ollama":
                        self.loaded_models = (
                            _ollama_model_names(data) if isinstance(data, dict) else []
                        )
                    else:
                        self.loaded_models = _openai_model_ids(data)
                except Exception:
                    self.loaded_models = []
                if self.loaded_models:
                    self.health_state = "ready"
                    self.health_error = ""
                    self.consecutive_failures = 0
                    self.last_health_check = time.time()
                else:
                    self.is_healthy = False
                    self.health_state = "unhealthy"
                    self.health_error = "No LLM models advertised by this host"
            elif resp.status_code in (401, 403):
                # Auth failure — server requires an API key
                self.health_state = "auth_required"
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("error", {})
                    if isinstance(err_msg, dict):
                        self.health_error = err_msg.get("message", "API key required")
                    else:
                        self.health_error = str(err_msg) or "API key required"
                except Exception:
                    self.health_error = "API key required by this server"
            else:
                self.health_state = "unhealthy"
                self.health_error = f"Server returned HTTP {resp.status_code}"
        except httpx.ConnectError:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "unreachable"
            self.health_error = "Cannot connect — check the host URL"
        except httpx.TimeoutException:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "timeout"
            self.health_error = "Connection timed out"
        except Exception as e:
            self.is_healthy = False
            self.latency_ms = 9999
            self.health_state = "unhealthy"
            self.health_error = str(e)[:200] if str(e) else "Unknown error"
        return self.is_healthy

    def _capability_supports(self, model_name: str, capability: str) -> bool:
        caps = self.model_capabilities.get(model_name)
        return bool(isinstance(caps, dict) and caps.get(capability))

    def _models_supporting(self, capability: str) -> list[str]:
        supported: list[str] = []
        for model_name, caps in self.model_capabilities.items():
            if isinstance(caps, dict) and caps.get(capability):
                supported.append(model_name)
        return supported

    def _models_marked_loaded(self) -> set[str]:
        loaded = {str(model).strip() for model in self.loaded_models if str(model).strip()}
        for model_name, caps in self.model_capabilities.items():
            if isinstance(caps, dict) and caps.get("is_loaded"):
                loaded.add(str(model_name).strip())
        return loaded

    def _has_explicit_loaded_state(self) -> bool:
        return any(
            isinstance(caps, dict) and caps.get("is_loaded") is not None
            for caps in self.model_capabilities.values()
        )

    def _known_chat_models(self, require_vision: bool = False) -> list[str]:
        names: list[Any] = []
        loaded_from_caps: list[str] = []
        loadable_from_caps: list[str] = []
        other_from_caps: list[str] = []
        for model_name, caps in self.model_capabilities.items():
            if not isinstance(caps, dict):
                other_from_caps.append(model_name)
                continue
            if require_vision and not caps.get("supports_vision"):
                continue
            if caps.get("is_loaded"):
                loaded_from_caps.append(model_name)
            elif caps.get("loadable") is not False:
                loadable_from_caps.append(model_name)
            else:
                other_from_caps.append(model_name)
        names.extend(loaded_from_caps)
        names.extend(self.loaded_models or [])
        names.extend(loadable_from_caps)
        names.extend(other_from_caps)
        return [
            name
            for name in _unique_model_names(tuple(names))
            if "embed" not in name.lower()
        ]

    def _resolve_model(self, model: str | None, require_vision: bool = False) -> str:
        """Resolve the model name — use what's available on this node."""
        models = self.loaded_models or []
        non_embed = [m for m in models if "embed" not in m.lower()]
        known_chat_models = self._known_chat_models(require_vision=require_vision)
        loaded_chat_models = [
            name
            for name, caps in self.model_capabilities.items()
            if (
                isinstance(caps, dict)
                and caps.get("is_loaded")
                and "embed" not in name.lower()
                and (not require_vision or caps.get("supports_vision"))
            )
        ]
        configured_lmstudio_host = settings.lmstudio_host.rstrip("/")
        is_configured_lmstudio = (
            self.provider_type != "ollama"
            and configured_lmstudio_host
            and self.host.rstrip("/") == configured_lmstudio_host
        )
        parsed_host = urlparse(self.host if "://" in self.host else f"http://{self.host}")
        is_native_lmstudio = self.provider_type == "lmstudio" and parsed_host.port == 1234
        if require_vision:
            vision_models = [m for m in self._models_supporting("supports_vision") if m]
            loaded = self._models_marked_loaded()
            if model and model != "default" and self._capability_supports(
                model, "supports_vision"
            ):
                return model
            loaded_vision = [m for m in vision_models if m in loaded]
            if loaded_vision:
                return loaded_vision[0]
            if vision_models:
                return vision_models[0]

        if model and model != "default":
            if is_configured_lmstudio:
                if model in self.model_capabilities:
                    return model
                if not is_native_lmstudio:
                    return model
                if loaded_chat_models:
                    return loaded_chat_models[0]
                if self._has_explicit_loaded_state():
                    return model
                if known_chat_models:
                    return known_chat_models[0]
                return model
            if model in self.model_capabilities:
                return model
            if models and model not in models:
                if known_chat_models:
                    return known_chat_models[0]
            if known_chat_models and not is_configured_lmstudio:
                return known_chat_models[0]
            return model
        if (
            is_configured_lmstudio
            and settings.lmstudio_model
            and settings.lmstudio_model != "default"
        ):
            configured_model = settings.lmstudio_model
            if configured_model in self.model_capabilities:
                return configured_model
            if not is_native_lmstudio:
                return configured_model
            if loaded_chat_models:
                return loaded_chat_models[0]
            if self._has_explicit_loaded_state():
                return configured_model
            if known_chat_models:
                return known_chat_models[0]
            return settings.lmstudio_model
        if known_chat_models:
            return known_chat_models[0]
        if non_embed:
            return non_embed[0]
        if self.provider_type == "ollama":
            return settings.ollama_model
        return settings.lmstudio_model

    async def load_model(
        self,
        model: str,
        context_length: int | None = None,
        *,
        force: bool = False,
    ) -> bool:
        """Load a model on this node when the provider exposes a load contract."""
        requested = (model or "").strip()
        if not requested:
            return False

        caps = self.model_capabilities.get(requested)
        if (
            not force
            and
            isinstance(caps, dict)
            and caps.get("is_loaded")
            and (
                not context_length
                or int(caps.get("loaded_context_length") or caps.get("context_length") or 0)
                >= context_length
            )
        ):
            return True

        if self.source in ("relay", "browser") and self.websocket:
            async with LMSTUDIO_MODEL_LOAD_LOCK:
                response = await self._request_over_websocket(
                    "load_model_request",
                    {
                        "model": requested,
                        "context_length": context_length,
                        "allow_unload": force and settings.lmstudio_allow_unload_on_reload,
                    },
                )
            result = response.get("result", {})
            if isinstance(result, dict):
                models = result.get("models")
                if isinstance(models, list):
                    self.loaded_models = [str(m) for m in models if str(m).strip()]
                model_capabilities = result.get("model_capabilities")
                if isinstance(model_capabilities, dict):
                    self.model_capabilities = {
                        **self.model_capabilities,
                        **model_capabilities,
                    }
            self._mark_model_loaded(requested, context_length=context_length)
            return True

        if self.provider_type == "lmstudio":
            client = await self._get_client()
            payload: dict[str, Any] = {"model": requested, "echo_load_config": True}
            if context_length:
                if force and settings.lmstudio_allow_unload_on_reload:
                    await self._unload_lmstudio_loaded_instances()
                payload["context_length"] = context_length
            async with LMSTUDIO_MODEL_LOAD_LOCK:
                resp = await client.post(
                    "api/v1/models/load",
                    json=payload,
                    timeout=None,
                )
                resp.raise_for_status()
                loaded_context = context_length
                try:
                    data = resp.json()
                    load_config = data.get("load_config") if isinstance(data, dict) else None
                    if isinstance(load_config, dict) and load_config.get("context_length"):
                        loaded_context = int(load_config["context_length"])
                except Exception:
                    pass
            self._mark_model_loaded(requested, context_length=loaded_context)
            return True

        return True

    async def _unload_lmstudio_loaded_instances(self) -> None:
        client = await self._get_client()
        try:
            resp = await client.get("api/v1/models", timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug("ComputeRegistry: LM Studio unload preflight skipped: %s", exc)
            return
        models = data.get("models") or data.get("data") or []
        unloaded: set[str] = set()
        for model in models:
            if not isinstance(model, dict):
                continue
            for instance in model.get("loaded_instances") or []:
                if not isinstance(instance, dict):
                    continue
                instance_id = str(instance.get("id") or instance.get("instance_id") or "").strip()
                if not instance_id or instance_id in unloaded:
                    continue
                try:
                    unload_resp = await client.post(
                        "api/v1/models/unload",
                        json={"instance_id": instance_id},
                        timeout=None,
                    )
                    unload_resp.raise_for_status()
                    unloaded.add(instance_id)
                except Exception as exc:
                    logger.warning(
                        "ComputeRegistry: failed to unload LM Studio instance %s on %s: %s",
                        instance_id,
                        self.name,
                        exc,
                    )

        if unloaded:
            for caps in self.model_capabilities.values():
                if isinstance(caps, dict) and caps.get("is_loaded"):
                    caps["is_loaded"] = False
                    caps["loaded_context_length"] = None

    def _mark_model_loaded(self, model: str, context_length: int | None = None) -> None:
        requested = model.strip()
        if not requested:
            return
        if requested not in self.loaded_models:
            self.loaded_models.append(requested)
        caps = self.model_capabilities.get(requested)
        if isinstance(caps, dict):
            caps["is_loaded"] = True
            if context_length:
                caps["loaded_context_length"] = context_length
                caps["context_length"] = max(int(caps.get("context_length") or 0), context_length)

    def _resolve_embed_model(self, model: str | None) -> str:
        """Resolve embedding model — prefer embedding-specific models."""
        if model and model != "default":
            return model
        if self.loaded_models:
            embed_models = [m for m in self.loaded_models if "embed" in m.lower()]
            if embed_models:
                return embed_models[0]
        if self.provider_type == "ollama":
            return settings.ollama_embed_model
        return settings.lmstudio_embed_model
