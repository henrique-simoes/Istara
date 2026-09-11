"""Compute registry candidate selection, model loading, and retry helpers."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import settings
from app.core.compute_node import ComputeNode
from app.core.compute_registry_helpers import (
    TRANSIENT_CHAT_BASE_DELAY_S,
    TRANSIENT_CHAT_MAX_DELAY_S,
    TRANSIENT_HTTP_STATUS_CODES,
    _unique_model_names,
)
from app.core.compute_route_evidence import schedule_compute_telemetry_event
from app.core.token_counter import count_tokens

logger = logging.getLogger("app.core.compute_registry")


class ComputeRegistryRoutingMixin:
    def _sorted_servers(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
        project_id: str | None = None,
    ) -> list[ComputeNode]:
        """Get nodes sorted by priority (lower = better), healthy first.

        Backward compat with LLMRouter._sorted_servers().
        """
        servers = [
            node
            for node in self._nodes.values()
            if self._node_authorized_for_project_content(node, project_id)
        ]
        if require_tools:
            # Nodes with detected tool support
            tool_nodes = [
                s
                for s in servers
                if any(c.get("supports_tools") for c in s.model_capabilities.values())
            ]
            # Nodes whose capabilities haven't been detected yet —
            # don't exclude them; they may well support tools.
            unknown_nodes = [s for s in servers if s.is_healthy and not s.model_capabilities]
            filtered = tool_nodes + [n for n in unknown_nodes if n not in tool_nodes]
            if filtered:
                servers = filtered
        if require_vision:
            filtered = [
                s
                for s in servers
                if any(c.get("supports_vision") for c in s.model_capabilities.values())
            ]
            servers = filtered
        if min_context > 0:
            filtered = [
                s
                for s in servers
                if any(
                    c.get("context_length", 0) >= min_context for c in s.model_capabilities.values()
                )
            ]
            if filtered:
                servers = filtered
        return sorted(
            servers,
            key=lambda s: (not s.is_healthy, s.priority, s.latency_ms or 999),
        )

    def _select_candidates(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
        model: str | None = None,
        strict_model: bool = False,
        include_unhealthy: bool = False,
        project_id: str | None = None,
    ) -> list[ComputeNode]:
        """Get candidate nodes sorted by score, filtered by capabilities and circuit breaker."""
        candidates = [
            n
            for n in self._nodes.values()
            if (
                n.score() > 0
                and n.cb_is_available()
                and (
                    n.source not in ("relay", "browser")
                    or bool(n.loaded_models or n.model_capabilities)
                )
            )
        ]
        if include_unhealthy:
            candidate_ids = {n.node_id for n in candidates}
            rescue_candidates = [
                n
                for n in self._nodes.values()
                if n.node_id not in candidate_ids
                and n.cb_is_available()
                and n.active_requests < n.max_active_requests
                and n.health_state not in {"auth_required", "cooldown", "no_model_server"}
                and (
                    n.source not in ("relay", "browser")
                    or bool(n.loaded_models or n.model_capabilities)
                )
            ]
            candidates.extend(rescue_candidates)

        candidates = [
            n for n in candidates if self._node_authorized_for_project_content(n, project_id)
        ]

        if require_tools and candidates:
            tool_capable = [
                n
                for n in candidates
                if any(c.get("supports_tools") for c in n.model_capabilities.values())
            ]
            # Include nodes with unknown capabilities (not yet detected)
            unknown_capable = [
                n for n in candidates if not n.model_capabilities and n not in tool_capable
            ]
            combined = tool_capable + unknown_capable
            if combined:
                candidates = combined

        if require_vision and candidates:
            vision_capable = [
                n
                for n in candidates
                if any(c.get("supports_vision") for c in n.model_capabilities.values())
            ]
            candidates = vision_capable

        requested_model = (model or "").strip()
        if requested_model and requested_model != "default" and strict_model and candidates:
            candidates = [
                n for n in candidates if self._node_can_attempt_requested_model(n, requested_model)
            ]

        if min_context > 0 and candidates:
            context_capable = [
                n
                for n in candidates
                if any(
                    c.get("context_length", 0) >= min_context for c in n.model_capabilities.values()
                )
            ]
            if context_capable:
                candidates = context_capable

        if requested_model and requested_model != "default" and candidates:
            support_check = (
                self._node_can_attempt_requested_model
                if strict_model
                else self._node_supports_model
            )
            model_capable = [n for n in candidates if support_check(n, requested_model)]
            if strict_model:
                candidates = model_capable
                if project_id:
                    candidates.sort(
                        key=lambda n: (
                            0 if n.source in {"relay", "browser"} else 1,
                            not n.is_healthy,
                            n.priority,
                            -n.score(),
                        )
                    )
                    return candidates
            elif model_capable:
                capable_ids = {n.node_id for n in model_capable}
                candidates.sort(
                    key=lambda n: (
                        0 if n.node_id in capable_ids else 1,
                        not n.is_healthy,
                        n.priority,
                        -n.score(),
                    )
                )
                return candidates

        candidates.sort(key=lambda n: (not n.is_healthy, n.priority, -n.score()))
        return candidates

    @staticmethod
    def _node_authorized_for_project_content(
        node: ComputeNode,
        project_id: str | None,
    ) -> bool:
        """Return whether a node may receive project prompt/embedding content.

        Server-owned local/network nodes are controlled by the Istara host and
        remain eligible. Donated relay/browser nodes are untrusted compute
        boundaries: they only receive content when the request has a concrete
        project_id and the node's authenticated donation scope includes it.
        """
        if node.source not in {"relay", "browser"}:
            return True
        requested_project = (project_id or "").strip()
        if not requested_project:
            return False
        allowed = {
            str(pid).strip()
            for pid in getattr(node, "allowed_project_ids", []) or []
            if str(pid).strip()
        }
        return "*" in allowed or requested_project in allowed

    @staticmethod
    def _model_aliases(model: str) -> set[str]:
        base = model.strip()
        aliases = {base}
        if base.endswith(":latest"):
            aliases.add(base.removesuffix(":latest"))
        elif ":" not in base:
            aliases.add(f"{base}:latest")
        return aliases

    @classmethod
    def _node_supports_model(cls, node: ComputeNode, model: str) -> bool:
        aliases = cls._model_aliases(model)
        loaded = {str(m).strip() for m in node.loaded_models if str(m).strip()}
        capability_keys = {str(m).strip() for m in node.model_capabilities.keys() if str(m).strip()}
        advertised = loaded | capability_keys
        return bool(advertised and advertised.intersection(aliases))

    @classmethod
    def _node_can_attempt_requested_model(cls, node: ComputeNode, model: str) -> bool:
        if cls._node_supports_model(node, model):
            return True
        requested = (model or "").strip()
        configured = (settings.lmstudio_model or "").strip()
        configured_host = (settings.lmstudio_host or "").rstrip("/")
        return bool(
            requested
            and configured
            and requested == configured
            and configured != "default"
            and node.provider_type == "lmstudio"
            and node.source not in {"relay", "browser"}
            and configured_host
            and node.host.rstrip("/") == configured_host
        )

    @classmethod
    def _node_supports_vision_model(cls, node: ComputeNode, model: str | None) -> bool:
        if not model or model == "default":
            return any(c.get("supports_vision") for c in node.model_capabilities.values())
        aliases = cls._model_aliases(model)
        for model_name, caps in node.model_capabilities.items():
            if str(model_name).strip() in aliases and caps.get("supports_vision"):
                return True
        return False

    @staticmethod
    def _content_requires_vision(content: Any) -> bool:
        if isinstance(content, list):
            return any(
                ComputeRegistryRoutingMixin._content_requires_vision(item) for item in content
            )
        if isinstance(content, dict):
            item_type = str(content.get("type", "")).lower()
            if item_type in {"image", "image_url", "input_image"}:
                return True
            if "image_url" in content or "input_image" in content:
                return True
            return any(
                ComputeRegistryRoutingMixin._content_requires_vision(value)
                for value in content.values()
                if isinstance(value, (dict, list))
            )
        return False

    @staticmethod
    def _messages_require_vision(messages: list[dict]) -> bool:
        return any(
            ComputeRegistryRoutingMixin._content_requires_vision(msg.get("content"))
            for msg in messages
        )

    @staticmethod
    def _node_loaded_model_names(node: ComputeNode) -> list[str]:
        loaded_from_caps = [
            str(model_name).strip()
            for model_name, caps in node.model_capabilities.items()
            if isinstance(caps, dict) and caps.get("is_loaded")
        ]
        if loaded_from_caps:
            return _unique_model_names(tuple(loaded_from_caps))
        if node._has_explicit_loaded_state():
            return []
        return node._known_chat_models()

    @staticmethod
    def _node_explicit_loaded_model_names(node: ComputeNode) -> list[str]:
        return _unique_model_names(
            tuple(
                str(model_name).strip()
                for model_name, caps in node.model_capabilities.items()
                if isinstance(caps, dict) and caps.get("is_loaded")
            )
        )

    @classmethod
    def _node_load_candidates(
        cls,
        node: ComputeNode,
        model: str | None,
        *,
        require_vision: bool = False,
    ) -> list[str]:
        requested = (model or "").strip()
        if (
            requested
            and requested != "default"
            and node.provider_type == "lmstudio"
            and node._has_explicit_loaded_state()
            and not cls._node_explicit_loaded_model_names(node)
            and requested not in node.model_capabilities
        ):
            return [requested]
        candidates: list[Any] = []
        if requested and requested != "default":
            candidates.append(requested)
        candidates.extend(node._known_chat_models(require_vision=require_vision))
        return [
            name
            for name in _unique_model_names(tuple(candidates))
            if not require_vision or cls._node_supports_vision_model(node, name)
        ]

    async def _recover_unloaded_node_model(
        self,
        node: ComputeNode,
        model: str | None,
        *,
        require_vision: bool = False,
        min_context: int = 0,
        strict_model: bool = False,
    ) -> str | None:
        if node.provider_type != "lmstudio" and not (
            node.source in ("relay", "browser") and node.websocket
        ):
            return None

        try:
            await node.check_health()
        except Exception:
            pass

        requested_model = (model or "").strip()
        strict_requested_model = strict_model and requested_model and requested_model != "default"

        loaded_models = [
            name
            for name in self._node_explicit_loaded_model_names(node)
            if not require_vision or self._node_supports_vision_model(node, name)
        ]
        if strict_requested_model:
            loaded_models = [
                name for name in loaded_models if name in self._model_aliases(requested_model)
            ]
        if loaded_models:
            candidates = loaded_models
        else:
            if not settings.lmstudio_auto_load_enabled:
                node.health_error = "LM Studio auto-load is disabled"
                node.health_state = "no_model_loaded"
                node.is_healthy = False
                return None
            max_attempts = max(1, int(settings.lmstudio_max_load_attempts_per_request or 1))
            if strict_requested_model:
                candidates = [requested_model]
            else:
                candidates = self._node_load_candidates(
                    node,
                    model,
                    require_vision=require_vision,
                )[:max_attempts]

        errors: list[str] = []
        for candidate in candidates:
            try:
                caps = node.model_capabilities.get(candidate)
                context_length = self._context_reload_target(min_context, caps)
                if isinstance(caps, dict) and caps.get("is_loaded"):
                    try:
                        loaded_context = int(
                            caps.get("loaded_context_length") or caps.get("context_length") or 0
                        )
                    except (TypeError, ValueError):
                        loaded_context = 0
                    if not min_context or not loaded_context or loaded_context >= min_context:
                        node.is_healthy = True
                        node.health_state = "ready"
                        node.health_error = ""
                        node.consecutive_failures = 0
                        return candidate
                logger.info(
                    "ComputeRegistry: loading model %s on %s after availability failure",
                    candidate,
                    node.name,
                )
                await node.load_model(
                    candidate,
                    context_length=context_length or None,
                    force=False,
                )
                node.is_healthy = True
                node.health_state = "ready"
                node.health_error = ""
                node.consecutive_failures = 0
                self._invalidate_chat_ready_cache()
                return candidate
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                logger.warning(
                    "ComputeRegistry: failed to load model %s on %s: %s",
                    candidate,
                    node.name,
                    exc,
                )

        if errors:
            node.health_error = "Model load failed: " + " | ".join(errors[-3:])
        else:
            node.health_error = "No loadable chat models discovered"
        node.health_state = "no_model_loaded"
        node.is_healthy = False
        return None

    @staticmethod
    def _context_reload_target(min_context: int, caps: Any) -> int:
        if min_context <= 0:
            return 0

        # Give LM Studio a little headroom over the prompt estimate and round
        # to a common context boundary so repeated runs converge on one load.
        requested = max(8192, min_context + 512, (min_context * 150 + 99) // 100)
        target = ((requested + 1023) // 1024) * 1024
        if isinstance(caps, dict):
            try:
                trained_context = int(caps.get("trained_context_length") or 0)
            except (TypeError, ValueError):
                trained_context = 0
            if trained_context > 0:
                if trained_context < min_context:
                    return 0
                target = min(target, trained_context)
        return target

    async def _recover_context_node_model(
        self,
        node: ComputeNode,
        model: str | None,
        *,
        min_context: int,
        require_vision: bool = False,
    ) -> str | None:
        if min_context <= 0 or node.provider_type != "lmstudio":
            return None
        if not settings.lmstudio_auto_context_reload:
            node.health_error = (
                "LM Studio auto context reload is disabled; "
                f"request needs at least {min_context} tokens"
            )
            return None

        requested_model = (model or "").strip()
        if settings.strict_auto_routing and requested_model and requested_model != "default":
            candidates = [requested_model]
        else:
            candidates = self._node_load_candidates(
                node,
                model,
                require_vision=require_vision,
            )
        context_capable = []
        for candidate in candidates:
            caps = node.model_capabilities.get(candidate)
            if not isinstance(caps, dict):
                context_capable.append(candidate)
                continue
            target_context = self._context_reload_target(min_context, caps)
            if target_context:
                context_capable.append(candidate)

        errors: list[str] = []
        for candidate in _unique_model_names(tuple(context_capable)):
            try:
                target_context = self._context_reload_target(
                    min_context,
                    node.model_capabilities.get(candidate),
                )
                if not target_context:
                    continue
                logger.info(
                    "ComputeRegistry: reloading %s on %s with context_length=%s",
                    candidate,
                    node.name,
                    target_context,
                )
                await node.load_model(
                    candidate,
                    context_length=target_context,
                    force=True,
                )
                node.is_healthy = True
                node.health_state = "ready"
                node.health_error = ""
                node.consecutive_failures = 0
                self._invalidate_chat_ready_cache()
                return candidate
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                logger.warning(
                    "ComputeRegistry: failed to reload %s with larger context on %s: %s",
                    candidate,
                    node.name,
                    exc,
                )

        if errors:
            node.health_error = "Context reload failed: " + " | ".join(errors[-3:])
        return None

    async def _ensure_node_model_ready(
        self,
        node: ComputeNode,
        model: str,
        *,
        require_vision: bool = False,
        min_context: int = 0,
        allow_model_load: bool = True,
        strict_model: bool = False,
    ) -> str:
        requested = (model or "").strip()
        if not requested or requested == "default":
            requested = node._resolve_model(model, require_vision=require_vision)

        if node.provider_type != "lmstudio":
            return requested

        if requested not in node.model_capabilities:
            loaded = self._node_loaded_model_names(node)
            if loaded and requested not in loaded and not strict_model:
                return loaded[0]

        caps = node.model_capabilities.get(requested)
        if isinstance(caps, dict) and caps.get("is_loaded") is False:
            if not allow_model_load:
                raise RuntimeError(f"Model {requested} is available but not loaded")
            loaded = await self._recover_unloaded_node_model(
                node,
                requested,
                require_vision=require_vision,
                min_context=min_context,
                strict_model=strict_model,
            )
            if loaded:
                return loaded
            raise RuntimeError(node.health_error or f"Unable to load model {requested}")

        if node._has_explicit_loaded_state() and not self._node_loaded_model_names(node):
            if not allow_model_load:
                raise RuntimeError("No LM Studio model is loaded")
            loaded = await self._recover_unloaded_node_model(
                node,
                requested,
                require_vision=require_vision,
                min_context=min_context,
                strict_model=strict_model,
            )
            if loaded:
                return loaded
            raise RuntimeError(node.health_error or "No LM Studio model is loaded")

        if min_context > 0 and isinstance(caps, dict) and caps.get("is_loaded"):
            try:
                loaded_context = int(caps.get("loaded_context_length") or 0)
            except (TypeError, ValueError):
                loaded_context = 0
            try:
                current_context = int(caps.get("context_length") or 0)
            except (TypeError, ValueError):
                current_context = 0
            effective_context = loaded_context or current_context
            if effective_context and effective_context < min_context:
                loaded = await self._recover_context_node_model(
                    node,
                    requested,
                    min_context=min_context,
                    require_vision=require_vision,
                )
                if loaded:
                    return loaded
                raise RuntimeError(
                    node.health_error
                    or f"Loaded model {requested} has context {effective_context}, "
                    f"but request needs at least {min_context}"
                )

        return requested

    @staticmethod
    def _record_selected(
        node: ComputeNode,
        *,
        route_kind: str,
        project_id: str | None = None,
        model: str | None = None,
    ) -> None:
        node.selected_request_count += 1
        node.last_selected_at = time.time()
        node.last_route_kind = route_kind
        node.last_selected_project_id = project_id or ""
        node.last_selected_model = model or ""
        schedule_compute_telemetry_event(
            node,
            operation="donor.selected",
            project_id=project_id,
            route_kind=route_kind,
            model=model,
        )

    @staticmethod
    def _record_success(
        node: ComputeNode,
        *,
        route_kind: str | None = None,
        project_id: str | None = None,
        model: str | None = None,
    ) -> None:
        node.consecutive_failures = 0
        node.health_state = "ready"
        node.health_error = ""
        node.is_healthy = True
        node.cb_record_success()
        if route_kind:
            node.served_request_count += 1
            node.last_served_at = time.time()
            node.last_route_kind = route_kind
            node.last_served_project_id = project_id or ""
            node.last_served_model = model or ""
            schedule_compute_telemetry_event(
                node,
                operation="donor.served",
                project_id=project_id,
                route_kind=route_kind,
                model=model,
            )

    @staticmethod
    def _record_failure(
        node: ComputeNode,
        error: Exception,
        *,
        route_kind: str | None = None,
        project_id: str | None = None,
        model: str | None = None,
    ) -> None:
        node.consecutive_failures += 1
        node.health_error = str(error)[:200] if str(error) else "Request failed"
        if route_kind:
            node.failed_request_count += 1
            node.last_failed_at = time.time()
            node.last_route_kind = route_kind
            node.last_selected_project_id = project_id or node.last_selected_project_id
            node.last_selected_model = model or node.last_selected_model
            node.last_failure_error = node.health_error
            schedule_compute_telemetry_event(
                node,
                operation="donor.failed",
                project_id=project_id,
                route_kind=route_kind,
                model=model,
                status="error",
                error_type="compute_route_failed",
                error_message=node.health_error,
            )
        node.cb_record_failure()
        if node.consecutive_failures >= 3:
            node.health_state = "cooldown"
            node.cooldown_until = time.time() + 60
            node.is_healthy = False
        else:
            node.health_state = "degraded"

    @staticmethod
    def _record_auxiliary_failure(node: ComputeNode, error: Exception) -> None:
        """Record a non-routing failure without taking the chat node offline.

        Embedding quotas and retrieval-side failures should degrade RAG quality,
        but they must not make a healthy chat model unavailable to skills,
        planning, or orchestration. Those callers already fall back to keyword
        search when embeddings fail.
        """
        node.health_error = str(error)[:200] if str(error) else "Auxiliary request failed"
        if node.is_healthy and node.health_state != "cooldown":
            node.health_state = "degraded"

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        """Return true for provider/network failures that are worth retrying."""
        if isinstance(error, (httpx.TimeoutException, httpx.NetworkError, TimeoutError)):
            return True
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        return status_code in TRANSIENT_HTTP_STATUS_CODES

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        """Small bounded exponential backoff between live-provider retries."""
        delay = TRANSIENT_CHAT_BASE_DELAY_S * (2 ** max(0, attempt - 1))
        return min(delay, TRANSIENT_CHAT_MAX_DELAY_S)

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        """Clean messages for LLM API compatibility."""
        sanitized = []
        for msg in messages:
            role = msg.get("role", "")

            # Pass through tool-result messages verbatim
            if role == "tool":
                entry: dict = {"role": "tool", "content": str(msg.get("content", ""))}
                if msg.get("tool_call_id"):
                    entry["tool_call_id"] = msg["tool_call_id"]
                sanitized.append(entry)
                continue

            # Pass through assistant messages that carry tool_calls
            if role == "assistant" and msg.get("tool_calls"):
                entry_a: dict = {
                    "role": "assistant",
                    "content": msg.get("content") or "",
                }
                entry_a["tool_calls"] = msg["tool_calls"]
                sanitized.append(entry_a)
                continue

            if role not in ("system", "user", "assistant"):
                continue
            content = msg.get("content")
            if content is None or (isinstance(content, str) and not content.strip()):
                continue
            if isinstance(content, (dict, list)):
                sanitized.append({"role": role, "content": content})
            else:
                sanitized.append({"role": role, "content": str(content)})

        # Merge consecutive system messages
        merged: list[dict] = []
        for msg in sanitized:
            if (
                merged
                and msg["role"] == "system"
                and merged[-1]["role"] == "system"
                and isinstance(msg["content"], str)
                and isinstance(merged[-1]["content"], str)
            ):
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg)
        return merged

    @staticmethod
    def _estimate_context_tokens(
        messages: list[dict],
        max_tokens: int | None,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
    ) -> int:
        total = max_tokens or 512
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, (dict, list)):
                text = json.dumps(content, ensure_ascii=False)
            else:
                text = str(content)
            total += count_tokens(text) + 4
        if response_format:
            try:
                total += count_tokens(json.dumps(response_format, ensure_ascii=False))
            except Exception:
                total += count_tokens(str(response_format))
        if tools:
            try:
                total += count_tokens(json.dumps(tools, ensure_ascii=False))
            except Exception:
                total += count_tokens(str(tools))
        return total
