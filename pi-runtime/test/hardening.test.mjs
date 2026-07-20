// W0 hardening regression tests (H-1/H-6/H-9/H-11/H-12). Spawns the real
// worker child, drives the NDJSON protocol, and exercises chunking, seq
// validation, the turn budget, the session cap, steer/followUp containment,
// and the guarded provider retry against a loopback HTTP server.

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import http from "node:http";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { FrameReader, ProtocolError, LIMITS, encodeFrameLines } from "../src/protocol.mjs";

const WORKER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "worker.mjs");

class WorkerHarness {
  constructor({ env } = {}) {
    this.child = spawn(process.execPath, [WORKER], {
      stdio: ["pipe", "pipe", "pipe"],
      env: env ? { ...process.env, ...env } : process.env,
    });
    this.frames = [];
    this._waiters = [];
    this._buffer = "";
    this._seqs = new Map(); // session_key (null = connection-level) -> last outbound seq
    this._chunkSets = new Map(); // reassembly of chunked worker->test frames
    this.stderr = "";
    this.child.stdout.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => {
      this._buffer += chunk;
      let idx;
      while ((idx = this._buffer.indexOf("\n")) !== -1) {
        const line = this._buffer.slice(0, idx).trim();
        this._buffer = this._buffer.slice(idx + 1);
        if (!line) continue;
        let frame = JSON.parse(line);
        if (frame.type === "payload.chunk") {
          frame = this._reassemble(frame);
          if (frame === null) continue;
        }
        this.frames.push(frame);
        for (const w of this._waiters.splice(0)) w();
      }
    });
    this.child.stderr.on("data", (c) => (this.stderr += c));
  }

  _reassemble(frame) {
    let entry = this._chunkSets.get(frame.chunk_id);
    if (!entry) {
      entry = { total: frame.total, parts: new Map() };
      this._chunkSets.set(frame.chunk_id, entry);
    }
    entry.parts.set(frame.seq, frame.data);
    if (entry.parts.size < entry.total) return null;
    let joined = "";
    for (let i = 1; i <= entry.total; i++) joined += entry.parts.get(i);
    this._chunkSets.delete(frame.chunk_id);
    return JSON.parse(joined);
  }

  // Mirrors the protocol contract: every frame carries a per-session_key
  // monotonically increasing seq (connection-level counter for keyless
  // frames). An explicit `seq` on the frame overrides the counter.
  send(frame) {
    const key = typeof frame.session_key === "string" ? frame.session_key : null;
    const next = (this._seqs.get(key) || 0) + 1;
    this._seqs.set(key, next);
    this.child.stdin.write(JSON.stringify({ seq: next, ...frame }) + "\n");
  }

  // Write exactly what is given — for protocol-violation tests.
  sendRaw(frame) {
    this.child.stdin.write(JSON.stringify(frame) + "\n");
  }

  sendLines(lines) {
    for (const line of lines) this.child.stdin.write(line);
  }

  async waitFor(predicate, timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const found = this.frames.find(predicate);
      if (found) return found;
      if (Date.now() > deadline) {
        throw new Error(`timeout waiting for frame; got: ${JSON.stringify(this.frames)} stderr=${this.stderr}`);
      }
      await new Promise((resolve) => {
        this._waiters.push(resolve);
        setTimeout(resolve, 50);
      });
    }
  }

  close() {
    try {
      this.send({ v: 1, type: "shutdown" });
      this.child.stdin.end();
    } catch {
      /* ignore */
    }
    // Backstop: never let an orphan child hold the test runner open.
    this.child.kill("SIGKILL");
  }
}

const CATALOG = [
  {
    name: "istara_create_task",
    description: "Create a task",
    parameters: {
      type: "object",
      properties: { title: { type: "string" } },
      required: ["title"],
      additionalProperties: false,
    },
  },
];

