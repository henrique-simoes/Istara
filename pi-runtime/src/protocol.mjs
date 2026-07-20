// Wire protocol codec for the Pi runtime worker (see PROTOCOL.md).
//
// One JSON object per line. stdout is protocol-only; stderr carries sanitized
// diagnostics. Every frame carries `v` (protocol version). Malformed frames are
// terminal for the affected run, never silently for the process.

export const PROTOCOL_VERSION = 1;

export const LIMITS = Object.freeze({
  MAX_LINE_BYTES: 256 * 1024,
  MAX_TOOL_ARGS_BYTES: 64 * 1024,
  MAX_HISTORY_MESSAGES: 200,
  MAX_SESSIONS: 8,
  MAX_INFLIGHT_TOOL_CALLS: 4,
});

/** Serialize a frame to a single NDJSON line (no embedded newlines). */
export function encodeFrame(frame) {
  return JSON.stringify(frame) + "\n";
}

/**
 * Stateful line reader that enforces the max line bound. Feed it string chunks;
 * it yields parsed frames. Over-long lines raise a protocol error so the caller
 * can terminate the offending run rather than buffer unboundedly.
 */
export class FrameReader {
  constructor({ maxLineBytes = LIMITS.MAX_LINE_BYTES } = {}) {
    this._buffer = "";
    this._maxLineBytes = maxLineBytes;
  }

  *push(chunk) {
    this._buffer += chunk;
    let newlineIndex;
    while ((newlineIndex = this._buffer.indexOf("\n")) !== -1) {
      const line = this._buffer.slice(0, newlineIndex);
      this._buffer = this._buffer.slice(newlineIndex + 1);
      if (Buffer.byteLength(line, "utf8") > this._maxLineBytes) {
        throw new ProtocolError("line_exceeds_max_bytes");
      }
      const trimmed = line.trim();
      if (!trimmed) continue;
      let frame;
      try {
        frame = JSON.parse(trimmed);
      } catch {
        throw new ProtocolError("malformed_frame_json");
      }
      yield frame;
    }
    if (Buffer.byteLength(this._buffer, "utf8") > this._maxLineBytes) {
      throw new ProtocolError("line_exceeds_max_bytes");
    }
  }
}

export class ProtocolError extends Error {
  constructor(code) {
    super(code);
    this.name = "ProtocolError";
    this.code = code;
  }
}

/** A monotonic per-side sequence counter for outbound frames. */
export function makeSeq() {
  let seq = 0;
  return () => (seq += 1);
}
