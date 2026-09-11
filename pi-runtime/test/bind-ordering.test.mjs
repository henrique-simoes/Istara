// F-2 unit pin: bind-before-prompt is enforced explicitly at the session
// layer, independent of stdin chunk batching.
//
// `bindProvider` tracks its in-flight promise on `session._pendingBind`
// (set synchronously on call), and `prompt`/`providerTurn` await it before
// touching the agent. This test calls prompt synchronously after bind — no
// awaits in between — so it is fully deterministic: on the pre-fix code there
// is no `_pendingBind`, prompt observes `_agent === null`, and the run fails
// closed with `no_provider_bound` even though the bind was already queued.

import { test } from "node:test";
import assert from "node:assert/strict";

import { PiSession } from "../src/session.mjs";

function fauxEndpoint(responses) {
  return { endpoint_id: "faux-unit", provider_kind: "faux", faux_responses: responses };
}

test("bindProvider tracks its in-flight bind and clears it afterwards", async () => {
  const session = new PiSession({ sessionKey: "unit-track", emit: () => {} });
  const bind = session.bindProvider(fauxEndpoint([{ text: "hi." }]));
  assert.ok(
    session._pendingBind instanceof Promise,
    "the in-flight bind must be tracked synchronously on call",
  );
  await bind;
  assert.equal(session._pendingBind, null, "the tracked bind must clear once resolved");
});

test("turn.prompt awaits an in-flight provider.bind (F-2, deterministic)", async () => {
  const frames = [];
  const session = new PiSession({ sessionKey: "unit-order", emit: (frame) => frames.push(frame) });
  // Start the bind and, with no await in between, start a prompt: the prompt
  // must wait for the bind instead of failing with no_provider_bound.
  const bind = session.bindProvider(fauxEndpoint([{ text: "bound and ready." }]));
  await session.prompt("unit-run-1", "go");
  await bind;
  const terminal = frames.find(
    (frame) => (frame.type === "run.completed" || frame.type === "run.failed") && frame.run_id === "unit-run-1",
  );
  assert.ok(terminal, `prompt must settle, got: ${JSON.stringify(frames)}`);
  assert.equal(
    terminal.type,
    "run.completed",
    `prompt must wait for the in-flight bind, got: ${JSON.stringify(terminal)}`,
  );
});

test("provider.turn awaits an in-flight provider.bind (F-2, deterministic)", async () => {
  const frames = [];
  const session = new PiSession({ sessionKey: "unit-order-pt", emit: (frame) => frames.push(frame) });
  const bind = session.bindProvider(fauxEndpoint([{ text: "x." }]));
  await session.providerTurn("unit-raw-1", [{ role: "user", content: "inspect" }], []);
  await bind;
  const terminal = frames.find(
    (frame) => (frame.type === "run.completed" || frame.type === "run.failed") && frame.run_id === "unit-raw-1",
  );
  assert.ok(terminal, `provider.turn must settle, got: ${JSON.stringify(frames)}`);
  assert.equal(
    terminal.type,
    "run.completed",
    `provider.turn must wait for the in-flight bind, got: ${JSON.stringify(terminal)}`,
  );
});
