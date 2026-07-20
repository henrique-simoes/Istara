"""Wire-protocol constants shared with the Node worker (see pi-runtime/PROTOCOL.md).

The frames themselves are plain dicts encoded as NDJSON; this module only pins
the version and the bounds so both sides agree.
"""

from __future__ import annotations

PROTOCOL_VERSION = 1

# Must match pi-runtime/src/protocol.mjs.  The transport chunks before this
# ceiling, while the subprocess reader is deliberately larger (H-1/H-2).
MAX_LINE_BYTES = 1024 * 1024
MAX_CHUNK_DATA_BYTES = 512 * 1024
MAX_REASSEMBLED_BYTES = 16 * 1024 * 1024
MAX_TOOL_ARGS_BYTES = 64 * 1024
MAX_HISTORY_MESSAGES = 200
MAX_SESSIONS = 8

# Terminal run frames — exactly one is emitted per run_id.
TERMINAL_RUN_TYPES = frozenset({"run.completed", "run.failed", "run.aborted"})
