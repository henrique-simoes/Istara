"""Compute node chat, stream, embedding, and serialization paths."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

from app.config import settings
from app.core.llm_output import (
    ThinkingContentFilter,
    visible_assistant_content,
    visible_assistant_message,
)
from app.core.llm_schema_adapter import provider_response_format_fields
from app.core.llm_thinking import apply_thinking_control

class ComputeNodeInvocationMixin:
    def _authorized_project_for_content_dispatch(self, project_id: str | None) -> str | None:
        if self.source not in ("relay", "browser"):
            return project_id

        requested_project = str(project_id or "").strip()
        if not requested_project:
            raise RuntimeError("project_id is required for donated compute dispatch")

        allowed = {
            str(pid).strip()
            for pid in getattr(self, "allowed_project_ids", []) or []
            if str(pid).strip()
        }
        if "*" not in allowed and requested_project not in allowed:
            raise RuntimeError("Donated compute node is not authorized for this project")
        return requested_project

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
        """Direct chat on this specific node (backward compat with LLMServerEntry.chat)."""
        project_id = self._authorized_project_for_content_dispatch(project_id)
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = apply_thinking_control(msgs, thinking_mode)

        if self.source in ("relay", "browser") and self.websocket:
            response = await self._request_over_websocket(
                "llm_request",
                {
                    "messages": msgs,
                    "model": self._resolve_model(model),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "tools": tools,
                    "response_format": response_format,
                    "thinking_mode": thinking_mode,
                    "project_id": project_id,
                },
            )
            return response.get("result", {})

        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": self._resolve_model(model),
                "messages": msgs,
                "stream": False,
                "options": options,
            }
            if response_format:
                payload.update(provider_response_format_fields(self.provider_type, response_format))
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message")
            if isinstance(message, dict):
                data["message"] = visible_assistant_message(message)
            return data
        elif self.is_anthropic:
            payload = self._anthropic_payload(
                msgs,
                self._resolve_model(model),
                temperature,
                max_tokens,
                tools,
                response_format,
            )
            resp = await client.post(self._openai_endpoint("messages"), json=payload)
            resp.raise_for_status()
            return self._normalize_anthropic_response(resp.json())
        else:
            payload = {
                "model": self._resolve_model(model),
                "messages": msgs,
                "temperature": temperature,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = tools
            if response_format:
                payload.update(provider_response_format_fields(self.provider_type, response_format))
            resp = await client.post(self._openai_endpoint("chat/completions"), json=payload)
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
            return result

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
        """Direct streaming chat on this specific node (backward compat)."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = apply_thinking_control(msgs, thinking_mode)

        if self.source in ("relay", "browser") and self.websocket:
            result = await self.chat(
                msgs,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                thinking_mode=None,
                project_id=project_id,
            )
            content = result.get("message", {}).get("content", "")
            if content:
                yield content
            return

        client = await self._get_client()

        if self.is_anthropic:
            result = await self.chat(
                msgs,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                thinking_mode=None,
                project_id=project_id,
            )
            content = result.get("message", {}).get("content", "")
            if content:
                yield content
            if result.get("message", {}).get("tool_calls"):
                yield {
                    "tool_calls": result["message"]["tool_calls"],
                    "finish_reason": result.get("finish_reason", "tool_calls"),
                }
            return

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": model or settings.ollama_model,
                "messages": msgs,
                "stream": True,
                "options": options,
            }
            async with client.stream("POST", "/api/chat", json=payload, timeout=None) as resp:
                resp.raise_for_status()
                content_filter = ThinkingContentFilter()
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = content_filter.push(data.get("message", {}).get("content", ""))
                        if content:
                            yield content
                        if data.get("done", False):
                            remaining = content_filter.flush()
                            if remaining:
                                yield remaining
                            return
        else:
            payload = {
                "model": self._resolve_model(model),
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
                "POST", self._openai_endpoint("chat/completions"), json=payload, timeout=None
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
                                            "function": {"name": "", "arguments": ""},
                                        }
                                    )
                                tc = accumulated_tool_calls[idx]
                                if tc_delta.get("id"):
                                    tc["id"] = tc_delta["id"]
                                fn = tc_delta.get("function", {})
                                if fn.get("name"):
                                    tc["function"]["name"] = fn["name"]
                                if fn.get("arguments"):
                                    tc["function"]["arguments"] += fn["arguments"]
                            continue

                        content = content_filter.push(delta.get("content", ""))
                        if content:
                            yield content

                        if finish == "tool_calls" or (finish == "stop" and tool_call_mode):
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            remaining = content_filter.flush()
            if remaining:
                yield remaining

            if accumulated_tool_calls and any(
                tc["function"]["name"] for tc in accumulated_tool_calls
            ):
                yield {
                    "tool_calls": accumulated_tool_calls,
                    "finish_reason": "tool_calls",
                }

    async def embed(
        self,
        text: str,
        model: str | None = None,
        project_id: str | None = None,
    ) -> list[float]:
        """Direct embedding on this specific node (backward compat)."""
        project_id = self._authorized_project_for_content_dispatch(project_id)
        if self.source in ("relay", "browser") and self.websocket:
            response = await self._request_over_websocket(
                "embed_request",
                {
                    "input": text,
                    "model": self._resolve_embed_model(model),
                    "project_id": project_id,
                },
            )
            result = response.get("result", [])
            return result if isinstance(result, list) else []

        client = await self._get_client()
        embed_model = self._resolve_embed_model(model)
        if self.is_anthropic:
            raise RuntimeError("Anthropic-compatible servers do not expose Istara embeddings")

        if self.provider_type == "ollama":
            resp = await client.post("/api/embed", json={"model": embed_model, "input": text})
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])
            return embeddings[0] if embeddings else []
        else:
            resp = await client.post(
                self._openai_endpoint("embeddings"),
                json={"model": embed_model, "input": text},
            )
            resp.raise_for_status()
            items = resp.json().get("data", [])
            return items[0].get("embedding", []) if items else []

    async def embed_batch(
        self,
        texts: list[str],
        model: str | None = None,
        project_id: str | None = None,
    ) -> list[list[float]]:
        """Direct batch embedding on this specific node (backward compat)."""
        project_id = self._authorized_project_for_content_dispatch(project_id)
        if self.source in ("relay", "browser") and self.websocket:
            response = await self._request_over_websocket(
                "embed_request",
                {
                    "input": texts,
                    "model": self._resolve_embed_model(model),
                    "project_id": project_id,
                },
            )
            result = response.get("result", [])
            return result if isinstance(result, list) else []

        client = await self._get_client()
        embed_model = self._resolve_embed_model(model)
        if self.is_anthropic:
            raise RuntimeError("Anthropic-compatible servers do not expose Istara embeddings")

        if self.provider_type == "ollama":
            resp = await client.post("/api/embed", json={"model": embed_model, "input": texts})
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
        else:
            resp = await client.post(
                self._openai_endpoint("embeddings"),
                json={"model": embed_model, "input": texts},
            )
            resp.raise_for_status()
            return [item.get("embedding", []) for item in resp.json().get("data", [])]

    def to_dict(self) -> dict:
        capability_probe_status = "not_applicable"
        if self.source in ("relay", "browser"):
            capability_probe_status = "available" if self.model_capabilities else "unavailable"
        elif self.model_capabilities:
            capability_probe_status = "available"
        reachable_states = {
            "ready",
            "no_model_loaded",
            "auth_required",
            "degraded",
            "slow",
        }
        is_reachable = bool(self.is_healthy or self.health_state in reachable_states)
        if self.health_state in {"unreachable", "timeout"}:
            is_reachable = False
        readiness_state = self.health_state or "unknown"
        if self.is_healthy and readiness_state in {"unknown", "unhealthy"}:
            readiness_state = "ready"
        model_list_stale = bool(
            self.source in ("relay", "browser")
            and self.last_heartbeat
            and (time.time() - self.last_heartbeat) > 60
        )
        return {
            "node_id": self.node_id,
            "hostname": self.name,
            "name": self.name,
            "host": self.host,
            "source": self.source,
            "provider_type": self.provider_type,
            "state": self.health_state,
            "serving_state": "serving" if self.is_healthy and self.websocket else self.health_state,
            "readiness_state": readiness_state,
            "health_error": self.health_error,
            "capability_probe_status": capability_probe_status,
            "model_list_stale": model_list_stale,
            "last_heartbeat": self.last_heartbeat,
            "is_healthy": self.is_healthy,
            "is_ready": self.is_healthy,
            "is_reachable": is_reachable,
            "online": is_reachable,
            "is_local": self.is_local,
            "priority": self.priority,
            "latency_ms": self.latency_ms,
            "active_requests": self.active_requests,
            "score": round(self.score(), 1) if self.score() >= 0 else 0,
            "alive": self.is_healthy,
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "cpu_cores": self.cpu_cores,
            "cpu_load_pct": self.cpu_load_pct,
            "gpu_name": self.gpu_name,
            "loaded_models": self.loaded_models,
            "model_capabilities": self.model_capabilities,
        }