async function openSession(h, key, { catalog = CATALOG } = {}) {
  h.send({ v: 1, type: "hello", protocol_version: 1 });
  await h.waitFor((f) => f.type === "ready");
  h.send({ v: 1, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
}

function bindFaux(h, key, responses) {
  h.send({
    v: 1,
    type: "provider.bind",
    session_key: key,
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: responses },
  });
}

// --- H-1: chunk codec unit tests -------------------------------------------

test("chunk codec round-trips a small frame as a single line", () => {
  const frame = { v: 1, type: "tool.result", session_key: "s", tool_call_id: "t", ok: true, result: "x", seq: 7 };
  const lines = encodeFrameLines(frame);
  assert.equal(lines.length, 1);
  const reader = new FrameReader();
  const out = [...reader.push(lines[0])];
  assert.deepEqual(out, [frame]);
});

test("chunk codec round-trips an oversized frame and stays within the line bound", () => {
  const big = "αβ-".repeat(400_000); // ~2.3 MB of multi-byte UTF-8
  const frame = { v: 1, type: "tool.result", session_key: "s", tool_call_id: "t", ok: true, result: big, seq: 3 };
  const lines = encodeFrameLines(frame);
  assert.ok(lines.length > 1);
  for (const line of lines) {
    assert.ok(Buffer.byteLength(line, "utf8") <= LIMITS.MAX_LINE_BYTES);
    const parsed = JSON.parse(line);
    assert.equal(parsed.type, "payload.chunk");
  }
  const reader = new FrameReader();
  let out = [];
  for (const line of lines) out = out.concat([...reader.push(line)]);
  assert.equal(out.length, 1);
  assert.deepEqual(out[0], frame);
});

test("chunk reassembly rejects sets that exceed the 16 MiB bound", () => {
  const reader = new FrameReader();
  const data = "x".repeat(512 * 1024);
  const total = Math.ceil((LIMITS.MAX_REASSEMBLED_BYTES + 1) / (512 * 1024)) + 1;
  assert.throws(() => {
    for (let seq = 1; seq <= total; seq++) {
      [...reader.push(JSON.stringify({ v: 1, type: "payload.chunk", chunk_id: "c", seq, total, data }) + "\n")];
    }
  }, (err) => err instanceof ProtocolError && err.code === "chunk_over_bound");
});

test("chunk reassembly rejects malformed chunk frames", () => {
  const reader = new FrameReader();
  assert.throws(
    () => [...reader.push(JSON.stringify({ v: 1, type: "payload.chunk", chunk_id: "c", seq: 2, total: 1, data: "x" }) + "\n")],
    (err) => err instanceof ProtocolError && err.code === "malformed_chunk_frame",
  );
});

// --- H-1: poisoned inbound line is run-scoped, never process-fatal ---------

test("malformed inbound line fails the active run, never the process", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-poison");
  bindFaux(h, "sess-poison", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
    { text: "done" },
  ]);
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-poison", run_id: "run-p", text: "go" });
  await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-p");

  // The poisoned line stands in for the tool.result the run is waiting on.
  h.child.stdin.write("this is not json at all\n");
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-p");
  assert.equal(failed.error, "malformed_frame_json");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // The process keeps serving other sessions.
  h.send({ v: 1, type: "session.open", session_key: "sess-after", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === "sess-after");
});

test("1 MB tool.result round-trips through chunked frames", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-chunk");
  bindFaux(h, "sess-chunk", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
    { text: "Acknowledged the big result." },
  ]);
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-chunk", run_id: "run-c", text: "go" });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-c");

  const bigResult = "R".repeat(1024 * 1024);
  const resultFrame = {
    v: 1,
    type: "tool.result",
    session_key: "sess-chunk",
    run_id: "run-c",
    tool_call_id: toolCall.tool_call_id,
    ok: true,
    result: bigResult,
    seq: (h._seqs.get("sess-chunk") || 0) + 1, // next in-order seq for this session
  };
  const lines = encodeFrameLines(resultFrame);
  assert.ok(lines.length > 1);
  h.sendLines(lines);

  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-c");
  assert.equal(completed.stop_reason, "stop");
});

// --- H-6: worker-side max_turns budget -------------------------------------

test("max_turns budget aborts the run with turn_budget_exceeded", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-budget");
  bindFaux(h, "sess-budget", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
    { text: "second turn" },
  ]);
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-budget", run_id: "run-b", text: "go", max_turns: 1 });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-b");
  h.send({ v: 1, type: "tool.result", session_key: "sess-budget", run_id: "run-b", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-b");
  assert.equal(failed.error, "turn_budget_exceeded");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-b"));
});

test("max_turns within budget completes normally", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-budget-ok");
  bindFaux(h, "sess-budget-ok", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
    { text: "second turn" },
  ]);
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-budget-ok", run_id: "run-ok", text: "go", max_turns: 2 });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-ok");
  h.send({ v: 1, type: "tool.result", session_key: "sess-budget-ok", run_id: "run-ok", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-ok");
  assert.equal(completed.stop_reason, "stop");
});

// --- H-11: seq validation ---------------------------------------------------

test("inbound seq violation is a run-scoped protocol_seq_violation", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-seq");
  // session.open consumed inbound seq 1 for this key; replaying seq 1 is a
  // monotonicity violation and the frame must not be processed.
  h.sendRaw({ v: 1, type: "turn.prompt", session_key: "sess-seq", run_id: "r-bad", text: "x", seq: 1 });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "r-bad");
  assert.equal(failed.error, "protocol_seq_violation");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // The session still accepts the next in-order frame.
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-seq", run_id: "r-good", text: "x" });
  const next = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "r-good");
  assert.equal(next.error, "no_provider_bound");
});

// --- H-12: MAX_SESSIONS cap -------------------------------------------------

