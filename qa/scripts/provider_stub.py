"""Deterministic, non-model Ollama-compatible QA provider stub.

The public QA contract needs the product backend to exercise its real startup,
provider, and vector-space guards without depending on a model server. This
stub implements only the bounded wire surface needed by those paths. It never
loads a model, emits request content, or makes outbound requests.
"""

from __future__ import annotations

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


CHAT_MODEL = os.environ.get("QA_CONTRACT_CHAT_MODEL", "istara-qa-contract-chat:latest")
EMBED_MODEL = os.environ.get(
    "QA_CONTRACT_EMBED_MODEL", "istara-qa-contract-embed:latest"
)
EMBEDDING_DIMENSION = 8


def embedding_for_text(text: str) -> list[float]:
    """Return a stable, finite contract-only vector for one source string."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [
        round((digest[index] - 127.5) / 127.5, 8)
        for index in range(EMBEDDING_DIMENSION)
    ]


def embeddings_for_input(value: Any) -> list[list[float]]:
    if isinstance(value, str):
        return [embedding_for_text(value)]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [embedding_for_text(item) for item in value]
    raise ValueError("input must be a string or list of strings")


def model_records() -> list[dict[str, Any]]:
    return [
        {"name": CHAT_MODEL, "model": CHAT_MODEL, "details": {"family": "qa-contract"}},
        {
            "name": EMBED_MODEL,
            "model": EMBED_MODEL,
            "details": {"family": "qa-contract"},
        },
    ]


def chat_response(model: str | None) -> dict[str, Any]:
    return {
        "model": model or CHAT_MODEL,
        "created_at": "1970-01-01T00:00:00Z",
        "message": {"role": "assistant", "content": "qa-contract-response"},
        "done": True,
        "prompt_eval_count": 1,
        "eval_count": 1,
    }


def openai_chat_stream(model: str | None) -> list[dict[str, Any]]:
    """Return a valid, deterministic OpenAI-compatible SSE chunk sequence.

    This is a transport-contract fixture only.  The content is deliberately
    canned and must never be interpreted as model or Research Spine evidence.
    """
    response = chat_response(model)
    return [
        {
            "id": "qa-contract-chat",
            "object": "chat.completion.chunk",
            "model": response["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": response["message"],
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "qa-contract-chat",
            "object": "chat.completion.chunk",
            "model": response["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    ]


class ProviderStubHandler(BaseHTTPRequestHandler):
    """Small HTTP handler for the Ollama-compatible contract surface."""

    server_version = "IstaraQAProviderStub/1"

    def log_message(self, _format: str, *_args: Any) -> None:
        # Do not emit request paths or payload-derived values into QA logs.
        return

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        content_type: str = "application/json",
    ) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")
        return payload

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/api/tags":
            self._send_json(200, {"models": model_records()})
            return
        if self.path == "/api/version":
            self._send_json(200, {"version": "istara-qa-contract"})
            return
        if self.path == "/api/ps":
            self._send_json(200, {"models": []})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            payload = self._read_json()
            if self.path == "/api/embed":
                vectors = embeddings_for_input(payload.get("input"))
                self._send_json(
                    200,
                    {
                        "model": payload.get("model") or EMBED_MODEL,
                        "embeddings": vectors,
                    },
                )
                return
            if self.path == "/api/chat":
                response = chat_response(payload.get("model"))
                if payload.get("stream"):
                    lines = [
                        {
                            "model": response["model"],
                            "message": response["message"],
                            "done": False,
                        },
                        response,
                    ]
                    body = b"".join(
                        json.dumps(line, separators=(",", ":")).encode() + b"\n"
                        for line in lines
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._send_json(200, response)
                return
            if self.path == "/api/generate":
                self._send_json(
                    200,
                    {
                        "model": payload.get("model") or CHAT_MODEL,
                        "response": "qa-contract-response",
                        "done": True,
                    },
                )
                return
            if self.path == "/api/show":
                self._send_json(200, {"details": {"family": "qa-contract"}})
                return
            if self.path == "/v1/embeddings":
                vectors = embeddings_for_input(payload.get("input"))
                self._send_json(
                    200,
                    {
                        "object": "list",
                        "model": payload.get("model") or EMBED_MODEL,
                        "data": [
                            {"object": "embedding", "index": index, "embedding": vector}
                            for index, vector in enumerate(vectors)
                        ],
                    },
                )
                return
            if self.path == "/v1/chat/completions":
                response = chat_response(payload.get("model"))
                if payload.get("stream"):
                    body = (
                        b"".join(
                            (
                                "data: "
                                + json.dumps(chunk, separators=(",", ":"))
                                + "\n\n"
                            ).encode("utf-8")
                            for chunk in openai_chat_stream(payload.get("model"))
                        )
                        + b"data: [DONE]\n\n"
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self._send_json(
                    200,
                    {
                        "id": "qa-contract-chat",
                        "object": "chat.completion",
                        "model": response["model"],
                        "choices": [
                            {
                                "index": 0,
                                "message": response["message"],
                                "finish_reason": "stop",
                            }
                        ],
                    },
                )
                return
        except (ValueError, TypeError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid_request"})
            return
        self._send_json(404, {"error": "not_found"})


def main() -> None:
    port = int(os.environ.get("QA_CONTRACT_PROVIDER_PORT", "11434"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ProviderStubHandler)
    server.daemon_threads = True
    print("qa-contract-provider-ready", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
