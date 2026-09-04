import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const scenarioPath = join(
  import.meta.dirname,
  "..",
  "scenarios",
  "20-all-skills-comprehensive.mjs",
);

test("Scenario 20 gates live skill execution on chat readiness", () => {
  const source = readFileSync(scenarioPath, "utf8");
  assert.match(source, /chat_ready/);
  assert.match(source, /LLM_CONNECTED\s*&&\s*CHAT_READY/);
  assert.match(source, /\[skipped\].*chat-ready/);
});
