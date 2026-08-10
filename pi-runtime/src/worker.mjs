#!/usr/bin/env node
// Pi runtime worker entrypoint.
//
// Speaks the versioned NDJSON protocol (PROTOCOL.md) over stdin/stdout. stdout
// is protocol-only; sanitized diagnostics go to stderr. Hosts one supervised
// pi-agent-core Agent per session (max LIMITS.MAX_SESSIONS, configurable via
// PI_MAX_SESSIONS). Secrets arrive only inside `provider.bind` and are never
// echoed, logged, or persisted.
//
// Failure discipline: malformed inbound lines, chunk-reassembly violations,
// and seq violations terminate the affected run with a run-scoped `run.failed`
// frame. The worker never broadcasts a process-wide `fatal` for input it can
// attribute to (or isolate from) a session.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FrameReader, ProtocolError, PROTOCOL_VERSION, LIMITS, encodeFrameLines, makeSeq } from "./protocol.mjs";
import { PiSession } from "./session.mjs";

function pkgVersion(name) {
  // pi-ai/pi-agent-core are import-only (no `require` condition and no
  // ./package.json export), so resolve the ESM entry and walk up to the
  // package's own package.json.
  try {
    let dir = path.dirname(fileURLToPath(import.meta.resolve(name)));
    for (let i = 0; i < 8; i++) {
      const candidate = path.join(dir, "package.json");
      if (fs.existsSync(candidate)) {
        const parsed = JSON.parse(fs.readFileSync(candidate, "utf8"));
        if (parsed.name === name) return parsed.version;
      }
      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  } catch {
    /* fall through */
  }
  return "unknown";
}

const sessions = new Map(); // session_key -> PiSession
const connectionSeq = makeSeq(); // outbound seq for frames without a session_key
const sessionSeqs = new Map(); // session_key -> last outbound seq
const inboundSeqs = new Map(); // session_key (null = connection-level) -> last inbound seq

function nextOutboundSeq(sessionKey) {
  if (typeof sessionKey === "string") {
    const next = (sessionSeqs.get(sessionKey) || 0) + 1;
    sessionSeqs.set(sessionKey, next);
    return next;
  }
  return connectionSeq();
}

function write(frame) {
  const withSeq = { ...frame, seq: frame.seq ?? nextOutboundSeq(frame.session_key) };
  for (const line of encodeFrameLines(withSeq)) {
    process.stdout.write(line);
  }
}

function diag(message) {
  // stderr only, never protocol; keep it terse and secret-free.
  process.stderr.write(`[pi-runtime] ${message}\n`);
}

function emitForSession(frame) {
  write(frame);
}

/**
 * Validate inbound protocol seq monotonicity: per-session_key counters
 * starting at 1, with a connection-level counter for frames that carry no
 * session_key. payload.chunk frames never reach here (the FrameReader
 * reassembles them); their embedded seq is the chunk ordering.
 */
function checkInboundSeq(frame) {
  const key = typeof frame.session_key === "string" ? frame.session_key : null;
  const seq = frame.seq;
  if (typeof seq !== "number" || !Number.isInteger(seq) || seq < 1) return false;
  const last = inboundSeqs.get(key) || 0;
  if (seq <= last) return false;
  inboundSeqs.set(key, seq);
  return true;
}

/**
 * Terminate every active run with a run-scoped error (used when an inbound
 * line cannot be attributed to a single session: a poisoned line is almost
 * certainly the frame an active run is waiting on). Never process-fatal.
 */
function failActiveRuns(error) {
  let any = false;
  for (const session of sessions.values()) {
    if (session.failActiveRun(error)) any = true;
  }
  if (!any) diag(`inbound_error:${error}`);
}

/** Run-scoped failure for a frame we refuse to process. */
function rejectFrame(frame, error) {
  const target = frame || {};
  const session = typeof target.session_key === "string" ? sessions.get(target.session_key) : null;
  if (session && session.failActiveRun(error)) return;
  if (typeof target.session_key === "string") {
    write({ v: PROTOCOL_VERSION, type: "run.failed", session_key: target.session_key, run_id: target.run_id, error });
  } else {
    diag(`rejected_frame:${error}:${target.type}`);
  }
}

async function handleFrame(frame) {
  const type = frame && frame.type;
  switch (type) {
    case "hello":
      // Both-side version validation: a host speaking a different protocol
      // version gets a typed fatal and never a `ready` — the worker must not
      // serve frames it cannot interpret (v2 forced structured contract).
      if (frame.v !== PROTOCOL_VERSION || frame.protocol_version !== PROTOCOL_VERSION) {
        write({
          v: PROTOCOL_VERSION,
          type: "fatal",
          error: "protocol_version_mismatch",
          protocol_version: PROTOCOL_VERSION,
        });
        return;
      }
      write({
        v: PROTOCOL_VERSION,
        type: "ready",
        protocol_version: PROTOCOL_VERSION,
        pi_agent_core: pkgVersion("@earendil-works/pi-agent-core"),
        pi_ai: pkgVersion("@earendil-works/pi-ai"),
      });
      return;

    case "session.open": {
      const key = frame.session_key;
      const existing = sessions.get(key);
      if (existing) {
        if (existing.revision !== (frame.revision ?? null)) {
          // Revision mismatch: close and rehydrate rather than append to stale state.
          await existing.close();
          sessions.delete(key);
        } else {
          write({ v: PROTOCOL_VERSION, type: "session.opened", session_key: key });
          return;
        }
      }
      if (sessions.size >= LIMITS.MAX_SESSIONS) {
        write({ v: PROTOCOL_VERSION, type: "session.open_failed", session_key: key, error: "session_capacity_exceeded" });
        return;
      }
      const session = new PiSession({
        sessionKey: key,
        systemPrompt: frame.system_prompt,
        history: frame.history,
        revision: frame.revision ?? null,
        catalog: frame.catalog,
        limits: frame.limits,
        emit: emitForSession,
      });
      sessions.set(key, session);
      write({ v: PROTOCOL_VERSION, type: "session.opened", session_key: key });
      return;
    }

    case "provider.bind": {
      const session = sessions.get(frame.session_key);
      if (!session) {
        write({ v: PROTOCOL_VERSION, type: "run.failed", session_key: frame.session_key, error: "unknown_session" });
        return;
      }
      try {
        const endpoint = frame.endpoint || {};
        // Canonical location for generation/retry params is endpoint.params;
        // a top-level `params` object is accepted as an alias.
        session.bindProvider({ ...endpoint, params: endpoint.params ?? frame.params });
      } catch (err) {
        write({ v: PROTOCOL_VERSION, type: "run.failed", session_key: frame.session_key, error: `provider_bind_failed:${err.message}` });
      }
      return;
    }

    case "turn.prompt": {
      const session = sessions.get(frame.session_key);
      if (!session) {
        write({ v: PROTOCOL_VERSION, type: "run.failed", session_key: frame.session_key, run_id: frame.run_id, error: "unknown_session" });
        return;
      }
      // Do not await: the run streams events until its own terminal frame.
      session.prompt(frame.run_id, frame.text, {
        maxTurns: frame.max_turns,
        outputSchema: frame.output_schema,
        toolChoice: frame.tool_choice,
      });
      return;
    }

    case "turn.follow_up": {
      const session = sessions.get(frame.session_key);
      if (session) {
        // Contain rejections: a failed follow-up must never crash the worker.
        Promise.resolve(session.followUp(frame.run_id, frame.text)).catch((err) => {
          diag(`follow_up_error:${err && err.message}`);
        });
      }
      return;
    }

    case "turn.steer": {
      const session = sessions.get(frame.session_key);
      if (session) {
        // Contain rejections: a failed steer must never crash the worker.
        Promise.resolve(session.steer(frame.run_id, frame.text)).catch((err) => {
          diag(`steer_error:${err && err.message}`);
        });
      }
      return;
    }

    case "turn.abort": {
      const session = sessions.get(frame.session_key);
      if (session) session.abort(frame.run_id);
      return;
    }

    case "tool.result": {
      const session = sessions.get(frame.session_key);
      if (session) {
        session.resolveToolResult(frame.tool_call_id, {
          ok: Boolean(frame.ok),
          result: frame.result,
          error: frame.error,
        });
      }
      return;
    }

    case "session.close": {
      const session = sessions.get(frame.session_key);
      if (session) {
        await session.close();
        sessions.delete(frame.session_key);
        sessionSeqs.delete(frame.session_key);
        inboundSeqs.delete(frame.session_key);
      }
      write({ v: PROTOCOL_VERSION, type: "session.closed", session_key: frame.session_key });
      return;
    }

    case "shutdown": {
      await shutdown();
      return;
    }

    default:
      diag(`ignored_unknown_frame:${type}`);
  }
}

async function shutdown() {
  for (const [key, session] of sessions) {
    try {
      await session.close();
    } catch {
      /* best-effort */
    }
    sessions.delete(key);
  }
  process.stdout.end(() => process.exit(0));
}

function main() {
  const reader = new FrameReader();
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => {
    let frames;
    try {
      frames = [...reader.push(chunk)];
    } catch (err) {
      if (err instanceof ProtocolError) {
        // A poisoned/malformed inbound line terminates the affected run(s)
        // with a run-scoped error frame; the process keeps serving every
        // other session.
        failActiveRuns(err.code);
        return;
      }
      throw err;
    }
    for (const frame of frames) {
      // Every inbound frame must speak this protocol version. Reject BEFORE
      // consuming the seq so a single mismatched frame does not wedge the
      // session's monotonic counter. `hello` is exempt here: its handler
      // answers a mismatch with the typed connection-level `fatal` so the
      // host learns the worker's version instead of seeing silence.
      if (!frame || (frame.v !== PROTOCOL_VERSION && frame.type !== "hello")) {
        rejectFrame(frame, "protocol_version_mismatch");
        continue;
      }
      if (!checkInboundSeq(frame)) {
        rejectFrame(frame, "protocol_seq_violation");
        continue;
      }
      Promise.resolve()
        .then(() => handleFrame(frame))
        .catch((err) => {
          diag(`frame_handler_error:${err && err.message}`);
          rejectFrame(frame, "frame_handler_error");
        });
    }
  });
  process.stdin.on("end", () => {
    shutdown();
  });
  process.on("SIGTERM", () => shutdown());
  process.on("SIGINT", () => shutdown());
}

main();
