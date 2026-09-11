import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dirname, "..", "..", "..");

for (const scenario of [
  "30-event-wiring-audit.mjs",
  "31-task-documents-tools.mjs",
]) {
  test(`${scenario} supports a mounted repository root`, () => {
    const source = readFileSync(join(root, "tests", "simulation", "scenarios", scenario), "utf8");
    assert.match(source, /ISTARA_SIM_REPO_ROOT/);
    assert.match(source, /join\(__dirname, "\.\.", "\.\.", "\.\."\)/);
  });
}
