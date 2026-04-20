"""Async LM Studio client — OpenAI-compatible API for inference and embeddings."""

import json
import time
from typing import AsyncGenerator

import httpx

from app.config import settings


class LMStudioClient:
    """Async client for LM Studio's OpenAI-compatible API.

    Exposes the same interface as OllamaClient so callers need no changes.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.lmstudio_host).rstrip("/")
        self._client: httpx.AsyncClient | None = None
        # Cache for detect_loaded_model (avoids probing on every API call)
        self._detected_model: str | None = None
        self._detected_at: float = 0.0
        self._detect_cache_ttl: float = 60.0  # seconds

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health(self) -> bool:
        """Check if LM Studio is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/v1/models")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[dict]:
        """List all available models (downloaded in LM Studio)."""
        client = await self._get_client()
        resp = await client.get("/v1/models")
        resp.raise_for_status()
        data = resp.json()
        # Normalize to Ollama-like format: [{"name": "...", ...}]
        models = data.get("data", [])
        return [{"name": m.get("id", ""), **m} for m in models]

    async def detect_loaded_model(self, force: bool = False) -> str | None:
        """Detect the actually loaded model via a minimal chat probe.

        LM Studio's /v1/models returns ALL downloaded models, not just loaded ones.
        The only reliable way to detect the loaded model is a minimal chat request —
        the response includes a 'model' field with the model that actually served it.

        Results are cached for 60 seconds to avoid slowing down every API call.
        Pass ``force=True`` to bypass the cache (e.g. on startup).
        """
        # Return cached result if still fresh
        if (
            not force
            and self._detected_model
            and (time.time() - self._detected_at) < self._detect_cache_ttl
        ):
            return self._detected_model

        try:
            client = await self._get_client()
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                    "stream": False,
                },
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                model = data.get("model")
                if model:
                    self._detected_model = model
                    self._detected_at = time.time()
                return model
        except Exception:
            pass
        return self._detected_model  # Return stale cache on error

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """No-op for LM Studio — models are managed via the GUI."""
        yield {"status": "LM Studio models are managed through the application UI."}

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        """Sanitize messages for OpenAI-compatible API.

        Filters invalid messages, merges consecutive system messages,
        and ensures all fields are properly formatted.  Passes through
        ``role: "tool"`` and ``role: "assistant"`` messages with
        ``tool_calls`` intact for native function calling.
        """
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
                entry: dict = {"role": "assistant", "content": msg.get("content") or ""}
                entry["tool_calls"] = msg["tool_calls"]
                sanitized.append(entry)
                continue

            if role not in ("system", "user", "assistant"):
                continue
            content = msg.get("content")
            if content is None or (isinstance(content, str) and not content.strip()):
                continue
            sanitized.append({"role": role, "content": str(content)})

        # Merge consecutive system messages
        merged: list[dict] = []
        for msg in sanitized:
            if merged and msg["role"] == "system" and merged[-1]["role"] == "system":
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(msg)
        return merged

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> dict:
        """Non-streaming chat completion.

        Returns Ollama-compatible format: ``{"message": {"content": "..."}}``.
        When the model invokes native tools the response also contains
        ``"tool_calls"`` and ``"finish_reason"``.
        """
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        payload: dict = {
            "model": model or settings.lmstudio_model,
            "messages": msgs,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        client = await self._get_client()
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

        # Include tool_calls if the model invoked native tools
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
        response_format: dict | None = None,
    ) -> AsyncGenerator[str | dict, None]:
        """Streaming chat completion — yields content chunks (str).

        When the model invokes native tools the stream yields a single
        ``dict`` of the form ``{"tool_calls": [...], "finish_reason": "tool_calls"}``
        instead of text content.  Callers must check the type of each
        yielded value.
        """
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        msgs = self._sanitize_messages(msgs)

        payload: dict = {
            "model": model or settings.lmstudio_model,
            "messages": msgs,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        client = await self._get_client()

        # Accumulate tool_calls across streamed deltas (LM Studio may
        # stream tool calls in multiple chunks or as a single chunk).
        accumulated_tool_calls: list[dict] = []
        tool_call_mode = False

        async with client.stream(
            "POST", "/v1/chat/completions", json=payload, timeout=None
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]  # strip "data: " prefix
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
                            # Grow the list to accommodate the index
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

                    # Regular content delta
                    content = delta.get("content", "")
                    if content:
                        yield content

                    # Check if we reached the end with tool calls
                    if finish == "tool_calls" or (finish == "stop" and tool_call_mode):
                        break

                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

        # If we accumulated tool calls, yield them as a structured dict
        if accumulated_tool_calls and any(tc["function"]["name"] for tc in accumulated_tool_calls):
            yield {
                "tool_calls": accumulated_tool_calls,
                "finish_reason": "tool_calls",
            }

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding for a single text."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/embeddings",
            json={
                "model": model or settings.lmstudio_embed_model,
                "input": text,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("data", [])
        if embeddings:
            return embeddings[0].get("embedding", [])
        return []

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/embeddings",
            json={
                "model": model or settings.lmstudio_embed_model,
                "input": texts,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [item.get("embedding", []) for item in data.get("data", [])]

    async def ensure_model(self, model_name: str) -> bool:
        """Check if a model is loaded. LM Studio models are managed via GUI."""
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        for name in model_names:
            if name == model_name or model_name in name:
                return True
        return False
