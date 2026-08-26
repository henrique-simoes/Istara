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
import { streamWithGuardedRetry } from "../src/provider.mjs";

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
      this.send({ v: 2, type: "shutdown" });
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
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
}

function bindFaux(h, key, responses) {
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: responses },
  });
}

// --- H-1: chunk codec unit tests -------------------------------------------

test("chunk codec round-trips a small frame as a single line", () => {
  const frame = { v: 2, type: "tool.result", session_key: "s", tool_call_id: "t", ok: true, result: "x", seq: 7 };
  const lines = encodeFrameLines(frame);
  assert.equal(lines.length, 1);
  const reader = new FrameReader();
  const out = [...reader.push(lines[0])];
  assert.deepEqual(out, [frame]);
});

test("chunk codec round-trips an oversized frame and stays within the line bound", () => {
  const big = "αβ-".repeat(400_000); // ~2.3 MB of multi-byte UTF-8
  const frame = { v: 2, type: "tool.result", session_key: "s", tool_call_id: "t", ok: true, result: big, seq: 3 };
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
      [...reader.push(JSON.stringify({ v: 2, type: "payload.chunk", chunk_id: "c", seq, total, data }) + "\n")];
    }
  }, (err) => err instanceof ProtocolError && err.code === "chunk_over_bound");
});

test("chunk reassembly rejects malformed chunk frames", () => {
  const reader = new FrameReader();
  assert.throws(
    () => [...reader.push(JSON.stringify({ v: 2, type: "payload.chunk", chunk_id: "c", seq: 2, total: 1, data: "x" }) + "\n")],
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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-poison", run_id: "run-p", text: "go" });
  await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-p");

  // The poisoned line stands in for the tool.result the run is waiting on.
  h.child.stdin.write("this is not json at all\n");
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-p");
  assert.equal(failed.error, "malformed_frame_json");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // The process keeps serving other sessions.
  h.send({ v: 2, type: "session.open", session_key: "sess-after", system_prompt: "s", history: [], revision: "r1", catalog: [] });
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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-chunk", run_id: "run-c", text: "go" });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-c");

  const bigResult = "R".repeat(1024 * 1024);
  const resultFrame = {
    v: 2,
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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-budget", run_id: "run-b", text: "go", max_turns: 1 });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-b");
  h.send({ v: 2, type: "tool.result", session_key: "sess-budget", run_id: "run-b", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-budget-ok", run_id: "run-ok", text: "go", max_turns: 2 });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-ok");
  h.send({ v: 2, type: "tool.result", session_key: "sess-budget-ok", run_id: "run-ok", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-ok");
  assert.equal(completed.stop_reason, "stop");
});

// --- H-6: whole-run wall-clock ceiling --------------------------------------

// Open a session carrying explicit per-run limits (session.open `limits`),
// which the harness openSession helper omits.
async function openSessionWithLimits(h, key, limits, { catalog = CATALOG } = {}) {
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog, limits });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
}

test("wall-clock budget fails a stalled run with wall_clock_budget_exceeded", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-wall", { max_wall_clock_ms: 250 });
  // The faux turn issues a tool call; the test never answers it, so the run
  // stays active with no visible progress until the wall-clock timer fires.
  bindFaux(h, "sess-wall", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
  ]);
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-wall", run_id: "run-w", text: "go" });
  // Deliberately withhold the tool.result the run is blocked on.
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-w");
  assert.equal(failed.error, "wall_clock_budget_exceeded");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-w"));

  // Exactly one terminal, and the worker still serves the next session.
  assert.equal(h.frames.filter((f) => f.type === "run.failed" && f.run_id === "run-w").length, 1);
  h.send({ v: 2, type: "session.open", session_key: "sess-wall-2", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === "sess-wall-2");
});

// --- H-6: per-run cost ceiling ----------------------------------------------

