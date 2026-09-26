"""Run liveness for Pi endpoints: judge a model by progress, with a generous total budget.

Istara is local-first. A local model can load weights before it answers and then stream slowly
for a long time, and a fixed two-minute wall clock killed it however steadily it produced. Two
questions are kept apart (DEC-10, 2026-09-25):

* **Idle** - the longest silence allowed between streamed provider events (text, thinking and
  tool-call frames all count as progress; time spent in Istara's own tools does not).
* **Total** - a backstop for the whole run.

Defaults follow the industry's defaults. Remote: idle 120 s, total 600 s (the OpenAI and Anthropic
SDKs time out after 10 minutes). Local: idle 300 s (Open WebUI gives Ollama 300 s, and Ollama's
load-stall window is 5 minutes), total 3,600 s (llama.cpp server's default read/write timeout).
A local endpoint also waits up to 300 s for its response to start, instead of 30 s.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

REMOTE_IDLE_MS = 120_000
REMOTE_RUN_MS = 600_000
LOCAL_IDLE_MS = 300_000
LOCAL_RUN_MS = 3_600_000
LOCAL_RESPONSE_START_MS = 300_000

_LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home.arpa", ".ts.net")
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def is_local_url(base_url: str) -> bool:
    """Whether a base URL points at this machine, the private network or the tailnet."""
    host = (urlsplit(base_url or "").hostname or "").strip().lower()
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # A single-label name is a Docker service or LAN host (``ollama``, ``llmbox``).
        return host == "localhost" or "." not in host or host.endswith(_LOCAL_SUFFIXES)
    return bool(
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or (ip.version == 4 and ip in _TAILSCALE_CGNAT)
    )


def run_budgets(
    *, local: bool, idle_ms: int | None = None, run_ms: int | None = None
) -> tuple[int, int]:
    """(idle, total) in milliseconds; explicit values win over the locality defaults."""
    default_idle, default_run = (
        (LOCAL_IDLE_MS, LOCAL_RUN_MS) if local else (REMOTE_IDLE_MS, REMOTE_RUN_MS)
    )
    return int(idle_ms or default_idle), int(run_ms or default_run)
