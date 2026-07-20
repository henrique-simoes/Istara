#!/usr/bin/env node
// Pi runtime worker entrypoint.
//
// Speaks the versioned NDJSON protocol (PROTOCOL.md) over stdin/stdout. stdout
// is protocol-only; sanitized diagnostics go to stderr. Hosts one supervised
// pi-agent-core Agent per session (max LIMITS.MAX_SESSIONS). Secrets arrive only
// inside `provider.bind` and are never echoed, logged, or persisted.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FrameReader, ProtocolError, PROTOCOL_VERSION, LIMITS, encodeFrame, makeSeq } from "./protocol.mjs";
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
const nextSeq = makeSeq();

function write(frame) {
  process.stdout.write(encodeFrame({ ...frame, seq: nextSeq() }));
}

function diag(message) {
  // stderr only, never protocol; keep it terse and secret-free.
  process.stderr.write(`[pi-runtime] ${message}\n`);
}

function emitForSession(frame) {
  write(frame);
}

async function handleFrame(frame) {
  const type = frame && frame.type;
  switch (type) {
    case "hello":
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
          write({ v: 1, type: "session.opened", session_key: key });
          return;
        }
      }
      if (sessions.size >= LIMITS.MAX_SESSIONS) {
        write({ v: 1, type: "run.failed", session_key: key, error: "max_sessions_exceeded" });
        return;
      }
      const session = new PiSession({
        sessionKey: key,
        systemPrompt: frame.system_prompt,
        history: frame.history,
        revision: frame.revision ?? null,
        catalog: frame.catalog,
        emit: emitForSession,
      });
      sessions.set(key, session);
      write({ v: 1, type: "session.opened", session_key: key });
      return;
    }

    case "provider.bind": {
      const session = sessions.get(frame.session_key);
      if (!session) {
        write({ v: 1, type: "run.failed", session_key: frame.session_key, error: "unknown_session" });
        return;
      }
      try {
        session.bindProvider(frame.endpoint || {});
      } catch (err) {
        write({ v: 1, type: "run.failed", session_key: frame.session_key, error: `provider_bind_failed:${err.message}` });
      }
      return;
    }

    case "turn.prompt": {
      const session = sessions.get(frame.session_key);
      if (!session) {
        write({ v: 1, type: "run.failed", session_key: frame.session_key, run_id: frame.run_id, error: "unknown_session" });
        return;
      }
      // Do not await: the run streams events until its own terminal frame.
      session.prompt(frame.run_id, frame.text);
      return;
    }

    case "turn.follow_up": {
      const session = sessions.get(frame.session_key);
      if (session) session.followUp(frame.run_id, frame.text);
      return;
    }

    case "turn.steer": {
      const session = sessions.get(frame.session_key);
      if (session) session.steer(frame.run_id, frame.text);
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
      }
      write({ v: 1, type: "session.closed", session_key: frame.session_key });
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
        write({ v: 1, type: "fatal", error: err.code });
        return;
      }
      throw err;
    }
    for (const frame of frames) {
      Promise.resolve()
        .then(() => handleFrame(frame))
        .catch((err) => {
          diag(`frame_handler_error:${err && err.message}`);
          write({ v: 1, type: "fatal", error: "frame_handler_error" });
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
