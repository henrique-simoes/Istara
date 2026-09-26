// Run liveness (DEC-10, 2026-09-25): a run is judged by provider progress, with the wall clock as
// a backstop. A steadily streaming model outlives its idle limit; a silent provider does not; time
// spent waiting on Istara's own tools is not provider silence.

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const WORKER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "worker.mjs");
const LONG_TEXT = Array.from({ length: 40 }, (_, i) => `word${i}`).join(" ");
const CATALOG = [
  {
    name: "istara_create_task",
    description: "Create a task",
    parameters: { type: "object", properties: { title: { type: "string" } }, required: ["title"], additionalProperties: false },
  },
];

class Harness {
  constructor() {
    this.child = spawn(process.execPath, [WORKER], { stdio: ["pipe", "pipe", "pipe"] });
    this.frames = [];
    this.stderr = "";
    this._buffer = "";
    this._seqs = new Map();
    this.child.stdout.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => {
      this._buffer += chunk;
      let idx;
      while ((idx = this._buffer.indexOf("\n")) !== -1) {
        const line = this._buffer.slice(0, idx).trim();
        this._buffer = this._buffer.slice(idx + 1);
        if (line) this.frames.push(JSON.parse(line));
      }
    });
    this.child.stderr.on("data", (c) => (this.stderr += c));
  }

  send(frame) {
    const key = typeof frame.session_key === "string" ? frame.session_key : null;
    const next = (this._seqs.get(key) || 0) + 1;
    this._seqs.set(key, next);
    this.child.stdin.write(JSON.stringify({ seq: next, ...frame }) + "\n");
  }

  async waitFor(predicate, timeoutMs = 15000) {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const found = this.frames.find(predicate);
      if (found) return found;
      if (Date.now() > deadline) throw new Error(`timeout; frames=${JSON.stringify(this.frames.slice(-5))} stderr=${this.stderr}`);
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
  }

  close() {
    this.child.kill();
  }
}

async function openSession(h, key, limits, catalog = CATALOG) {
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog, limits });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
}

function bindFaux(h, key, responses, tokensPerSecond) {
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: responses, faux_tokens_per_second: tokensPerSecond },
  });
}

const terminal = (runId) => (f) => (f.type === "run.completed" || f.type === "run.failed") && f.run_id === runId;

test("a provider that goes silent fails with idle_timeout_exceeded, long before the wall clock", async (t) => {
  const h = new Harness();
  t.after(() => h.close());
  await openSession(h, "sess-idle", { max_wall_clock_ms: 20000, max_idle_ms: 300 });
  bindFaux(h, "sess-idle", [{ text: LONG_TEXT }], 2); // a token every ~500 ms: silence > 300 ms
  const started = Date.now();
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-idle", run_id: "run-idle", text: "go" });
  const end = await h.waitFor(terminal("run-idle"));
  assert.equal(end.type, "run.failed");
  assert.equal(end.error, "idle_timeout_exceeded");
  assert.ok(Date.now() - started < 5000, "the idle limit, not the 20 s wall clock, ended the run");
});

test("a model that keeps streaming outlives its idle limit", async (t) => {
  const h = new Harness();
  t.after(() => h.close());
  await openSession(h, "sess-steady", { max_wall_clock_ms: 20000, max_idle_ms: 600 });
  bindFaux(h, "sess-steady", [{ text: LONG_TEXT }], 40); // steady, ~25 ms between tokens
  const started = Date.now();
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-steady", run_id: "run-steady", text: "go" });
  const end = await h.waitFor(terminal("run-steady"));
  assert.equal(end.type, "run.completed", JSON.stringify(end));
  assert.ok(Date.now() - started > 600, "the run lasted longer than the idle limit and still completed");
});

test("waiting on Istara's own tool is not provider silence", async (t) => {
  const h = new Harness();
  t.after(() => h.close());
  await openSession(h, "sess-tool", { max_wall_clock_ms: 20000, max_idle_ms: 300 });
  bindFaux(h, "sess-tool", [
    { tool_calls: [{ name: "istara_create_task", arguments: { title: "x" } }], stop_reason: "toolUse" },
    { text: "done" },
  ], 0);
  h.send({ v: 2, type: "turn.prompt", session_key: "sess-tool", run_id: "run-tool", text: "go" });
  const call = await h.waitFor((f) => f.type === "tool.call" && f.run_id === "run-tool");
  await new Promise((resolve) => setTimeout(resolve, 900)); // the tool takes longer than the idle limit
  h.send({ v: 2, type: "tool.result", session_key: "sess-tool", run_id: "run-tool", tool_call_id: call.tool_call_id, ok: true, result: { ok: true } });
  const end = await h.waitFor(terminal("run-tool"));
  assert.equal(end.type, "run.completed", JSON.stringify(end));
});
