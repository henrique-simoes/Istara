"""Compute node transport, compatibility aliases, and provider payload helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.compute_capacity import node_capacity_score
from app.core.llm_output import strip_thinking_blocks
from app.core.llm_schema_adapter import (
    anthropic_structured_output_tool,
    normalize_anthropic_structured_tool_block,
)
from app.core.model_capabilities import ANTHROPIC_PROVIDERS, provider_auth_headers

logger = logging.getLogger("app.core.compute_registry")


class ComputeNodeTransportMixin:
    def server_id(self) -> str:
        return self.node_id

    @property
    def last_latency_ms(self) -> float:
        return self.latency_ms

    @last_latency_ms.setter
    def last_latency_ms(self, value: float) -> None:
        self.latency_ms = value

    @property
    def available_models(self) -> list:
        return self.loaded_models

    @available_models.setter
    def available_models(self, value: list) -> None:
        self.loaded_models = value

    @property
    def hostname(self) -> str:
        return self.name

    @property
    def is_anthropic(self) -> bool:
        return self.provider_type in ANTHROPIC_PROVIDERS

    def score(self) -> float:
        return node_capacity_score(self)

    def is_alive(self, timeout: float = 90) -> bool:
        """Backward compat with RelayNode.is_alive()."""
        if self.source == "relay":
            return self.last_heartbeat > 0 and (time.time() - self.last_heartbeat) < timeout
        return self.is_healthy

    # ── Circuit Breaker ──────────────────────────────────────────────

    def cb_record_success(self) -> None:
        """Record a successful LLM call — reset failure count, close breaker."""
        self.cb_failure_count = 0
        if self.cb_state == "half_open":
            self.cb_state = "closed"
            self.health_error = ""
            logger.info(f"Circuit breaker CLOSED for {self.name} — recovered")

    def cb_record_failure(self) -> None:
        """Record a failed LLM call — increment count, trip if threshold."""
        self.cb_failure_count += 1
        if self.cb_failure_count >= self.CB_FAILURE_THRESHOLD:
            self.cb_state = "open"
            self.cb_last_trip = time.time()
            self.health_error = (
                f"Circuit breaker OPEN — {self.cb_failure_count} consecutive failures"
            )
            logger.warning(
                f"Circuit breaker OPEN for {self.name} (failures={self.cb_failure_count})"
            )

    def cb_is_available(self) -> bool:
        """Check if this node can accept requests (circuit breaker check)."""
        if self.cb_state == "closed":
            return True
        if self.cb_state == "open":
            if time.time() - self.cb_last_trip > self.cb_cooldown:
                self.cb_state = "half_open"
                logger.info(f"Circuit breaker HALF_OPEN for {self.name} — probing")
                return True
            return False
        return True  # half_open allows one probe

    def cb_record_slow(self, latency_ms: float) -> None:
        """Track slow responses — warn but don't trip breaker."""
        if latency_ms > self.CB_SLOW_THRESHOLD_MS:
            self.health_state = "slow"
            self.health_error = (
                f"Slow response: {latency_ms:.0f}ms (threshold: {self.CB_SLOW_THRESHOLD_MS}ms)"
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client for this node.

        Enforces RFC 3986 trailing-slash normalization for base_url to ensure
        OpenAI-compatible relative path joining.
        """
        if self._client is None or self._client.is_closed:
            headers = provider_auth_headers(self.provider_type, self.api_key)

            # RFC 3986: Ensure base_url ends with slash for correct relative joining
            normalized_host = self.host
            if not normalized_host.endswith("/"):
                normalized_host += "/"

            self._client = httpx.AsyncClient(
                base_url=normalized_host, timeout=300.0, headers=headers
            )
        return self._client

    def _openai_endpoint(self, suffix: str) -> str:
        """Return a relative OpenAI-compatible endpoint for this node's base URL.

        Local LM Studio commonly exposes endpoints under `/v1/*`, while Google
        Gemini's OpenAI-compatible base URL already includes `/v1beta/openai/`.
        Keeping the path relative preserves any provider-specific base path.
        """
        clean_suffix = suffix.lstrip("/")
        parsed = urlparse(self.host)
        base_path = parsed.path.rstrip("/")
        if (
            self.provider_type == "gemini_openai"
            or "generativelanguage.googleapis.com" in (parsed.hostname or "")
            or base_path.endswith("/openai")
            or base_path.endswith("/v1")
        ):
            return clean_suffix
        return f"v1/{clean_suffix}"

    @staticmethod
    def _anthropic_content(content: Any) -> str | list[dict]:
        """Translate common OpenAI multimodal blocks into Anthropic content blocks."""
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return str(content)

        blocks: list[dict] = []
        for item in content:
            if not isinstance(item, dict):
                blocks.append({"type": "text", "text": str(item)})
                continue
            item_type = str(item.get("type") or "").lower()
            if item_type in {"text", "input_text"}:
                text = item.get("text") or item.get("content") or ""
                if text:
                    blocks.append({"type": "text", "text": str(text)})
                continue
            image_url = item.get("image_url") or item.get("input_image") or item.get("image")
            url = ""
            if isinstance(image_url, dict):
                url = str(image_url.get("url") or image_url.get("data") or "")
            elif isinstance(image_url, str):
                url = image_url
            if not url:
                continue
            if url.startswith("data:") and ";base64," in url:
                header, encoded = url.split(";base64,", 1)
                media_type = header.removeprefix("data:") or "image/png"
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded,
                        },
                    }
                )
            else:
                blocks.append({"type": "image", "source": {"type": "url", "url": url}})
        return blocks or ""

    @classmethod
    def _anthropic_messages(cls, messages: list[dict]) -> tuple[str, list[dict]]:
        system_parts: list[str] = []
        converted: list[dict] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                if content:
                    system_parts.append(str(content))
                continue
            if role == "tool":
                converted.append({"role": "user", "content": f"Tool result: {content}"})
                continue
            if role not in ("user", "assistant"):
                continue
            converted.append({"role": role, "content": cls._anthropic_content(content)})
        return "\n\n".join(system_parts), converted

    @staticmethod
    def _anthropic_tools(tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        converted: list[dict] = []
        for tool in tools:
            fn = tool.get("function") if isinstance(tool, dict) else None
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not name:
                continue
            converted.append(
                {
                    "name": name,
                    "description": fn.get("description", ""),
                    "input_schema": fn.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                }
            )
        return converted or None

    @classmethod
    def _anthropic_payload(
        cls,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int | None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> dict:
        system_text, converted_messages = cls._anthropic_messages(messages)
        payload: dict = {
            "model": model,
            "messages": converted_messages,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
        }
        if system_text:
            payload["system"] = system_text
        converted_tools = cls._anthropic_tools(tools)
        structured_tool = anthropic_structured_output_tool(response_format)
        if structured_tool:
            converted_tools = [*(converted_tools or []), structured_tool]
            payload["tool_choice"] = {"type": "tool", "name": structured_tool["name"]}
        if converted_tools:
            payload["tools"] = converted_tools
        return payload

    @staticmethod
    def _normalize_anthropic_response(data: dict) -> dict:
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        for block in data.get("content", []) if isinstance(data, dict) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
            elif block.get("type") == "tool_use":
                structured_payload = normalize_anthropic_structured_tool_block(block)
                if structured_payload is not None:
                    text_parts.append(structured_payload)
                    continue
                tool_calls.append(
                    {
                        "id": block.get("id") or "",
                        "type": "function",
                        "function": {
                            "name": block.get("name") or "",
                            "arguments": json.dumps(block.get("input") or {}),
                        },
                    }
                )
        result: dict = {
            "message": {
                "role": "assistant",
                "content": strip_thinking_blocks("".join(text_parts)).strip(),
            }
        }
        if tool_calls:
            result["message"]["tool_calls"] = tool_calls
            result["finish_reason"] = "tool_calls"
        if isinstance(data.get("usage"), dict) and data["usage"]:
            result["usage"] = dict(data["usage"])
        return result

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def fail_pending_requests(self, reason: str) -> None:
        """Fail in-flight relay/browser requests when the websocket disappears."""
        for request_id, future in list(self.pending_requests.items()):
            if future and not future.done():
                future.set_exception(RuntimeError(reason))
            self.pending_requests.pop(request_id, None)

    async def _request_over_websocket(self, request_type: str, payload: dict) -> dict:
        """Send a request to a relay/browser donor over its outbound websocket."""
        if self.source not in ("relay", "browser") or not self.websocket:
            raise RuntimeError("Node is not connected over relay websocket")

        request_id = f"relay-{uuid.uuid4()}"
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[request_id] = future
        await self.websocket.send_json(
            {
                "type": request_type,
                "request_id": request_id,
                **payload,
            }
        )
        try:
            response = await asyncio.wait_for(future, timeout=self.relay_request_timeout_s)
        except TimeoutError as exc:
            self.health_error = f"Relay request timed out after {self.relay_request_timeout_s:.0f}s"
            raise RuntimeError(self.health_error) from exc
        finally:
            self.pending_requests.pop(request_id, None)

        if response.get("error"):
            self.health_error = str(response["error"])
            raise RuntimeError(self.health_error)
        self.health_error = ""
        return response
