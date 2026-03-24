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
        """Probe the server health endpoint."""
        try:
            client = await self._get_client()
            start = time.time()
            if self.provider_type == "ollama":
                resp = await client.get("/api/tags", timeout=10.0)
            else:
                resp = await client.get("/v1/models", timeout=10.0)
            self.last_latency_ms = (time.time() - start) * 1000
            self.is_healthy = resp.status_code == 200
        except Exception:
            self.is_healthy = False
            self.last_latency_ms = 9999
        return self.is_healthy

    async def chat(self, messages: list[dict], model: str | None = None,
                   temperature: float = 0.7, max_tokens: int | None = None) -> dict:
        """Send a chat completion request."""
        client = await self._get_client()

        if self.provider_type == "ollama":
            options: dict = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": model or settings.ollama_model,
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
                "model": model or settings.lmstudio_model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"message": {"role": "assistant", "content": content}}

    async def chat_stream(self, messages: list[dict], model: str | None = None,
                          temperature: float = 0.7, max_tokens: int | None = None) -> AsyncGenerator[str, None]:
        """Stream a chat completion."""
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
                "model": model or settings.lmstudio_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            async with client.stream("POST", "/v1/chat/completions", json=payload, timeout=None) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding."""
        client = await self._get_client()

        if self.provider_type == "ollama":
            resp = await client.post(
                "/api/embed",
                json={"model": model or settings.ollama_embed_model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            return embeddings[0] if embeddings else []
        else:
            embed_model = model or settings.lmstudio_embed_model
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
                json={"model": model or settings.ollama_embed_model, "input": texts},
            )
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
        else:
            resp = await client.post(
                "/v1/embeddings",
                json={"model": model or settings.lmstudio_embed_model, "input": texts},
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

    def _sorted_servers(self) -> list[LLMServerEntry]:
        """Get servers sorted by priority (lower = better), healthy first."""
        return sorted(
            self._servers.values(),
            key=lambda s: (not s.is_healthy, s.priority, s.last_latency_ms),
        )

    async def health(self) -> bool:
        """True if any server is healthy."""
        return any(s.is_healthy for s in self._servers.values())

    async def check_all_health(self) -> dict[str, bool]:
        """Run health checks on all servers."""
        results = {}
        for sid, server in self._servers.items():
            results[sid] = await server.check_health()
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
            content = msg.get("content")
            if role not in ("system", "user", "assistant"):
                continue
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
                   max_tokens: int | None = None) -> dict:
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for server in self._sorted_servers():
            if not server.is_healthy:
                continue
            try:
                return await server.chat(msgs, model=model, temperature=temperature, max_tokens=max_tokens)
            except Exception as e:
                logger.warning(f"LLM Router: chat failed on {server.name}: {e}")
                server.is_healthy = False

        raise RuntimeError("No healthy LLM servers available")

    async def chat_stream(self, messages: list[dict], model: str | None = None,
                          system: str | None = None, temperature: float = 0.7,
                          max_tokens: int | None = None) -> AsyncGenerator[str, None]:
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        for server in self._sorted_servers():
            if not server.is_healthy:
                continue
            try:
                async for chunk in server.chat_stream(msgs, model=model, temperature=temperature, max_tokens=max_tokens):
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
