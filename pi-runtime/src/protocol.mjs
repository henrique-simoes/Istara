// Wire protocol codec for the Pi runtime worker (see PROTOCOL.md).
//
// One JSON object per line. stdout is protocol-only; stderr carries sanitized
// diagnostics. Every frame carries `v` (protocol version) and a per-session_key
// monotonically increasing `seq` (frames without a session_key use a
// connection-level counter). Frames whose serialized line exceeds
// MAX_LINE_BYTES are split into `payload.chunk` frames; the receiver
// reassembles them per chunk_id with a hard bound on the reassembled size.
// Malformed frames are terminal for the affected run, never silently for the
// process.

// v2: turn.prompt gains output_schema / tool_choice / max_turns and
// run.completed may carry the captured `structured` object (forced
// emit_structured_output contract, see structured.mjs). Both sides validate
// the version at handshake and per-frame; a mismatch is a typed failure.
export const PROTOCOL_VERSION = 2;

function envMaxSessions() {
  const raw = Number.parseInt(process.env.PI_MAX_SESSIONS ?? "", 10);
  return Number.isInteger(raw) && raw > 0 ? raw : 8;
}

export const LIMITS = Object.freeze({
  MAX_LINE_BYTES: 1024 * 1024,
  // Chunk data slices stay well under MAX_LINE_BYTES so the encoded chunk
  // frame (with JSON escaping overhead) always fits on one line.
  MAX_CHUNK_DATA_BYTES: 512 * 1024,
  MAX_REASSEMBLED_BYTES: 16 * 1024 * 1024,
  MAX_PENDING_CHUNK_SETS: 64,
  MAX_TOOL_ARGS_BYTES: 64 * 1024,
  MAX_HISTORY_MESSAGES: 200,
  MAX_SESSIONS: envMaxSessions(),
  MAX_INFLIGHT_TOOL_CALLS: 4,
});

/** Serialize a frame to a single NDJSON line (no embedded newlines). */
export function encodeFrame(frame) {
  return JSON.stringify(frame) + "\n";
}

let chunkCounter = 0;

/**
 * Split a string into slices of at most maxBytes UTF-8 bytes each, never
 * breaking a code point (for..of iterates code points, so surrogate pairs
 * stay together and concatenation reproduces the input exactly).
 */
export function splitUtf8(str, maxBytes) {
  const parts = [];
  let current = "";
  let currentBytes = 0;
  for (const ch of str) {
    const bytes = Buffer.byteLength(ch, "utf8");
    if (current && currentBytes + bytes > maxBytes) {
      parts.push(current);
      current = "";
      currentBytes = 0;
    }
    current += ch;
    currentBytes += bytes;
  }
  if (current) parts.push(current);
  return parts;
}

/**
 * Serialize a frame to one or more NDJSON lines. Frames that fit within
 * MAX_LINE_BYTES produce a single line; oversized frames are split into
 * `payload.chunk` frames whose `data` slices concatenate (in `seq` order,
 * 1-based) to the original serialized frame JSON (no newline). Note the
 * chunk `seq` field is the chunk ordering, not the protocol-level seq — the
 * original frame carries its own protocol seq inside the chunked payload.
 */
export function encodeFrameLines(frame) {
  const line = encodeFrame(frame);
  if (Buffer.byteLength(line, "utf8") <= LIMITS.MAX_LINE_BYTES) return [line];
  const json = line.slice(0, -1);
  const parts = splitUtf8(json, LIMITS.MAX_CHUNK_DATA_BYTES);
  const chunkId = `chunk-${process.pid}-${Date.now().toString(36)}-${++chunkCounter}`;
  return parts.map((data, index) =>
    encodeFrame({
      v: PROTOCOL_VERSION,
      type: "payload.chunk",
      chunk_id: chunkId,
      seq: index + 1,
      total: parts.length,
      data,
    }),
  );
}

/**
 * Stateful line reader that enforces the max line bound and reassembles
 * `payload.chunk` frame sets. Feed it string chunks; it yields parsed frames.
 * Over-long lines and chunk-set violations raise a protocol error so the
 * caller can terminate the offending run rather than buffer unboundedly.
 */
export class FrameReader {
  constructor({ maxLineBytes = LIMITS.MAX_LINE_BYTES } = {}) {
    this._buffer = "";
    this._maxLineBytes = maxLineBytes;
    this._chunkSets = new Map(); // chunk_id -> {total, parts: Map(seq -> data), bytes}
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
      if (frame && frame.type === "payload.chunk") {
        const reassembled = this._reassemble(frame);
        if (reassembled === null) continue;
        frame = reassembled;
      }
      yield frame;
    }
    if (Buffer.byteLength(this._buffer, "utf8") > this._maxLineBytes) {
      throw new ProtocolError("line_exceeds_max_bytes");
    }
  }

  /**
   * Accumulate one payload.chunk frame. Returns null while the set is
   * incomplete, the reassembled frame once every part has arrived, and throws
   * a ProtocolError on garbage or when the reassembled size exceeds
   * MAX_REASSEMBLED_BYTES.
   */
  _reassemble(frame) {
    const { chunk_id: id, seq, total, data } = frame;
    if (
      typeof id !== "string" ||
      !id ||
      !Number.isInteger(seq) ||
      !Number.isInteger(total) ||
      total < 1 ||
      seq < 1 ||
      seq > total ||
      typeof data !== "string"
    ) {
      throw new ProtocolError("malformed_chunk_frame");
    }
    let entry = this._chunkSets.get(id);
    if (!entry) {
      if (this._chunkSets.size >= LIMITS.MAX_PENDING_CHUNK_SETS) {
        throw new ProtocolError("chunk_reassembly_overflow");
      }
      entry = { total, parts: new Map(), bytes: 0 };
      this._chunkSets.set(id, entry);
    }
    if (entry.total !== total) {
      this._chunkSets.delete(id);
      throw new ProtocolError("malformed_chunk_frame");
    }
    if (!entry.parts.has(seq)) {
      const bytes = Buffer.byteLength(data, "utf8");
      if (entry.bytes + bytes > LIMITS.MAX_REASSEMBLED_BYTES) {
        this._chunkSets.delete(id);
        throw new ProtocolError("chunk_over_bound");
      }
      entry.parts.set(seq, data);
      entry.bytes += bytes;
    }
    if (entry.parts.size < entry.total) return null;
    let joined = "";
    for (let i = 1; i <= entry.total; i++) joined += entry.parts.get(i);
    this._chunkSets.delete(id);
    try {
      return JSON.parse(joined);
    } catch {
      throw new ProtocolError("malformed_frame_json");
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
