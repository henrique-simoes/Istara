#!/usr/bin/env python3
"""Small DeepSeek smoke using an OpenAI-compatible chat-completions request.

The API key is fetched from macOS Keychain inside this process and never printed.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "logs" / "deepseek-openai-compatible-smoke.json"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-pro"


def keychain_secret() -> str:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    proc = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            "openclaw",
            "-s",
            "istara-pi-deepseek",
            "-w",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError("DEEPSEEK_API_KEY unavailable from Keychain")
    return proc.stdout.strip()


def capped(value: str, limit: int = 1200) -> str:
    return value if len(value) <= limit else value[:limit] + "...[truncated]"


def main() -> int:
    started = time.monotonic()
    key = keychain_secret()
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Return exactly the word pong.",
            },
            {
                "role": "user",
                "content": "Connectivity smoke. Reply with pong.",
            },
        ],
        "stream": False,
        "max_tokens": 16,
        "temperature": 0,
        "reasoning_effort": "high",
        "extra_body": {"thinking": {"type": "enabled"}},
    }
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    result = {
        "smoke": "deepseek_openai_compatible",
        "provider": "DeepSeek",
        "base_url": BASE_URL,
        "model": MODEL,
        "reasoning_effort": "high",
        "thinking_requested": True,
        "deepseek_key_present": True,
        "secret_value_logged": False,
        "passed": False,
        "latency_ms": None,
        "status_code": None,
        "usage": None,
        "response_text_capped": "",
        "error_capped": "",
    }
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result.update(
                {
                    "passed": True,
                    "status_code": response.status,
                    "usage": data.get("usage"),
                    "response_model": data.get("model"),
                    "response_text_capped": capped(text),
                }
            )
    except urllib.error.HTTPError as exc:
        result["status_code"] = exc.code
        result["error_capped"] = capped(exc.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        result["error_capped"] = capped(type(exc).__name__ + ": " + str(exc))
    finally:
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "smoke": result["smoke"],
                    "passed": result["passed"],
                    "status_code": result["status_code"],
                    "latency_ms": result["latency_ms"],
                    "usage": result["usage"],
                    "error_capped": result["error_capped"],
                },
                indent=2,
            )
        )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

