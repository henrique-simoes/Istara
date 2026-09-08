// End-to-end worker protocol tests. Spawns the real worker child, drives the
// NDJSON protocol, and exercises the real pi-agent-core Agent through the faux
// provider (Node-unit-test-only, no network).

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const WORKER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "worker.mjs");

class WorkerHarness {
  constructor() {
    this.child = spawn(process.execPath, [WORKER], { stdio: ["pipe", "pipe", "pipe"] });
    this.frames = [];
    this._waiters = [];
    this._buffer = "";
    this._seqs = new Map(); // session_key (null = connection-level) -> last outbound seq
    this.stderr = "";
    this.child.stdout.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => {
      this._buffer += chunk;
      let idx;
      while ((idx = this._buffer.indexOf("\n")) !== -1) {
        const line = this._buffer.slice(0, idx).trim();
        this._buffer = this._buffer.slice(idx + 1);
        if (!line) continue;
        const frame = JSON.parse(line);
        this.frames.push(frame);
        for (const w of this._waiters.splice(0)) w();
      }
    });
    this.child.stderr.on("data", (c) => (this.stderr += c));
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

  async waitFor(predicate, timeoutMs = 5000) {
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

test("handshake returns ready with package versions", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  const ready = await h.waitFor((f) => f.type === "ready");
  assert.equal(ready.protocol_version, 2);
  assert.match(ready.pi_agent_core, /^\d+\.\d+\.\d+/);
  assert.match(ready.pi_ai, /^\d+\.\d+\.\d+/);
});

test("full prompt→tool.call→tool.result→run.completed round-trip", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");

  const key = "sess-1";
  h.send({
    v: 2,
    type: "session.open",
    session_key: key,
    system_prompt: "You are a test.",
    history: [],
    revision: "r1",
    catalog: [
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
    ],
  });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);

  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: {
      endpoint_id: "faux",
      provider_kind: "faux",
      faux_responses: [
        { tool_calls: [{ name: "istara_create_task", arguments: { title: "Test task" } }], stop_reason: "toolUse" },
        { text: "Created the task." },
      ],
    },
  });

  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-1", text: "Create a task" });

  await h.waitFor((f) => f.type === "run.started" && f.run_id === "run-1");
  const toolCall = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-1");
  assert.equal(toolCall.name, "istara_create_task");
  assert.deepEqual(toolCall.arguments, { title: "Test task" });

  // Authority responds with a successful tool result.
  h.send({
    v: 2,
    type: "tool.result",
    session_key: key,
    run_id: "run-1",
    tool_call_id: toolCall.tool_call_id,
    ok: true,
    result: { ok: true, id: "task-1" },
  });

  const delta = await h.waitFor((f) => f.type === "assistant.delta" && f.run_id === "run-1");
  assert.ok(delta.text.length > 0);
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-1");
  assert.equal(completed.stop_reason, "stop");
  assert.ok(completed.usage);
});

test("structured tool error keeps the session alive and completes", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  const key = "sess-err";
  h.send({
    v: 2,
    type: "session.open",
    session_key: key,
    system_prompt: "s",
    history: [],
    revision: "r1",
    catalog: [{ name: "istara_create_task", description: "d", parameters: { type: "object", properties: { title: { type: "string" } } } }],
  });
  await h.waitFor((f) => f.type === "session.opened");
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: {
      endpoint_id: "faux",
      provider_kind: "faux",
      faux_responses: [
        { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
        { text: "Understood the tool failed." },
      ],
    },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "r", text: "go" });
  const toolCall = await h.waitFor((f) => f.type === "tool.call");
  h.send({ v: 2, type: "tool.result", session_key: key, run_id: "r", tool_call_id: toolCall.tool_call_id, ok: false, error: "not_authorized" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "r");
  assert.ok(completed);
});

test("prompt without provider binding fails closed", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  const key = "sess-nobind";
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened");
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "r", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "r");
  assert.equal(failed.error, "no_provider_bound");
});

