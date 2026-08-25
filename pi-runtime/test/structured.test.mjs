// Forced structured-output contract tests (protocol v2). Spawns the real
// worker child and drives it through the faux provider (no network). Covers:
// captured (never executed) forced tool results, free-form JSON rejection,
// unsupported-schema fail-closed, missing/incorrect tool calls, tool_choice
// validation, and both-side protocol version validation.

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { captureParameters, mapToolChoiceForApi, translateOutputSchema } from "../src/structured.mjs";

const WORKER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "worker.mjs");

const SCHEMA = {
  type: "object",
  properties: {
    verdict: { type: "string", enum: ["pass", "fail"] },
    confidence: { type: "number", minimum: 0, maximum: 1 },
  },
  required: ["verdict", "confidence"],
  additionalProperties: false,
};

test("capture tool parameters keep an object root accepted by OpenAI-compatible APIs", () => {
  const parameters = captureParameters(translateOutputSchema(SCHEMA));

  assert.equal(parameters.type, "object");
  assert.equal(parameters.anyOf, undefined);
  assert.deepEqual(
    parameters.properties.verdict.anyOf.map((arm) => arm.const),
    ["pass", "fail"],
  );
});

test("Codex Responses requires the sole structured capture tool", () => {
  const mapped = mapToolChoiceForApi("openai-codex-responses", {
    kind: "tool",
    name: "emit_structured_output",
  });

  assert.equal(mapped, "required");
});

class WorkerHarness {
  constructor() {
    this.child = spawn(process.execPath, [WORKER], { stdio: ["pipe", "pipe", "pipe"] });
    this.frames = [];
    this._waiters = [];
    this._buffer = "";
    this._seqs = new Map();
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
    this.child.kill("SIGKILL");
  }
}

async function openFauxSession(h, key, fauxResponses) {
  h.send({ v: 2, type: "hello", protocol_version: 2 });
  await h.waitFor((f) => f.type === "ready");
  h.send({ v: 2, type: "session.open", session_key: key, system_prompt: "s", history: [], revision: "r1", catalog: [] });
  await h.waitFor((f) => f.type === "session.opened" && f.session_key === key);
  h.send({
    v: 2,
    type: "provider.bind",
    session_key: key,
    endpoint: { endpoint_id: "faux", provider_kind: "faux", faux_responses: fauxResponses },
  });
}

test("structured run captures the forced tool call; nothing round-trips as tool.call", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-structured";
  await openFauxSession(h, key, [
    { tool_calls: [{ name: "emit_structured_output", arguments: { verdict: "pass", confidence: 0.9 } }], stop_reason: "toolUse" },
  ]);
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-s", text: "grade", output_schema: SCHEMA });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-s");
  assert.deepEqual(completed.structured, { verdict: "pass", confidence: 0.9 });
  // Captured, not executed: the forced tool must never reach the authority.
  assert.equal(h.frames.some((f) => f.type === "tool.call" && f.name === "emit_structured_output"), false);
});

test("free-form JSON text is never accepted as structured output", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-freeform";
  await openFauxSession(h, key, [{ text: '{"verdict": "pass", "confidence": 0.9}' }]);
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-f", text: "grade", output_schema: SCHEMA });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-f");
  assert.equal(failed.error, "structured_output_missing");
});

test("an incorrect tool call settles as structured_output_missing", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-wrongtool";
  // The model calls a made-up tool instead of the forced one; agent-core
  // answers with an error tool result, then the model stops with text.
  await openFauxSession(h, key, [
    { tool_calls: [{ name: "not_the_forced_tool", arguments: {} }], stop_reason: "toolUse" },
    { text: "done" },
  ]);
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-w", text: "grade", output_schema: SCHEMA });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-w");
  assert.equal(failed.error, "structured_output_missing");
});

test("unsupported schema fails closed before any provider call", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-unsupported";
  await openFauxSession(h, key, [{ text: "should never be consumed" }]);
  h.send({
    v: 2,
    type: "turn.prompt",
    session_key: key,
    run_id: "run-u",
    text: "grade",
    output_schema: { type: "object", properties: { a: { $ref: "#/$defs/x" } } },
  });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-u");
  assert.match(failed.error, /^structured_output_schema_unsupported:.*\$ref/);
});

test("invalid tool_choice shape is a typed failure", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-badchoice";
  await openFauxSession(h, key, [{ text: "x" }]);
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-tc", text: "go", tool_choice: { bogus: true } });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-tc");
  assert.equal(failed.error, "invalid_tool_choice");
});

test("handshake with a mismatched protocol version gets a typed fatal, never ready", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  h.send({ v: 1, type: "hello", protocol_version: 1 });
  const fatal = await h.waitFor((f) => f.type === "fatal");
  assert.equal(fatal.error, "protocol_version_mismatch");
  assert.equal(fatal.protocol_version, 2);
  assert.equal(h.frames.some((f) => f.type === "ready"), false);
});

test("a mismatched-version frame is rejected without consuming seq", async (t) => {
  const h = new WorkerHarness();
  t.after(() => h.close());
  const key = "sess-version";
  await openFauxSession(h, key, [{ text: "ok" }]);
  // v:1 frame (explicitly overriding the harness's v) is rejected run-scoped.
  h.send({ v: 1, type: "turn.prompt", session_key: key, run_id: "run-old", text: "go" });
  const failed = await h.waitFor((f) => f.type === "run.failed" && f.run_id === "run-old");
  assert.equal(failed.error, "protocol_version_mismatch");
  // The rejected frame must not wedge the session: a valid v2 run still works.
  h.send({ v: 2, type: "turn.prompt", session_key: key, run_id: "run-new", text: "go" });
  const completed = await h.waitFor((f) => f.type === "run.completed" && f.run_id === "run-new");
  assert.ok(completed.usage);
});