test("cost budget fails a completed run with cost_budget_exceeded", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-cost", { max_cost_usd: 0.5 }, { catalog: [] });
  // The run completes normally but the binding reports a scripted $5 cost that
  // exceeds the $0.5 ceiling: the terminal must flip to a cost failure.
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: "sess-cost",
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: [{ text: "done" }], faux_cost_usd: 5 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-cost", run_id: "run-cost", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-cost");
  assert.equal(failed.error, "cost_budget_exceeded");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-cost"));
});

test("cost within budget completes and reports the run cost", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-cost-ok", { max_cost_usd: 10 }, { catalog: [] });
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: "sess-cost-ok",
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: [{ text: "done" }], faux_cost_usd: 1 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-cost-ok", run_id: "run-cost-ok", text: "go" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-cost-ok");
  assert.equal(completed.stop_reason, "stop");
  assert.equal(completed.usage.cost_usd, 1);
});

// --- F-2: production cost ceiling with a REAL (non-faux) priced binding ------
// These drive the real openai-completions HTTP stack against a loopback that
// reports token usage. pi-ai prices that usage from the binding's model rates,
// which now come from `endpoint.pricing`. A zero-priced real binding would
// compute $0 and complete, so every over-budget assertion here fails if the
// pricing regressed — the non-faux proof the delta review required.

// An OpenAI-style usage-only chunk (empty choices) — parsed before the choice
// guard, so this is how a provider reports final token counts on a stream.
function sseUsageChunk(usage) {
  return (
    "data: " +
    JSON.stringify({ id: "chatcmpl-1", object: "chat.completion.chunk", created: 1, model: "test-model", choices: [], usage }) +
    "\n\n"
  );
}

function sseToolCallChunk(name, args) {
  return (
    "data: " +
    JSON.stringify({
      id: "chatcmpl-1",
      object: "chat.completion.chunk",
      created: 1,
      model: "test-model",
      choices: [
        {
          index: 0,
          delta: { tool_calls: [{ index: 0, id: "call-1", type: "function", function: { name, arguments: JSON.stringify(args) } }] },
          finish_reason: null,
        },
      ],
    }) +
    "\n\n"
  );
}

function bindLoopbackPriced(h, key, port, { params, pricing } = {}) {
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: {
      endpoint_id: "loopback",
      provider_kind: "openai_compat",
      base_url: `http://127.0.0.1:${port}/v1`,
      model: "test-model",
      api_key: "test-key",
      params,
      pricing,
    },
  });
}

