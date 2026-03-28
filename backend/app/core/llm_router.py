"""LLM Router — routes requests to the best available LLM server.

Maintains the same interface as OllamaClient/LMStudioClient so all existing
code works unchanged. Routes to local Ollama/LM Studio first, then external
servers, with automatic failover.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMServerEntry:
    """A registered LLM server that the router can send requests to."""

    def __init__(
        self,
        server_id: str,
        name: str,
        provider_type: str,
        host: str,
        api_key: str = "",
        priority: int = 10,
        is_local: bool = True,
    ):
        self.server_id = server_id
        self.name = name
        self.provider_type = provider_type  # ollama | lmstudio | openai_compat
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.priority = priority
        self.is_local = is_local
        self.is_healthy = False
        self.last_latency_ms: float = 0
        self.available_models: list[str] = []
        self.model_capabilities: dict = {}  # model_name -> ModelCapability.to_dict()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.host, timeout=300.0, headers=headers
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def check_health(self) -> bool:
        """Probe the server health endpoint and discover available models."""
        try:
            client = await self._get_client()
            start = time.time()
            if self.provider_type == "ollama":
                resp = await client.get("/api/tags", timeout=10.0)
            else:
                resp = await client.get("/v1/models", timeout=10.0)
            self.last_latency_ms = (time.time() - start) * 1000
            self.is_healthy = resp.status_code == 200
            # Extract available models
            if self.is_healthy:
                try:
                    data = resp.json()
                    if self.provider_type == "ollama":
                        self.available_models = [m.get("name", "") for m in data.get("models", [])]
                    else:
                        self.available_models = [m.get("id", "") for m in data.get("data", [])]
                except Exception:
                    pass
        except Exception:
            self.is_healthy = False
            self.last_latency_ms = 9999
        return self.is_healthy

    def _resolve_model(self, model: str | None) -> str:
        """Resolve the model name — use what's available on this server."""
        if model and model != "default":
            # Check if the requested model is available on this server
            if self.available_models and model not in self.available_models:
                # Model not available — pick the best available non-embedding model
                non_embed = [m for m in self.available_models if "embed" not in m.lower()]
                if non_embed:
                    return non_embed[0]
            return model
        # No model specified — use the first available non-embedding model
        if self.available_models:
            non_embed = [m for m in self.available_models if "embed" not in m.lower()]
            if non_embed:
                return non_embed[0]
        # Fallback to configured settings
        if self.provider_type == "ollama":
            return settings.ollama_model
        return settings.lmstudio_model

    def _resolve_embed_model(self, model: str | None) -> str:
        """Resolve embedding model — prefer embedding-specific models."""
        if model and model != "default":
            return model
        # Look for an embedding model in available models
        if self.available_models:
            embed_models = [m for m in self.available_models if "embed" in m.lower()]
            if embed_models:
                return embed_models[0]
        # Fallback to configured settings
        if self.provider_type == "ollama":
            return settings.ollama_embed_model
        return settings.lmstudio_embed_model

    async def chat(self, messages: list[dict], model: str | None = None,
                   temperature: float = 0.7, max_tokens: int | None = None,
                   tools: list[dict] | None = None) -> dict:
        """Send a chat completion request.

        When *tools* is provided and the provider is OpenAI-compatible the
        tools are included in the payload for native function calling.
        """
        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": self._resolve_model(model),
                "messages": messages,
                "stream": False,
                "options": options,
            }
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
        else:
            # OpenAI-compatible (LM Studio, external)
            payload = {
                "model": self._resolve_model(model),
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = tools
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            message = choice["message"]

            result: dict = {
                "message": {
                    "role": "assistant",
                    "content": message.get("content") or "",
                }
            }
            if message.get("tool_calls"):
                result["message"]["tool_calls"] = message["tool_calls"]
                result["finish_reason"] = choice.get("finish_reason", "tool_calls")
            return result

    async def chat_stream(self, messages: list[dict], model: str | None = None,
                          temperature: float = 0.7, max_tokens: int | None = None,
                          tools: list[dict] | None = None) -> AsyncGenerator[str | dict, None]:
        """Stream a chat completion.

        Yields ``str`` content chunks for regular responses.  When the
        model invokes native tools the stream yields a single ``dict``
        with ``{"tool_calls": [...], "finish_reason": "tool_calls"}``.
        """
        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": model or settings.ollama_model,
                "messages": messages,
                "stream": True,
                "options": options,
            }
            async with client.stream("POST", "/api/chat", json=payload, timeout=None) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            return
        else:
            payload = {
                "model": self._resolve_model(model),
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = tools

            # Accumulate tool_calls across streamed deltas
            accumulated_tool_calls: list[dict] = []
            tool_call_mode = False

            async with client.stream("POST", "/v1/chat/completions", json=payload, timeout=None) as resp:
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

                        # Handle tool call deltas
                        if delta.get("tool_calls"):
                            tool_call_mode = True
                            for tc_delta in delta["tool_calls"]:
                                idx = tc_delta.get("index", 0)
                                while len(accumulated_tool_calls) <= idx:
                                    accumulated_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    })
                                tc = accumulated_tool_calls[idx]
                                if tc_delta.get("id"):
                                    tc["id"] = tc_delta["id"]
                                fn = tc_delta.get("function", {})
                                if fn.get("name"):
                                    tc["function"]["name"] = fn["name"]
                                if fn.get("arguments"):
                                    tc["function"]["arguments"] += fn["arguments"]
                            continue

                        content = delta.get("content", "")
                        if content:
                            yield content

                        if finish == "tool_calls" or (finish == "stop" and tool_call_mode):
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            # Yield accumulated tool calls
            if accumulated_tool_calls and any(tc["function"]["name"] for tc in accumulated_tool_calls):
                yield {
                    "tool_calls": accumulated_tool_calls,
                    "finish_reason": "tool_calls",
                }

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding."""
        client = await self._get_client()

        if self.provider_type == "ollama":
            resp = await client.post(
                "/api/embed",
                json={"model": self._resolve_embed_model(model), "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            return embeddings[0] if embeddings else []
        else:
            embed_model = self._resolve_embed_model(model)
            resp = await client.post(
                "/v1/embeddings",
                json={"model": embed_model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            return items[0].get("embedding", []) if items else []

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        client = await self._get_client()

        if self.provider_type == "ollama":
            resp = await client.post(
                "/api/embed",
                json={"model": self._resolve_embed_model(model), "input": texts},
            )
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
        else:
            resp = await client.post(
                "/v1/embeddings",
                json={"model": self._resolve_embed_model(model), "input": texts},
            )
            resp.raise_for_status()
            return [item.get("embedding", []) for item in resp.json().get("data", [])]


class LLMRouter:
    """Routes LLM requests to the best available server with failover.

    Exposes the same interface as OllamaClient so it's a drop-in replacement.
    """

    def __init__(self):
        self._servers: dict[str, LLMServerEntry] = {}
        self._health_task: asyncio.Task | None = None

    def register_server(self, entry: LLMServerEntry) -> None:
        self._servers[entry.server_id] = entry
        logger.info(f"LLM Router: registered server '{entry.name}' ({entry.provider_type} @ {entry.host})")

    def unregister_server(self, server_id: str) -> None:
        entry = self._servers.pop(server_id, None)
        if entry:
            asyncio.ensure_future(entry.close())
            logger.info(f"LLM Router: unregistered server '{entry.name}'")

    def list_servers(self) -> list[dict]:
        return [
            {
                "id": s.server_id,
                "name": s.name,
                "provider_type": s.provider_type,
                "host": s.host,
                "is_local": s.is_local,
                "is_healthy": s.is_healthy,
                "priority": s.priority,
                "last_latency_ms": s.last_latency_ms,
            }
            for s in sorted(self._servers.values(), key=lambda s: s.priority)
        ]

    def _sorted_servers(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
    ) -> list[LLMServerEntry]:
        """Get servers sorted by priority (lower = better), healthy first.

        Optional capability filters narrow the candidate list. If no server
        matches the filter, all servers are returned as a fallback so that
        routing still proceeds.
        """
        servers = list(self._servers.values())
        if require_tools:
            filtered = [
                s for s in servers
                if any(c.get("supports_tools") for c in s.model_capabilities.values())
            ]
            if filtered:
                servers = filtered
        if require_vision:
            filtered = [
                s for s in servers
                if any(c.get("supports_vision") for c in s.model_capabilities.values())
            ]
            if filtered:
                servers = filtered
        if min_context > 0:
            filtered = [
                s for s in servers
                if any(c.get("context_length", 0) >= min_context for c in s.model_capabilities.values())
            ]
            if filtered:
                servers = filtered
        return sorted(
            servers,
            key=lambda s: (not s.is_healthy, s.priority, s.last_latency_ms or 999),
        )

    async def health(self) -> bool:
        """True if any server is healthy."""
        return any(s.is_healthy for s in self._servers.values())

    async def check_all_health(self) -> dict[str, bool]:
        """Run health checks on all servers and detect model capabilities."""
        results = {}
        for sid, server in self._servers.items():
            results[sid] = await server.check_health()
            # After health check, detect capabilities for healthy servers
            if server.is_healthy:
                try:
                    from app.core.model_capabilities import (
                        detect_capabilities_lmstudio,
                        detect_capabilities_ollama,
                    )
                    if server.provider_type == "ollama":
                        caps = await detect_capabilities_ollama(server.host)
                    else:
                        caps = await detect_capabilities_lmstudio(server.host)
                    server.model_capabilities = {
                        k: v.to_dict() for k, v in caps.items()
                    }
                except Exception as e:
                    logger.debug(f"Model capability detection failed for {server.name}: {e}")
        return results

    async def start_health_loop(self, interval: int = 60):
        """Background health check loop."""
        while True:
            try:
                await self.check_all_health()
            except Exception as e:
                logger.error(f"LLM Router health check error: {e}")
            await asyncio.sleep(interval)

    # --- Proxy methods (same interface as OllamaClient) ---

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        sanitized = []
        for msg in messages:
            role = msg.get("role", "")

            # Pass through tool-result messages verbatim
            if role == "tool":
                entry = {"role": "tool", "content": str(msg.get("content", ""))}
                if msg.get("tool_call_id"):
                    entry["tool_call_id"] = msg["tool_call_id"]
                sanitized.append(entry)
                continue

            # Pass through assistant messages that carry tool_calls
            if role == "assistant" and msg.get("tool_calls"):
                entry_a: dict = {"role": "assistant", "content": msg.get("content") or ""}
                entry_a["tool_calls"] = msg["tool_calls"]
                sanitized.append(entry_a)
                continue

            if role not in ("system", "user", "assistant"):
                continue
            content = msg.get("content")
            if content is None or (isinstance(content, str) and not content.strip()):
                continue
            sanitized.append({"role": role, "content": str(content)})
        merged: list[dict] = []
        for msg in sanitized:
            if merged and msg["role"] == "system" and merged[-1]["role"] == "system":
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg)
        return merged

    async def chat(self, messages: list[dict], model: str | None = None,
                   system: str | None = None, temperature: float = 0.7,
                   max_tokens: int | None = None,
                   tools: list[dict] | None = None) -> dict:
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for server in self._sorted_servers(require_tools=bool(tools)):
            if not server.is_healthy:
                continue
            try:
                logger.info(f"LLM Router: routing chat to {server.name} ({server.host})")
                return await server.chat(msgs, model=model, temperature=temperature,
                                         max_tokens=max_tokens, tools=tools)
            except Exception as e:
                logger.warning(f"LLM Router: chat failed on {server.name}: {e}")
                server.is_healthy = False

        raise RuntimeError("No healthy LLM servers available")

    async def chat_stream(self, messages: list[dict], model: str | None = None,
                          system: str | None = None, temperature: float = 0.7,
                          max_tokens: int | None = None,
                          tools: list[dict] | None = None) -> AsyncGenerator[str | dict, None]:
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for server in self._sorted_servers(require_tools=bool(tools)):
            if not server.is_healthy:
                continue
            try:
                logger.info(f"LLM Router: routing stream to {server.name} ({server.host})")
                async for chunk in server.chat_stream(msgs, model=model, temperature=temperature,
                                                      max_tokens=max_tokens, tools=tools):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"LLM Router: stream failed on {server.name}: {e}")
                server.is_healthy = False

        raise RuntimeError("No healthy LLM servers available")

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        for server in self._sorted_servers():
            if not server.is_healthy:
                continue
            try:
                return await server.embed(text, model=model)
            except Exception as e:
                logger.warning(f"LLM Router: embed failed on {server.name}: {e}")
                server.is_healthy = False
        raise RuntimeError("No healthy LLM servers available for embedding")

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        for server in self._sorted_servers():
            if not server.is_healthy:
                continue
            try:
                return await server.embed_batch(texts, model=model)
            except Exception as e:
                logger.warning(f"LLM Router: embed_batch failed on {server.name}: {e}")
                server.is_healthy = False
        raise RuntimeError("No healthy LLM servers available for embedding")

    async def list_models(self) -> list[dict]:
        """Aggregate models from all healthy servers."""
        all_models: list[dict] = []
        for server in self._sorted_servers():
            if not server.is_healthy:
                continue
            try:
                client = await server._get_client()
                if server.provider_type == "ollama":
                    resp = await client.get("/api/tags", timeout=10.0)
                    data = resp.json()
                    models = data.get("models", [])
                else:
                    resp = await client.get("/v1/models", timeout=10.0)
                    data = resp.json()
                    models = [{"name": m.get("id", ""), **m} for m in data.get("data", [])]
                for m in models:
                    m["_server"] = server.name
                    m["_server_id"] = server.server_id
                all_models.extend(models)
            except Exception:
                pass
        return all_models

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """Pull model on the first healthy Ollama server."""
        for server in self._sorted_servers():
            if server.is_healthy and server.provider_type == "ollama":
                client = await server._get_client()
                async with client.stream("POST", "/api/pull", json={"name": model_name}, timeout=None) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.strip():
                            yield json.loads(line)
                return
        yield {"status": "No Ollama server available for model pull."}

    async def ensure_model(self, model_name: str) -> bool:
        models = await self.list_models()
        for m in models:
            name = m.get("name", "")
            if name == model_name or name.startswith(model_name.split(":")[0]):
                return True
        async for _ in self.pull_model(model_name):
            pass
        return True

    async def close(self):
        for server in self._servers.values():
            await server.close()


# Singleton
llm_router = LLMRouter()