test("session cap refuses session.open with session_capacity_exceeded", async (t) => {
  const h = new WorkerHarness({ env: { PI_MAX_SESSIONS: "2" } });
  t.after(() => h.close());
  h.send({ v: 1, type: "hello", protocol_version: 1 });
  await h.waitFor((f) => f.type === "ready");
  for (const key of ["cap-1", "cap-2"]) {
    h.send({ v: 1, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog: [] });
    await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
  }
  h.send({ v: 1, type: "session.open", session_key: "cap-3", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  const refused = await h.waitFor((f) => f.type === "session.open_failed" && f.session_key === "cap-3");
  assert.equal(refused.error, "session_capacity_exceeded");

  // Capacity frees up when a session closes.
  h.send({ v: 1, type: "session.close", session_key: "cap-1" });
  await h.waitFor((f) => f.type === "session.closed" && f.session_key === "cap-1");
  h.send({ v: 1, type: "session.open", session_key: "cap-3", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === "cap-3");
});

// --- H-9: steer/followUp containment ---------------------------------------

test("steer/followUp during a run never crash the worker", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-steer");
  bindFaux(h, "sess-steer", [{ text: "First answer." }, { text: "Follow-up answer." }]);
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-steer", run_id: "run-s", text: "go" });
  await h.waitFor((f) => f.type === "run.started" && f.run_id === "run-s");
  h.send({ v: 1, type: "turn.steer", session_key: "sess-steer", run_id: "run-s", text: "steer note" });
  h.send({ v: 1, type: "turn.follow_up", session_key: "sess-steer", run_id: "run-s", text: "follow-up note" });
  // Also exercise the unknown-session paths.
  h.send({ v: 1, type: "turn.steer", session_key: "sess-missing", run_id: "run-x", text: "x" });
  h.send({ v: 1, type: "turn.follow_up", session_key: "sess-missing", run_id: "run-x", text: "x" });

  await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-s");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // Worker is still responsive after steer/followUp traffic.
  h.send({ v: 1, type: "session.open", session_key: "sess-steer-2", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === "sess-steer-2");
});

// --- H-11: guarded provider retry against a loopback server -----------------

function sseChunk(content, finishReason = null) {
  return (
    "data: " +
    JSON.stringify({
      id: "chatcmpl-1",
      object: "chat.completion.chunk",
      created: 1,
      model: "test-model",
      choices: [{ index: 0, delta: content ? { content } : {}, finish_reason: finishReason }],
    }) +
    "\n\n"
  );
}

async function startLoopback(handler) {
  const server = http.createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { server, port: server.address().port };
}

function bindLoopback(h, key, port, params) {
  h.send({
    v: 1,
    type: "provider.bind",
    session_key: key,
    endpoint: {
      endpoint_id: "loopback",
      provider_kind: "openai_compat",
      base_url: `http://127.0.0.1:${port}/v1`,
      model: "test-model",
      api_key: "test-key",
      params,
    },
  });
}

test("provider 500-then-success loopback retries before visible output", async (t) => {
  let requests = 0;
  const { server, port } = await startLoopback((req, res) => {
    requests += 1;
    if (requests === 1) {
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: "internal server error 500", type: "server_error" } }));
      return;
    }
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Recovered"));
    res.write(sseChunk(" cleanly."));
    res.write(sseChunk(null, "stop"));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-retry", { catalog: [] });
  bindLoopback(h, "sess-retry", port, { timeout_ms: 5000, max_retries: 2 });
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-retry", run_id: "run-r", text: "go" });

  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-r");
  assert.equal(completed.stop_reason, "stop");
  assert.ok(requests >= 2, `expected at least one retry, saw ${requests} request(s)`);
  const deltas = h.frames.filter((f) => f.type === "assistant.delta" && f.run_id === "run-r").map((f) => f.text);
  assert.equal(deltas.join(""), "Recovered cleanly.");
});

test("provider failure after visible output does not retry or duplicate", async (t) => {
  let requests = 0;
  const { server, port } = await startLoopback((req, res) => {
    requests += 1;
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Partial"));
    // Die mid-stream once the delta has been delivered: visible output
    // already went out, so retry is forbidden.
    setTimeout(() => res.socket.destroy(), 50);
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-noretry", { catalog: [] });
  bindLoopback(h, "sess-noretry", port, { timeout_ms: 5000, max_retries: 3 });
  h.send({ v: 1, type: "turn.prompt", session_key: "sess-noretry", run_id: "run-n", text: "go" });

  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-n");
  assert.ok(failed.error.length > 0);
  // Give any erroneous retry a chance to happen before asserting.
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(requests, 1);
  const deltas = h.frames.filter((f) => f.type === "assistant.delta" && f.run_id === "run-n").map((f) => f.text);
  assert.deepEqual(deltas, ["Partial"]);
});