test("cross-chunk bind->prompt ordering: prompt waits for an in-flight bind (F-2)", async (t) => {
  // The bind is the first in this worker process, so it pays the cold
  // once-per-process registry import while the prompt is already queued in a
  // later stdin chunk. Without cross-chunk enforcement the prompt would run
  // on a missing binding and fail with no_provider_bound.
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  const key = "sess-bind-order";
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: { endpoint_id: "faux-order", provider_kind: "faux", faux_responses: [{ text: "bound and ready." }] },
  });
  // Separate stdin chunk ~5ms later: long enough to guarantee a distinct
  // `data` event (the worker drains the first write within a millisecond),
  // short enough that the cold once-per-process registry import (~40ms)
  // inside the bind above is still in flight — the exact cross-chunk race.
  await new Promise((resolve) => setTimeout(resolve, 5));
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "order-1", text: "go" });
  const terminal = await h.waitFor(
    (f) => (f.type === "run.completed" || f.type === "run.failed") && f.run_id === "order-1",
    15000,
  );
  assert.equal(terminal.type, "run.completed", `prompt must wait for the in-flight bind, got: ${JSON.stringify(terminal)}`);
});

test("a blocked close never starves an unrelated session (F-3)", async (t) => {
  // Session A parks on an unanswered tool.call; session.close(A) then
  // session.open(B) arrive batched behind it. B must still open promptly —
  // pre-fix the shared dispatch chain starved every frame behind the close.
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  const keyA = "sess-blocked-a";
  h.send({
    v: 2,
    type: "session.open",
    session_key: keyA,
    system_prompt: "s",
    history: [],
    revision: "r1",
    catalog: [{ name: "t_block", description: "d", parameters: { type: "object", properties: {} } }],
  });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === keyA);
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: keyA,
    endpoint: {
      endpoint_id: "faux-blocked",
      provider_kind: "faux",
      faux_responses: [
        { tool_calls: [{ name: "t_block", arguments: {} }], stop_reason: "toolUse" },
        { text: "done." },
      ],
    },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: keyA, run_id: "blocked-1", text: "go" });
  // A is now parked: the tool promise settles only on tool.result, which we
  // deliberately withhold.
  await h.waitFor((f) => f.type === "tool.call" && f.run_id === "blocked-1", 15000);
  // Batched behind the parked close: B must still open.
  h.send({ v: 2, type: "session.close", session_key: keyA });
  const keyB = "sess-unblocked-b";
  h.send({ v: 2, type: "session.open", session_key: keyB, system_prompt: "s", history: [], revision: "r1", catalog: [] });
  const openedB = await h.waitFor((f) => f.type === "session.opened" && f.session_key === keyB, 15000);
  assert.ok(openedB, "unrelated session B must open while A's close is blocked");
  // B is fully live: it binds and completes a turn of its own.
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: keyB,
    endpoint: { endpoint_id: "faux-b", provider_kind: "faux", faux_responses: [{ text: "b alive." }] },
  });
  h.send({ v: 2, type: "turn.prompt", session_key: keyB, run_id: "b-1", text: "go" });
  const doneB = await h.waitFor(
    (f) => (f.type === "run.completed" || f.type === "run.failed") && f.run_id === "b-1",
    15000,
  );
  assert.equal(doneB.type, "run.completed", `B must complete while A is parked, got: ${JSON.stringify(doneB)}`);
});

test("provider-only turn returns raw tool calls without executing the Pi agent loop", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  const key = "sess-provider-only";
  h.send({
    v: 2,
    type: "session.open",
    session_key: key,
    system_prompt: "legacy loop system",
    history: [],
    revision: "r1",
    catalog: [],
  });
  await h.waitFor((f) => f.type === "session.opened");
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: {
      endpoint_id: "faux",
      provider_kind: "faux",
      faux_responses: [
        {
          text: "I will inspect it.",
          tool_calls: [{ name: "search_documents", arguments: { query: "bias" } }],
          stop_reason: "toolUse",
        },
      ],
    },
  });
  h.send({
    v: 2,
    type: "provider.turn",
    session_key: key,
    run_id: "raw-1",
    messages: [{ role: "user", content: "inspect" }],
    tools: [{
      name: "search_documents",
      description: "Search documents",
      parameters: { type: "object", properties: { query: { type: "string" } } },
    }],
  });

  const completed = await h.waitFor(
    (f) => f.type === "run.completed" && f.run_id === "raw-1"
  );
  assert.equal(completed.stop_reason, "toolUse");
  assert.equal(completed.provider_message.content[0].type, "toolCall");
  assert.equal(completed.provider_message.content[0].name, "search_documents");
  assert.equal(
    h.frames.some((f) => f.type === "tool.call" && f.run_id === "raw-1"),
    false,
    "the outer legacy loop, not the worker agent, owns tool execution",
  );
});
