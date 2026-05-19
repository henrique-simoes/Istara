"""Compute registry chat, stream, embedding, model, and stats invocation paths."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings
from app.core.compute_capacity import compute_capacity_envelope
from app.core.compute_node import ComputeNode
from app.core.compute_registry_helpers import (
    TRANSIENT_CHAT_BASE_DELAY_S,
    TRANSIENT_CHAT_MAX_ATTEMPTS,
    TRANSIENT_CHAT_MAX_DELAY_S,
    TRANSIENT_HTTP_STATUS_CODES,
    _hydrate_local_resources,
    _looks_like_context_length_error,
    _looks_like_model_availability_error,
    _positive_number,
    _redacted_endpoint_for_log,
    _server_endpoint_identity,
    _unique_model_names,
)
from app.core.llm_output import (
    ThinkingContentFilter,
    visible_assistant_content,
    visible_assistant_message,
)
from app.core.llm_schema_adapter import provider_response_format_fields
from app.core.llm_thinking import apply_thinking_control
from app.core.token_counter import count_tokens

logger = logging.getLogger("app.core.compute_registry")


def _hardware_resource_key(node: ComputeNode) -> tuple[str, str]:
    host = getattr(node, "host", "") or getattr(node, "provider_host", "") or ""
    if host:
        _, hostname, _, _ = _server_endpoint_identity(host)
        if hostname == "local":
            return ("machine", "local")
        return ("machine", hostname)
    if getattr(node, "source", "") in {"relay", "browser"}:
        return ("donor", getattr(node, "user_id", "") or getattr(node, "node_id", ""))
    return ("node", getattr(node, "node_id", ""))


def _unique_hardware_resource_nodes(nodes: list[ComputeNode]) -> list[ComputeNode]:
    resources: dict[tuple[str, str], ComputeNode] = {}
    for node in nodes:
        key = _hardware_resource_key(node)
        current = resources.get(key)
        if current is None:
            resources[key] = node
            continue
        if getattr(node, "ram_total_gb", 0) > getattr(current, "ram_total_gb", 0):
            resources[key] = node
            continue
        if (
            getattr(node, "ram_total_gb", 0) == getattr(current, "ram_total_gb", 0)
            and getattr(node, "ram_available_gb", 0) > getattr(current, "ram_available_gb", 0)
        ):
            resources[key] = node
            continue
        if getattr(node, "is_healthy", False) and not getattr(current, "is_healthy", False):
            resources[key] = node
    return list(resources.values())


def _endpoint_resource_key(node: ComputeNode) -> tuple:
    host = getattr(node, "host", "") or getattr(node, "provider_host", "") or ""
    if host:
        return (
            "endpoint",
            getattr(node, "provider_type", ""),
            *_server_endpoint_identity(host),
        )
    return ("node", getattr(node, "node_id", ""))


def _source_snapshot_rank(node: ComputeNode) -> int:
    source = getattr(node, "source", "")
    if source == "local":
        return 30
    if source in {"relay", "browser"}:
        return 20
    if source == "network":
        return 10
    return 0


def _prefer_node_snapshot(current: ComputeNode, candidate: ComputeNode) -> ComputeNode:
    candidate_source_rank = _source_snapshot_rank(candidate)
    current_source_rank = _source_snapshot_rank(current)
    if candidate_source_rank != current_source_rank:
        return candidate if candidate_source_rank > current_source_rank else current
    candidate_healthy = getattr(candidate, "is_healthy", False)
    current_healthy = getattr(current, "is_healthy", False)
    if candidate_healthy != current_healthy:
        return candidate if candidate_healthy else current
    if getattr(candidate, "priority", 10) < getattr(current, "priority", 10):
        return candidate
    candidate_models = len(getattr(candidate, "loaded_models", []) or []) + len(
        getattr(candidate, "model_capabilities", {}) or {}
    )
    current_models = len(getattr(current, "loaded_models", []) or []) + len(
        getattr(current, "model_capabilities", {}) or {}
    )
    if candidate_models > current_models:
        return candidate
    if getattr(candidate, "last_heartbeat", 0) > getattr(current, "last_heartbeat", 0):
        return candidate
    return current


def _unique_endpoint_nodes(nodes: list[ComputeNode]) -> list[ComputeNode]:
    endpoints: dict[tuple, ComputeNode] = {}
    order: list[tuple] = []
    for node in nodes:
        key = _endpoint_resource_key(node)
        current = endpoints.get(key)
        if current is None:
            endpoints[key] = node
            order.append(key)
            continue
        endpoints[key] = _prefer_node_snapshot(current, node)
    return [endpoints[key] for key in order]


class ComputeRegistryInvocationMixin:
    @staticmethod
    def _effective_requested_chat_model(model: str | None) -> str | None:
        requested = (model or "").strip()
        if requested and requested != "default":
            return requested
        configured = (settings.lmstudio_model or "").strip()
        if (
            settings.strict_auto_routing
            and settings.llm_provider == "lmstudio"
            and configured
            and configured != "default"
        ):
            return configured
        return model

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        min_context: int = 0,
        thinking_mode: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Route a chat request to the best available node."""
        model = self._effective_requested_chat_model(model)
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = apply_thinking_control(msgs, thinking_mode)
        msgs = self._sanitize_messages(msgs)
        require_vision = self._messages_require_vision(msgs)
        if min_context <= 0:
            min_context = self._estimate_context_tokens(
                msgs,
                max_tokens,
                response_format=response_format,
                tools=tools,
            )

        lmstudio_load_recovery_used = False
        for node in self._select_candidates(
            require_tools=bool(tools),
            require_vision=require_vision,
            min_context=min_context,
            model=model,
            strict_model=settings.strict_auto_routing,
            include_unhealthy=True,
            project_id=project_id,
        ):
            if (
                require_vision
                and model
                and model != "default"
                and not self._node_supports_vision_model(node, model)
            ):
                continue
            resolved_model = node._resolve_model(model, require_vision=require_vision)
            logger.info(
                f"ComputeRegistry: routing chat to {node.name} ({node.host}) model={resolved_model}"
            )
            node.active_requests += 1
            try:
                for attempt in range(1, TRANSIENT_CHAT_MAX_ATTEMPTS + 1):
                    try:
                        resolved_model = await self._ensure_node_model_ready(
                            node,
                            resolved_model,
                            require_vision=require_vision,
                            min_context=min_context,
                        )
                        if node.source in ("relay", "browser") and node.websocket:
                            data = await node.chat(
                                msgs,
                                model=resolved_model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                tools=tools,
                                response_format=response_format,
                                thinking_mode=None,
                                project_id=project_id,
                            )
                            self._record_success(node)
                            return data

                        client = await node._get_client()

                        if node.provider_type == "ollama":
                            options: dict = {"temperature": temperature}
                            if max_tokens:
                                options["num_predict"] = max_tokens
                            payload = {
                                "model": resolved_model,
                                "messages": msgs,
                                "stream": False,
                                "options": options,
                            }
                            if response_format:
                                payload.update(
                                    provider_response_format_fields(
                                        node.provider_type,
                                        response_format,
                                    )
                                )
                            resp = await client.post("/api/chat", json=payload)
                            resp.raise_for_status()
                            data = resp.json()
                            message = data.get("message")
                            if isinstance(message, dict):
                                data["message"] = visible_assistant_message(message)
                            self._record_success(node)
                            return data

                        if node.is_anthropic:
                            data = await node.chat(
                                msgs,
                                model=resolved_model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                tools=tools,
                                response_format=response_format,
                                thinking_mode=None,
                                project_id=project_id,
                            )
                            self._record_success(node)
                            return data

                        payload = {
                            "model": resolved_model,
                            "messages": msgs,
                            "temperature": temperature,
                            "stream": False,
                        }
                        if max_tokens:
                            payload["max_tokens"] = max_tokens
                        if tools:
                            payload["tools"] = tools
                        if response_format:
                            payload.update(
                                provider_response_format_fields(
                                    node.provider_type,
                                    response_format,
                                )
                            )
                        resp = await client.post(
                            node._openai_endpoint("chat/completions"),
                            json=payload,
                        )
                        resp.raise_for_status()
                        data = resp.json()

                        choice = data["choices"][0]
                        message = choice["message"]

                        result: dict = {
                            "message": {
                                "role": "assistant",
                                "content": visible_assistant_content(message),
                            }
                        }
                        if message.get("tool_calls"):
                            result["message"]["tool_calls"] = message["tool_calls"]
                            result["finish_reason"] = choice.get("finish_reason", "tool_calls")

                        self._record_success(node)
                        return result
                    except Exception as e:
                        if _looks_like_model_availability_error(e):
                            loaded_recovery_models = [
                                name
                                for name in self._node_explicit_loaded_model_names(node)
                                if not require_vision
                                or self._node_supports_vision_model(node, name)
                            ]
                            if (
                                node.provider_type == "lmstudio"
                                and not loaded_recovery_models
                            ):
                                if lmstudio_load_recovery_used:
                                    logger.warning(
                                        "ComputeRegistry: skipped additional LM Studio "
                                        "model load on %s; one load attempt is allowed "
                                        "per chat request",
                                        node.name,
                                    )
                                    break
                                lmstudio_load_recovery_used = True
                            recovered = await self._recover_unloaded_node_model(
                                node,
                                resolved_model,
                                require_vision=require_vision,
                                min_context=min_context,
                            )
                            if recovered and attempt < TRANSIENT_CHAT_MAX_ATTEMPTS:
                                resolved_model = recovered
                                continue
                        if _looks_like_context_length_error(e):
                            recovered = await self._recover_context_node_model(
                                node,
                                resolved_model,
                                min_context=min_context,
                                require_vision=require_vision,
                            )
                            if recovered and attempt < TRANSIENT_CHAT_MAX_ATTEMPTS:
                                resolved_model = recovered
                                continue
                            logger.warning(
                                "ComputeRegistry: %s lacks required context for "
                                "this prompt (requested >=%s tokens); trying next node",
                                node.name,
                                min_context or "unknown",
                            )
                            break
                        self._record_failure(node, e)
                        transient = self._is_transient_error(e)
                        if attempt < TRANSIENT_CHAT_MAX_ATTEMPTS and transient:
                            delay = self._retry_delay(attempt)
                            logger.warning(
                                "ComputeRegistry: transient chat failure on %s "
                                "(attempt %s/%s); retrying in %.2fs: %s",
                                node.name,
                                attempt,
                                TRANSIENT_CHAT_MAX_ATTEMPTS,
                                delay,
                                e,
                            )
                            await asyncio.sleep(delay)
                            continue

                        if hasattr(e, "response") and hasattr(e.response, "text"):
                            logger.warning(
                                "ComputeRegistry: chat failed on %s after %s attempt(s): "
                                "%s | Body: %s",
                                node.name,
                                attempt,
                                e,
                                e.response.text,
                            )
                        else:
                            logger.warning(
                                "ComputeRegistry: chat failed on %s after %s attempt(s): %s",
                                node.name,
                                attempt,
                                e,
                            )
                        break

            except Exception as e:
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    logger.warning(
                        "ComputeRegistry: chat failed on %s: %s | Body: %s",
                        node.name,
                        e,
                        e.response.text,
                    )
                else:
                    logger.warning(f"ComputeRegistry: chat failed on {node.name}: {e}")
                self._record_auxiliary_failure(node, e)
            finally:
                node.active_requests -= 1

        if require_vision:
            raise RuntimeError("No vision-capable compute nodes available for image chat")
        raise RuntimeError("No compute nodes available for chat")

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        min_context: int = 0,
        thinking_mode: str | None = None,
        project_id: str | None = None,
    ) -> AsyncGenerator[str | dict, None]:
        """Streaming chat -- yields str chunks and dict for tool calls."""
        model = self._effective_requested_chat_model(model)
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = apply_thinking_control(msgs, thinking_mode)
        msgs = self._sanitize_messages(msgs)
        require_vision = self._messages_require_vision(msgs)
        if min_context <= 0:
            min_context = self._estimate_context_tokens(msgs, max_tokens, tools=tools)

        lmstudio_load_recovery_used = False
        for node in self._select_candidates(
            require_tools=bool(tools),
            require_vision=require_vision,
            min_context=min_context,
            model=model,
            strict_model=settings.strict_auto_routing,
            include_unhealthy=True,
            project_id=project_id,
        ):
            if (
                require_vision
                and model
                and model != "default"
                and not self._node_supports_vision_model(node, model)
            ):
                continue
            resolved_model = node._resolve_model(model, require_vision=require_vision)
            logger.info(
                f"ComputeRegistry: routing stream to {node.name} "
                f"({node.host}) model={resolved_model}"
            )
            node.active_requests += 1
            try:
                for attempt in range(1, TRANSIENT_CHAT_MAX_ATTEMPTS + 1):
                    emitted_chunk = False
                    try:
                        resolved_model = await self._ensure_node_model_ready(
                            node,
                            resolved_model,
                            require_vision=require_vision,
                            min_context=min_context,
                        )
                        if node.source in ("relay", "browser") and node.websocket:
                            data = await node.chat(
                                msgs,
                                model=resolved_model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                tools=tools,
                                thinking_mode=None,
                                project_id=project_id,
                            )
                            content = data.get("message", {}).get("content", "")
                            if content:
                                emitted_chunk = True
                                yield content
                            self._record_success(node)
                            return

                        client = await node._get_client()

                        if node.provider_type == "ollama":
                            options: dict = {"temperature": temperature}
                            if max_tokens:
                                options["num_predict"] = max_tokens
                            payload = {
                                "model": resolved_model,
                                "messages": msgs,
                                "stream": True,
                                "options": options,
                            }
                            async with client.stream(
                                "POST", "/api/chat", json=payload, timeout=None
                            ) as resp:
                                resp.raise_for_status()
                                content_filter = ThinkingContentFilter()
                                async for line in resp.aiter_lines():
                                    if line.strip():
                                        data = json.loads(line)
                                        content = content_filter.push(
                                            data.get("message", {}).get("content", "")
                                        )
                                        if content:
                                            emitted_chunk = True
                                            yield content
                                        if data.get("done", False):
                                            remaining = content_filter.flush()
                                            if remaining:
                                                emitted_chunk = True
                                                yield remaining
                                            break
                        elif node.is_anthropic:
                            data = await node.chat(
                                msgs,
                                model=resolved_model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                tools=tools,
                                thinking_mode=None,
                                project_id=project_id,
                            )
                            content = data.get("message", {}).get("content", "")
                            if content:
                                emitted_chunk = True
                                yield content
                            if data.get("message", {}).get("tool_calls"):
                                emitted_chunk = True
                                yield {
                                    "tool_calls": data["message"]["tool_calls"],
                                    "finish_reason": data.get("finish_reason", "tool_calls"),
                                }
                        else:
                            payload = {
                                "model": resolved_model,
                                "messages": msgs,
                                "temperature": temperature,
                                "stream": True,
                            }
                            if max_tokens:
                                payload["max_tokens"] = max_tokens
                            if tools:
                                payload["tools"] = tools

                            accumulated_tool_calls: list[dict] = []
                            tool_call_mode = False
                            content_filter = ThinkingContentFilter()

                            async with client.stream(
                                "POST",
                                node._openai_endpoint("chat/completions"),
                                json=payload,
                                timeout=None,
                            ) as resp:
                                resp.raise_for_status()
                                async for line in resp.aiter_lines():
                                    line = line.strip()
                                    if not line or not line.startswith("data: "):
                                        continue
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        choice = data.get("choices", [{}])[0]
                                        delta = choice.get("delta", {})
                                        finish = choice.get("finish_reason")

                                        if delta.get("tool_calls"):
                                            tool_call_mode = True
                                            for tc_delta in delta["tool_calls"]:
                                                idx = tc_delta.get("index", 0)
                                                while len(accumulated_tool_calls) <= idx:
                                                    accumulated_tool_calls.append(
                                                        {
                                                            "id": "",
                                                            "type": "function",
                                                            "function": {
                                                                "name": "",
                                                                "arguments": "",
                                                            },
                                                        }
                                                    )
                                                tc = accumulated_tool_calls[idx]
                                                if tc_delta.get("id"):
                                                    tc["id"] = tc_delta["id"]
                                                fn = tc_delta.get("function", {})
                                                if fn.get("name"):
                                                    tc["function"]["name"] = fn["name"]
                                                if fn.get("arguments"):
                                                    tc["function"]["arguments"] += fn[
                                                        "arguments"
                                                    ]
                                            continue

                                        content = content_filter.push(delta.get("content", ""))
                                        if content:
                                            emitted_chunk = True
                                            yield content

                                        if finish == "tool_calls" or (
                                            finish == "stop" and tool_call_mode
                                        ):
                                            break
                                    except (json.JSONDecodeError, IndexError, KeyError):
                                        continue

                            if accumulated_tool_calls and any(
                                tc["function"]["name"] for tc in accumulated_tool_calls
                            ):
                                emitted_chunk = True
                                yield {
                                    "tool_calls": accumulated_tool_calls,
                                    "finish_reason": "tool_calls",
                                }
                            remaining = content_filter.flush()
                            if remaining:
                                emitted_chunk = True
                                yield remaining

                        self._record_success(node)
                        return
                    except Exception as e:
                        if not emitted_chunk and _looks_like_model_availability_error(e):
                            loaded_recovery_models = [
                                name
                                for name in self._node_explicit_loaded_model_names(node)
                                if not require_vision
                                or self._node_supports_vision_model(node, name)
                            ]
                            if (
                                node.provider_type == "lmstudio"
                                and not loaded_recovery_models
                            ):
                                if lmstudio_load_recovery_used:
                                    logger.warning(
                                        "ComputeRegistry: skipped additional LM Studio "
                                        "model load on %s; one load attempt is allowed "
                                        "per stream request",
                                        node.name,
                                    )
                                    break
                                lmstudio_load_recovery_used = True
                            recovered = await self._recover_unloaded_node_model(
                                node,
                                resolved_model,
                                require_vision=require_vision,
                                min_context=min_context,
                            )
                            if recovered and attempt < TRANSIENT_CHAT_MAX_ATTEMPTS:
                                resolved_model = recovered
                                continue
                        if _looks_like_context_length_error(e):
                            recovered = await self._recover_context_node_model(
                                node,
                                resolved_model,
                                min_context=min_context,
                                require_vision=require_vision,
                            )
                            if recovered and attempt < TRANSIENT_CHAT_MAX_ATTEMPTS:
                                resolved_model = recovered
                                continue
                            logger.warning(
                                "ComputeRegistry: %s lacks required stream context "
                                "for this prompt (requested >=%s tokens); trying next node",
                                node.name,
                                min_context or "unknown",
                            )
                            break
                        self._record_failure(node, e)
                        transient = self._is_transient_error(e)
                        if (
                            not emitted_chunk
                            and attempt < TRANSIENT_CHAT_MAX_ATTEMPTS
                            and transient
                        ):
                            delay = self._retry_delay(attempt)
                            logger.warning(
                                "ComputeRegistry: transient stream failure on %s "
                                "(attempt %s/%s); retrying in %.2fs: %s",
                                node.name,
                                attempt,
                                TRANSIENT_CHAT_MAX_ATTEMPTS,
                                delay,
                                e,
                            )
                            await asyncio.sleep(delay)
                            continue

                        if hasattr(e, "response") and hasattr(e.response, "text"):
                            logger.warning(
                                "ComputeRegistry: stream failed on %s after %s "
                                "attempt(s): %s | Body: %s",
                                node.name,
                                attempt,
                                e,
                                e.response.text,
                            )
                        else:
                            logger.warning(
                                "ComputeRegistry: stream failed on %s after %s "
                                "attempt(s): %s",
                                node.name,
                                attempt,
                                e,
                            )
                        break

            except Exception as e:
                logger.warning(f"ComputeRegistry: stream failed on {node.name}: {e}")
                self._record_auxiliary_failure(node, e)
            finally:
                node.active_requests -= 1

        if require_vision:
            raise RuntimeError("No vision-capable compute nodes available for image chat")
        raise RuntimeError("No compute nodes available for streaming")

    async def embed(
        self,
        text: str,
        model: str | None = None,
        project_id: str | None = None,
    ) -> list[float]:
        """Route an embedding request."""
        for node in self._select_candidates(
            model=model,
            strict_model=settings.strict_auto_routing,
            project_id=project_id,
        ):
            if node.is_anthropic:
                continue
            node.active_requests += 1
            try:
                if node.source in ("relay", "browser") and node.websocket:
                    result = await node.embed(text, model=model, project_id=project_id)
                    self._record_success(node)
                    return result

                client = await node._get_client()
                embed_model = node._resolve_embed_model(model)

                if node.provider_type == "ollama":
                    resp = await client.post(
                        "/api/embed",
                        json={"model": embed_model, "input": text},
                    )
                else:
                    resp = await client.post(
                        node._openai_endpoint("embeddings"),
                        json={"model": embed_model, "input": text},
                    )

                resp.raise_for_status()
                data = resp.json()

                if node.provider_type == "ollama":
                    embeddings = data.get("embeddings", [])
                    self._record_success(node)
                    return embeddings[0] if embeddings else []
                else:
                    items = data.get("data", [])
                    self._record_success(node)
                    return items[0].get("embedding", []) if items else []

            except Exception as e:
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    logger.warning(
                        "ComputeRegistry: embed failed on %s: %s | Body: %s",
                        node.name,
                        e,
                        e.response.text,
                    )
                else:
                    logger.warning(f"ComputeRegistry: embed failed on {node.name}: {e}")
                self._record_auxiliary_failure(node, e)
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for embedding")

    async def embed_batch(
        self,
        texts: list[str],
        model: str | None = None,
        project_id: str | None = None,
    ) -> list[list[float]]:
        """Route a batch embedding request."""
        for node in self._select_candidates(
            model=model,
            strict_model=settings.strict_auto_routing,
            project_id=project_id,
        ):
            if node.is_anthropic:
                continue
            node.active_requests += 1
            try:
                if node.source in ("relay", "browser") and node.websocket:
                    result = await node.embed_batch(texts, model=model, project_id=project_id)
                    self._record_success(node)
                    return result

                client = await node._get_client()
                embed_model = node._resolve_embed_model(model)

                if node.provider_type == "ollama":
                    resp = await client.post(
                        "/api/embed",
                        json={"model": embed_model, "input": texts},
                    )
                    resp.raise_for_status()
                    self._record_success(node)
                    return resp.json().get("embeddings", [])
                else:
                    resp = await client.post(
                        node._openai_endpoint("embeddings"),
                        json={"model": embed_model, "input": texts},
                    )
                    resp.raise_for_status()
                    self._record_success(node)
                    return [item.get("embedding", []) for item in resp.json().get("data", [])]

            except Exception as e:
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    logger.warning(
                        "ComputeRegistry: embed_batch failed on %s: %s | Body: %s",
                        node.name,
                        e,
                        e.response.text,
                    )
                else:
                    logger.warning(f"ComputeRegistry: embed_batch failed on {node.name}: {e}")
                self._record_auxiliary_failure(node, e)
            finally:
                node.active_requests -= 1

        raise RuntimeError("No compute nodes available for batch embedding")

    async def list_models(self, project_id: str | None = None) -> list[dict]:
        """Aggregate models from nodes visible to the optional project scope."""
        all_models: list[dict] = []
        for node in self._select_candidates(project_id=project_id):
            try:
                if node.source in ("relay", "browser"):
                    for name in _unique_model_names(
                        list(node.loaded_models or []) + list(node.model_capabilities.keys())
                    ):
                        all_models.append(self._model_record_for_node(node, name))
                    continue

                client = await node._get_client()
                if node.provider_type == "ollama":
                    resp = await client.get("/api/tags", timeout=10.0)
                    data = resp.json()
                    models = data.get("models", [])
                else:
                    resp = await client.get(node._openai_endpoint("models"), timeout=10.0)
                    data = resp.json()
                    models = [{"name": m.get("id", ""), **m} for m in data.get("data", [])]
                for m in models:
                    m["_server"] = node.name
                    m["_server_id"] = node.node_id
                    model_id = m.get("id") or m.get("name")
                    if isinstance(model_id, str):
                        caps = node.model_capabilities.get(model_id)
                        if isinstance(caps, dict):
                            m.update(
                                {
                                    "supports_tools": caps.get("supports_tools", False),
                                    "supports_vision": caps.get("supports_vision", False),
                                    "supports_audio": caps.get("supports_audio", False),
                                    "supports_json": caps.get("supports_json", False),
                                    "context_length": caps.get("context_length"),
                                    "trained_context_length": caps.get(
                                        "trained_context_length"
                                    ),
                                    "loaded_context_length": caps.get("loaded_context_length"),
                                    "parameter_count": caps.get("parameter_count"),
                                    "quantization": caps.get("quantization"),
                                    "is_loaded": caps.get("is_loaded"),
                                    "endpoint_family": caps.get("endpoint_family"),
                                    "capabilities": {
                                        "tools": caps.get("supports_tools", False),
                                        "vision": caps.get("supports_vision", False),
                                        "audio": caps.get("supports_audio", False),
                                        "json": caps.get("supports_json", False),
                                    },
                                }
                            )
                all_models.extend(models)
            except Exception:
                pass
        return all_models

    @staticmethod
    def _model_record_for_node(node: ComputeNode, name: str) -> dict:
        record: dict = {
            "name": name,
            "id": name,
            "_server": node.name,
            "_server_id": node.node_id,
        }
        caps = node.model_capabilities.get(name)
        if isinstance(caps, dict):
            record.update(
                {
                    "supports_tools": caps.get("supports_tools", False),
                    "supports_vision": caps.get("supports_vision", False),
                    "supports_audio": caps.get("supports_audio", False),
                    "supports_json": caps.get("supports_json", False),
                    "context_length": caps.get("context_length"),
                    "trained_context_length": caps.get("trained_context_length"),
                    "loaded_context_length": caps.get("loaded_context_length"),
                    "parameter_count": caps.get("parameter_count"),
                    "quantization": caps.get("quantization"),
                    "is_loaded": caps.get("is_loaded"),
                    "endpoint_family": caps.get("endpoint_family"),
                    "capabilities": {
                        "tools": caps.get("supports_tools", False),
                        "vision": caps.get("supports_vision", False),
                        "audio": caps.get("supports_audio", False),
                        "json": caps.get("supports_json", False),
                    },
                }
            )
        return record

    async def list_models_async(self, project_id: str | None = None) -> list[dict]:
        """Async alias for list_models (backward compat)."""
        return await self.list_models(project_id=project_id)

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """Pull model on the first healthy Ollama node."""
        for node in self._sorted_servers():
            if node.is_healthy and node.provider_type == "ollama":
                client = await node._get_client()
                async with client.stream(
                    "POST", "/api/pull", json={"name": model_name}, timeout=None
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.strip():
                            yield json.loads(line)
                return
        yield {"status": "No Ollama server available for model pull."}

    async def ensure_model(self, model_name: str) -> bool:
        """Ensure a model is available, pull if not."""
        models = await self.list_models()
        for m in models:
            name = m.get("name", "")
            if name == model_name or name.startswith(model_name.split(":")[0]):
                return True
        async for _ in self.pull_model(model_name):
            pass
        return True

    async def close(self) -> None:
        """Close all HTTP clients."""
        for node in self._nodes.values():
            await node.close()

    # ================================================================
    # ComputePool backward-compat methods
    # ================================================================

    def alive_nodes(self) -> list[ComputeNode]:
        """Return all alive nodes (backward compat with ComputePool)."""
        return [n for n in self._nodes.values() if n.is_alive()]

    def total_capacity(self) -> int:
        """Total number of alive donated compute nodes (relay/browser)."""
        return len(
            [n for n in self._nodes.values() if n.source in ("relay", "browser") and n.is_alive()]
        )

    def available_models_list(self) -> list[str]:
        """All models available across the pool (backward compat)."""
        models: set[str] = set()
        for node in self.alive_nodes():
            models.update(node.loaded_models)
        return sorted(models)

    def best_node_for(self, model: str | None = None) -> ComputeNode | None:
        """Select the best node for a given model (backward compat)."""
        candidates = self._select_candidates(model=model)
        if not candidates:
            return None
        return candidates[0]

    # ================================================================
    # Unified Stats
    # ================================================================

    def _nodes_visible_for_project(self, project_id: str | None = None) -> list[ComputeNode]:
        if not project_id:
            return list(self._nodes.values())
        return [
            node
            for node in self._nodes.values()
            if self._node_authorized_for_project_content(node, project_id)
        ]

    def get_stats(self, project_id: str | None = None) -> dict:
        registry_nodes = self._nodes_visible_for_project(project_id)
        for node in registry_nodes:
            _hydrate_local_resources(node)
        logical_nodes = _unique_endpoint_nodes(registry_nodes)
        nodes = [n.to_dict() for n in logical_nodes]
        alive = sum(1 for n in logical_nodes if n.is_healthy)
        reachable = sum(1 for n in nodes if n.get("is_reachable"))
        all_models: set[str] = set()
        for n in logical_nodes:
            all_models.update(n.loaded_models or [])
            all_models.update(str(name) for name in n.model_capabilities.keys())
        hardware_nodes = _unique_hardware_resource_nodes(logical_nodes)
        total_ram = sum(n.ram_total_gb for n in hardware_nodes)
        avail_ram = sum(n.ram_available_gb for n in hardware_nodes)
        total_cpu = sum(n.cpu_cores for n in hardware_nodes)
        capacity = compute_capacity_envelope(logical_nodes)

        if alive >= 8:
            tier = "full_swarm"
        elif alive >= 4:
            tier = "standard"
        elif alive >= 2:
            tier = "conservative"
        elif alive >= 1:
            tier = "minimal"
        else:
            tier = "local_only"

        return {
            "total_nodes": len(nodes),
            "alive_nodes": alive,
            "ready_nodes": alive,
            "reachable_nodes": reachable,
            "hardware_node_count": len(hardware_nodes),
            "total_ram_gb": round(total_ram, 1),
            "available_ram_gb": round(avail_ram, 1),
            "total_cpu_cores": total_cpu,
            "available_models": sorted(all_models),
            "swarm_tier": tier,
            **capacity,
            "nodes": nodes,
        }

    def get_warnings(self, project_id: str | None = None) -> list[dict]:
        warnings = []
        for node in self._nodes_visible_for_project(project_id):
            for model_name, caps in node.model_capabilities.items():
                if "embed" in model_name.lower():
                    continue
                if not caps.get("supports_tools", False):
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} does not support native tool calling. "
                                "Chat will use text-based tools (less reliable)."
                            ),
                            "severity": "medium",
                        }
                    )
                ctx = caps.get("context_length", 4096)
                if ctx < 4096:
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} has a small context window "
                                f"({ctx} tokens). Complex conversations may "
                                "be truncated."
                            ),
                            "severity": "high",
                        }
                    )
                param = caps.get("parameter_count", "")
                if param in ("0.5B", "0.8B", "1B", "1.5B", "2B"):
                    warnings.append(
                        {
                            "model": model_name,
                            "server": node.name,
                            "warning": (
                                f"{model_name} ({param}) is very small for "
                                "research tasks. Consider using a 4B+ model."
                            ),
                            "severity": "low",
                        }
                    )
        return warnings
