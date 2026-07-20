"""Wire-protocol constants shared with the Node worker (see pi-runtime/PROTOCOL.md).

The frames themselves are plain dicts encoded as NDJSON; this module only pins
the version and the bounds so both sides agree.
"""

from __future__ import annotations

PROTOCOL_VERSION = 1

MAX_LINE_BYTES = 256 * 1024
MAX_TOOL_ARGS_BYTES = 64 * 1024
MAX_HISTORY_MESSAGES = 200
MAX_SESSIONS = 8

# Terminal run frames — exactly one is emitted per run_id.
TERMINAL_RUN_TYPES = frozenset({"run.completed", "run.failed", "run.aborted"})
