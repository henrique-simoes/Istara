// Adversarial stub worker (test-only): answers `hello` with a protocol v1
// `ready` and then goes silent. The backend supervisor must refuse it with a
// typed protocol_version_mismatch instead of driving runs on a worker that
// cannot honor the v2 forced structured contract.
let buffer = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  let idx;
  while ((idx = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    const frame = JSON.parse(line);
    if (frame.type === "hello") {
      process.stdout.write(
        JSON.stringify({ v: 1, type: "ready", protocol_version: 1, pi_agent_core: "0.0.0", pi_ai: "0.0.0", seq: 1 }) + "\n",
      );
    }
  }
});
