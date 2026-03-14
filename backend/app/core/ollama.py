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
    ) -> dict:
        """Non-streaming chat completion."""
        payload: dict = {
            "model": model or settings.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}, *messages]

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
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion — yields content chunks."""
        payload: dict = {
            "model": model or settings.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}, *messages]

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


# Singleton instance
ollama = OllamaClient()
