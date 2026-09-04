import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const scenarioPath = join(
  import.meta.dirname,
  "..",
  "scenarios",
  "05-chat-interaction.mjs",
);

test("Chat Interaction gates live assertions on chat readiness", () => {
  const source = readFileSync(scenarioPath, "utf8");
  assert.match(source, /llmReadiness\?\.chat_ready\s*===\s*false/);
  assert.match(source, /skipped:\s*true/);
});
