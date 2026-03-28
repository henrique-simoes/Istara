"""Async Ollama client for model management and inference."""

import json
from typing import AsyncGenerator

import httpx

from app.config import settings


class OllamaClient:
    """Async client for the Ollama API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_host).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        """Sanitize messages for the Ollama/LM Studio API.

        Filters invalid messages, merges consecutive system messages,
        and ensures all fields are properly formatted.
        """
        sanitized = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content")
            if role not in ("system", "user", "assistant"):
                continue
            if content is None or (isinstance(content, str) and not content.strip()):
                continue
            sanitized.append({"role": role, "content": str(content)})

        # Merge consecutive system messages to avoid duplicates
        merged: list[dict] = []
        for msg in sanitized:
            if merged and msg["role"] == "system" and merged[-1]["role"] == "system":
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg)
        return merged

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[dict]:
        """List all locally available models."""
        client = await self._get_client()
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return data.get("models", [])

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """Pull a model, yielding progress updates."""
        client = await self._get_client()
        async with client.stream(
            "POST",
            "/api/pull",
            json={"name": model_name},
            timeout=None,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    yield json.loads(line)

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """Non-streaming chat completion."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        options: dict = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        payload: dict = {
            "model": model or settings.ollama_model,
            "messages": msgs,
            "stream": False,
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        client = await self._get_client()
        resp = await client.post("/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion — yields content chunks."""
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        options: dict = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        payload: dict = {
            "model": model or settings.ollama_model,
            "messages": msgs,
            "stream": True,
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        client = await self._get_client()
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

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding for a single text."""
        client = await self._get_client()
        resp = await client.post(
            "/api/embed",
            json={
                "model": model or settings.ollama_embed_model,
                "input": text,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return []

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        client = await self._get_client()
        resp = await client.post(
            "/api/embed",
            json={
                "model": model or settings.ollama_embed_model,
                "input": texts,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("embeddings", [])

    async def ensure_model(self, model_name: str) -> bool:
        """Ensure a model is available locally, pull if not."""
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]

        # Check if already present (exact match or tag match)
        for name in model_names:
            if name == model_name or name.startswith(model_name.split(":")[0]):
                return True

        # Pull the model
        async for _progress in self.pull_model(model_name):
            pass  # Could broadcast progress via WebSocket
        return True


def _create_llm_client():
    """Create the LLM client based on config."""
    if settings.llm_provider == "lmstudio":
        from app.core.lmstudio import LMStudioClient
        return LMStudioClient()
    return OllamaClient()


def _init_llm_router():
    """Initialize the LLM router with the local provider as default server."""
    from app.core.llm_router import llm_router, LLMServerEntry

    # Register the local provider
    if settings.llm_provider == "lmstudio":
        entry = LLMServerEntry(
            server_id="local-lmstudio",
            name="Local LM Studio",
            provider_type="lmstudio",
            host=settings.lmstudio_host,
            priority=1,
            is_local=True,
        )
    else:
        entry = LLMServerEntry(
            server_id="local-ollama",
            name="Local Ollama",
            provider_type="ollama",
            host=settings.ollama_host,
            priority=1,
            is_local=True,
        )
    entry.is_healthy = True  # Assume healthy at startup; health loop will verify
    llm_router.register_server(entry)

    # Also register the other local provider as fallback
    if settings.llm_provider == "lmstudio":
        fallback = LLMServerEntry(
            server_id="local-ollama",
            name="Local Ollama (fallback)",
            provider_type="ollama",
            host=settings.ollama_host,
            priority=5,
            is_local=True,
        )
    else:
        fallback = LLMServerEntry(
            server_id="local-lmstudio",
            name="Local LM Studio (fallback)",
            provider_type="lmstudio",
            host=settings.lmstudio_host,
            priority=5,
            is_local=True,
        )
    llm_router.register_server(fallback)

    # Load any persisted external servers from DB (best-effort at import time)
    _load_persisted_servers()

    return llm_router


def _load_persisted_servers():
    """Load external LLM servers from DB into the router (sync context)."""
    # This runs at import time — DB may not be ready yet.
    # The lifespan handler in main.py will also call this.
    pass


async def load_persisted_servers_async():
    """Load persisted LLM servers from DB into the live router."""
    try:
        from app.models.database import async_session
        from app.models.llm_server import LLMServer
        from app.core.llm_router import llm_router, LLMServerEntry
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(LLMServer).order_by(LLMServer.priority))
            servers = result.scalars().all()
            # Collect existing hosts to avoid duplicates
            existing_hosts = {e.host for e in llm_router._servers.values()}
            for s in servers:
                if s.id not in llm_router._servers and s.host not in existing_hosts:
                    entry = LLMServerEntry(
                        server_id=s.id,
                        name=s.name,
                        provider_type=s.provider_type,
                        host=s.host,
                        api_key=s.api_key,
                        priority=s.priority,
                        is_local=s.is_local,
                    )
                    llm_router.register_server(entry)
                    existing_hosts.add(s.host)
    except Exception:
        pass  # DB may not be initialized yet


async def auto_detect_provider() -> None:
    """Auto-detect LLM provider availability.

    Checks health of all registered servers in the LLM Router.
    The router handles failover automatically — if local is down,
    it routes to network-discovered or manually-added servers.
    """
    from app.core.llm_router import llm_router

    # Run health checks on all registered servers
    await llm_router.check_all_health()

    # Check if any server is healthy
    healthy_servers = [s for s in llm_router._servers.values() if s.is_healthy]
    if healthy_servers:
        best = healthy_servers[0]
        print(f"LLM provider available: {best.name} ({best.host})")
        return

    # Try local providers directly as last resort
    from app.core.lmstudio import LMStudioClient
    for name, client_cls, host in [
        ("lmstudio", LMStudioClient, settings.lmstudio_host),
        ("ollama", OllamaClient, settings.ollama_host),
    ]:
        try:
            client = client_cls()
            if await client.health():
                settings.llm_provider = name
                print(f"Auto-detected LLM provider: {name}")
                try:
                    from app.api.routes.settings import _persist_env
                    _persist_env("LLM_PROVIDER", name)
                except Exception:
                    pass
                await client.close()
                return
            await client.close()
        except Exception:
            pass

    print("LLM provider (lmstudio) is not reachable.")


# Create the raw client and initialize the router
_raw_client = _create_llm_client()
_init_llm_router()

# Singleton instance — delegates to unified ComputeRegistry for multi-server
# failover. All code that imports `from app.core.ollama import ollama`
# automatically gets router-based fallback to network-discovered and
# external LLM servers.
from app.core.compute_registry import compute_registry as ollama  # noqa: E402
