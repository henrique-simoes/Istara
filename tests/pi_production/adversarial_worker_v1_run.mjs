// Adversarial stub worker (test-only, F-W1-R1-1): completes a VALID v2
// handshake and session open, then — on the first turn.prompt — downgrades to
// protocol v1 and emits run frames the backend must never trust. It first
// sends a v1 tool.call (to prove the Python authority never executes a
// wrong-version tool round-trip) and then a v1 run.completed carrying a forged
// structured artifact and usage (to prove no partial/terminal data from a
// mismatched frame is ever accepted). A compliant supervisor rejects each
// frame per-frame with a typed protocol_version_mismatch and settles the run
// without a tool.result or accepted artifact.
let buffer = "";
const seqs = new Map(); // session_key -> outbound seq
function nextSeq(key) {
  const n = (seqs.get(key) || 0) + 1;
  seqs.set(key, n);
  return n;
}
function send(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  let idx;
  while ((idx = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    const frame = JSON.parse(line);
    switch (frame.type) {
      case "hello":
        send({ v: 2, type: "ready", protocol_version: 2, pi_agent_core: "0.0.0", pi_ai: "0.0.0", seq: 1 });
        break;
      case "session.open":
        send({ v: 2, type: "session.opened", session_key: frame.session_key, seq: nextSeq(frame.session_key) });
        break;
      case "turn.prompt": {
        const key = frame.session_key;
        // Downgrade: a v1-framed tool.call on a v2 session. The backend must
        // reject it and NEVER answer with a tool.result.
        send({
          v: 1, type: "tool.call", session_key: key, run_id: frame.run_id,
          tool_call_id: "adv-1", name: "create_task", arguments: { title: "pwned" },
          seq: nextSeq(key),
        });
        // And a v1-framed run.completed carrying a forged artifact/usage: even
        // if the backend kept the run alive, it must never surface this.
        send({
          v: 1, type: "run.completed", session_key: key, run_id: frame.run_id,
          usage: { input_tokens: 99, output_tokens: 99, cost_usd: 0 },
          stop_reason: "stop", structured: { pwned: true }, seq: nextSeq(key),
        });
        break;
      }
      case "tool.result":
        // Must never arrive: a rejected v1 tool.call is never executed. Signal
        // the contract violation on stderr so the harness log records it.
        process.stderr.write("[adv] VIOLATION: received tool.result for a rejected v1 tool.call\n");
        break;
      case "session.close":
        send({ v: 2, type: "session.closed", session_key: frame.session_key, seq: nextSeq(frame.session_key) });
        break;
      default:
        break;
    }
  }
});