test("real priced openai_compat run over the cost ceiling fails closed (non-faux)", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Priced output."));
    res.write(sseChunk(null, "stop"));
    // 1M input + 1M output priced at $1/$2 per Mtok = $3.00, over the $0.50 cap.
    res.write(sseUsageChunk({ prompt_tokens: 1_000_000, completion_tokens: 1_000_000 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-real-cost", { max_cost_usd: 0.5 }, { catalog: [] });
  bindLoopbackPriced(h, "sess-real-cost", port, {
    params: { timeout_ms: 5000 },
    pricing: { input_per_mtok: 1.0, output_per_mtok: 2.0 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-real-cost", run_id: "run-rc", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-rc");
  assert.equal(failed.error, "cost_budget_exceeded");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-rc"));
});

test("real priced run within budget completes and reports the calculated cost", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Cheap output."));
    res.write(sseChunk(null, "stop"));
    res.write(sseUsageChunk({ prompt_tokens: 1_000_000, completion_tokens: 0 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-real-ok", { max_cost_usd: 10 }, { catalog: [] });
  bindLoopbackPriced(h, "sess-real-ok", port, {
    params: { timeout_ms: 5000 },
    pricing: { input_per_mtok: 3.0, output_per_mtok: 6.0 }, // 1M input -> $3.00
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-real-ok", run_id: "run-ro", text: "go" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-ro");
  assert.equal(completed.stop_reason, "stop");
  assert.equal(completed.usage.input_tokens, 1_000_000);
  assert.ok(Math.abs(completed.usage.cost_usd - 3.0) < 1e-6, `expected ~$3.00, got ${completed.usage.cost_usd}`);
});

test("real binding that spends tokens but carries no pricing fails a budgeted run closed", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Unpriced output."));
    res.write(sseChunk(null, "stop"));
    res.write(sseUsageChunk({ prompt_tokens: 5000, completion_tokens: 5000 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-unpriced", { max_cost_usd: 0.5 }, { catalog: [] });
  // No `pricing`: a $0 cost cannot prove the run stayed under budget.
  bindLoopbackPriced(h, "sess-unpriced", port, { params: { timeout_ms: 5000 } });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-unpriced", run_id: "run-up", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-up");
  assert.equal(failed.error, "cost_budget_unpriced");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-up"));
});

test("cost ceiling is cumulative across a real multi-turn tool loop", async (t) => {
  let requests = 0;
  const { server, port } = await startLoopback((req, res) => {
    requests += 1;
    res.writeHead(200, { "content-type": "text/event-stream" });
    if (requests === 1) {
      // Turn 1: a tool call. 1M input priced at $0.30/Mtok = $0.30 (under $0.50).
      res.write(sseToolCallChunk("istara_create_task", { title: "x" }));
      res.write(sseChunk(null, "tool_calls"));
      res.write(sseUsageChunk({ prompt_tokens: 1_000_000, completion_tokens: 0 }));
    } else {
      // Turn 2: final text, another $0.30. Cumulative $0.60 > the $0.50 ceiling,
      // even though neither single turn exceeds it — the per-run sum must fail.
      res.write(sseChunk("Final answer."));
      res.write(sseChunk(null, "stop"));
      res.write(sseUsageChunk({ prompt_tokens: 1_000_000, completion_tokens: 0 }));
    }
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-cumulative", { max_cost_usd: 0.5 });
  bindLoopbackPriced(h, "sess-cumulative", port, {
    params: { timeout_ms: 5000 },
    pricing: { input_per_mtok: 0.3, output_per_mtok: 0.3 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-cumulative", run_id: "run-cum", text: "go" });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-cum");
  h.send({ v: 2, type: "tool.result", session_key: "sess-cumulative", run_id: "run-cum", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-cum");
  assert.equal(failed.error, "cost_budget_exceeded");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-cum"));
  assert.ok(requests >= 2, `expected two provider turns, saw ${requests}`);
});

test("real run that spends cache-read tokens on an endpoint priced only for input/output fails closed (non-faux)", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Cached reply."));
    res.write(sseChunk(null, "stop"));
    // A fully cache-hit prompt: 1M cache-read tokens, zero cache-miss input.
    // pi-ai prices cacheRead independently, so with no cache_read rate this turn
    // would price to $0 and complete fail-open if the category were not checked.
    res.write(sseUsageChunk({ prompt_tokens: 1_000_000, prompt_cache_hit_tokens: 1_000_000, completion_tokens: 0 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-cache-unpriced", { max_cost_usd: 0.5 }, { catalog: [] });
  // Priced for input/output but NOT cache_read — the exact partial-pricing gap.
  bindLoopbackPriced(h, "sess-cache-unpriced", port, {
    params: { timeout_ms: 5000 },
    pricing: { input_per_mtok: 1.0, output_per_mtok: 2.0 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-cache-unpriced", run_id: "run-cu", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-cu");
  assert.equal(failed.error, "cost_budget_unpriced");
  assert.ok(!h.frames.some((f) => f.type === "run.completed" && f.run_id === "run-cu"));
});

test("real run that prices its cache-read tokens is counted and completes within budget (non-faux)", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Cached reply."));
    res.write(sseChunk(null, "stop"));
    res.write(sseUsageChunk({ prompt_tokens: 1_000_000, prompt_cache_hit_tokens: 1_000_000, completion_tokens: 0 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSessionWithLimits(h, "sess-cache-ok", { max_cost_usd: 0.5 }, { catalog: [] });
  // Cache reads ARE priced: 1M cache-read tokens at $0.40/Mtok = $0.40, within
  // the $0.50 ceiling. Proves cache-read usage is priced nonzero and counted.
  bindLoopbackPriced(h, "sess-cache-ok", port, {
    params: { timeout_ms: 5000 },
    pricing: { input_per_mtok: 1.0, output_per_mtok: 2.0, cache_read_per_mtok: 0.4 },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-cache-ok", run_id: "run-co", text: "go" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-co");
  assert.equal(completed.stop_reason, "stop");
  assert.ok(Math.abs(completed.usage.cost_usd - 0.4) < 1e-6, `expected ~$0.40, got ${completed.usage.cost_usd}`);
});

// --- F-W1-R1-2: run.completed usage is complete and cumulative (non-faux) ----
// The ledger records exact per-run accounting, so run.completed must emit the
// cache-read/cache-write tokens and the actual turn count, not just
// input/output/cost. These drive the real openai-completions stack against a
// loopback that reports usage; a settlement that dropped cache tokens or
// defaulted the turn count would fail them.

test("run.completed usage carries cache tokens, total, and the real turn count (non-faux)", async (t) => {
  const { server, port } = await startLoopback((req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write(sseChunk("Cached answer."));
    res.write(sseChunk(null, "stop"));
    // A partially cache-hit prompt: 400 cache-miss input + 600 cache-read + 50 output.
    res.write(sseUsageChunk({ prompt_tokens: 1000, prompt_cache_hit_tokens: 600, completion_tokens: 50 }));
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-usage", { catalog: [] });
  bindLoopback(h, "sess-usage", port, { timeout_ms: 5000 });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-usage", run_id: "run-u", text: "go" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-u");
  const usage = completed.usage;
  assert.equal(usage.output_tokens, 50);
  assert.equal(usage.cache_read, 600); // dropped entirely before the fix
  assert.equal(usage.cache_write, 0);
  assert.equal(usage.input_tokens, 400); // cache-miss input = prompt_tokens - cache-hit
  assert.equal(usage.total_tokens, usage.input_tokens + usage.output_tokens + usage.cache_read + usage.cache_write);
  assert.equal(usage.turns, 1); // a single assistant turn
});

test("run.completed usage is cumulative across a real multi-turn tool loop (non-faux)", async (t) => {
  let requests = 0;
  const { server, port } = await startLoopback((req, res) => {
    requests += 1;
    res.writeHead(200, { "content-type": "text/event-stream" });
    if (requests === 1) {
      // Turn 1: a tool call reporting 100 input / 10 output.
      res.write(sseToolCallChunk("istara_create_task", { title: "x" }));
      res.write(sseChunk(null, "tool_calls"));
      res.write(sseUsageChunk({ prompt_tokens: 100, completion_tokens: 10 }));
    } else {
      // Turn 2: final text reporting 200 input / 20 output.
      res.write(sseChunk("Final answer."));
      res.write(sseChunk(null, "stop"));
      res.write(sseUsageChunk({ prompt_tokens: 200, completion_tokens: 20 }));
    }
    res.end("data: [DONE]\n\n");
  });
  t.after(() => server.close());

  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-multi"); // default CATALOG exposes istara_create_task
  bindLoopback(h, "sess-multi", port, { timeout_ms: 5000 });
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-multi", run_id: "run-m", text: "go" });
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-m");
  h.send({ v: 2, type: "tool.result", session_key: "sess-multi", run_id: "run-m", tool_call_id: toolCall.tool_call_id, ok: true, result: { ok: true } });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-m");
  assert.equal(completed.usage.turns, 2); // was recorded as a single turn before the fix
  assert.equal(completed.usage.input_tokens, 300); // 100 + 200 cumulative, not final-turn-only
  assert.equal(completed.usage.output_tokens, 30); // 10 + 20 cumulative
  assert.ok(requests >= 2, `expected two provider turns, saw ${requests}`);
});

// --- H-11: seq validation ---------------------------------------------------

test("inbound seq violation is a run-scoped protocol_seq_violation", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-seq");
  // session.open consumed inbound seq 1 for this key; replaying seq 1 is a
  // monotonicity violation and the frame must not be processed.
  h.sendRaw({ v: 2, type: "turn.prompt", session_key: "sess-seq", run_id: "r-bad", text: "x", seq: 1 });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "r-bad");
  assert.equal(failed.error, "protocol_seq_violation");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // The session still accepts the next in-order frame.
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-seq", run_id: "r-good", text: "x" });
  const next = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "r-good");
  assert.equal(next.error, "no_provider_bound");
});

// --- H-12: MAX_SESSIONS cap -------------------------------------------------

test("session cap refuses session.open with session_capacity_exceeded", async (t) => {
  const h = new WorkerHarness({ env: { PI_MAX_SESSIONS: "2" } });
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  for (const key of ["cap-1", "cap-2"]) {
    h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog: [] });
    await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
  }
  h.send({ v: 2, type: "session.open", session_key: "cap-3", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  const refused = await h.waitFor((f) => f.type === "session.open_failed" && f.session_key === "cap-3");
  assert.equal(refused.error, "session_capacity_exceeded");

  // Capacity frees up when a session closes.
  h.send({ v: 2, type: "session.close", session_key: "cap-1" });
  await h.waitFor((f) => f.type === "session.closed" && f.session_key === "cap-1");
  h.send({ v: 2, type: "session.open", session_key: "cap-3", system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === "cap-3");
});

// --- H-9: steer/followUp containment ---------------------------------------

test("steer/followUp during a run never crash the worker", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  await openSession(h, "sess-steer");
  bindFaux(h, "sess-steer", [{ text: "First answer." }, { text: "Follow-up answer." }]);
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-steer", run_id: "run-s", text: "go" });
  await h.waitFor((f) => f.type === "run.started" && f.run_id === "run-s");
  h.send({ v: 2, type: "turn.steer", session_key: "sess-steer", run_id: "run-s", text: "steer note" });
  h.send({ v: 2, type: "turn.follow_up", session_key: "sess-steer", run_id: "run-s", text: "follow-up note" });
  // Also exercise the unknown-session paths.
  h.send({ v: 2, type: "turn.steer", session_key: "sess-missing", run_id: "run-x", text: "x" });
  h.send({ v: 2, type: "turn.follow_up", session_key: "sess-missing", run_id: "run-x", text: "x" });

  await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-s");
  assert.ok(!h.frames.some((f) => f.type === "fatal"));

  // Worker is still responsive after steer/followUp traffic.
  h.send({ v: 2, type: "session.open", session_key: "sess-steer-2", system_prompt: "s", history: [], revision: "r1", catalog: [] });
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
    v: 2,
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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-retry", run_id: "run-r", text: "go" });

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
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-noretry", run_id: "run-n", text: "go" });

  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-n");
  assert.ok(failed.error.length > 0);
  // Give any erroneous retry a chance to happen before asserting.
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(requests, 1);
  const deltas = h.frames.filter((f) => f.type === "assistant.delta" && f.run_id === "run-n").map((f) => f.text);
  assert.deepEqual(deltas, ["Partial"]);
});

test("synchronous non-retryable provider throws settle one terminal error without retry", async () => {
  let calls = 0;
  const stream = streamWithGuardedRetry(
    { streamSimple() { calls += 1; throw new Error("invalid request schema"); } },
    {},
    {},
    {},
    3,
  );
  const events = [];
  for await (const event of stream) events.push(event);
  assert.equal(calls, 1);
  assert.equal(events.length, 1);
  assert.equal(events[0].type, "error");
  assert.equal(events[0].reason, "error");
  assert.equal(events[0].error.errorMessage, "invalid request schema");
});

test("synchronous transient provider throws retry only within the bounded budget", async () => {
  let calls = 0;
  const message = {
    stopReason: "stop",
    content: [{ type: "text", text: "recovered" }],
    timestamp: Date.now(),
  };
  const stream = streamWithGuardedRetry(
    {
      streamSimple() {
        calls += 1;
        if (calls === 1) throw new Error("connection refused");
        return (async function* () { yield { type: "done", reason: "stop", message }; })();
      },
    },
    {},
    {},
    {},
    1,
  );
  const events = [];
  for await (const event of stream) events.push(event);
  assert.equal(calls, 2);
  assert.deepEqual(events, [{ type: "done", reason: "stop", message }]);
});
