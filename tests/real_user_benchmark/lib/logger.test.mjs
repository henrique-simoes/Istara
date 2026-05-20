import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { BenchmarkLogger } from "./logger.mjs";

test("BenchmarkLogger applies sanitizer recursively to JSONL records", () => {
  const rootDir = mkdtempSync(join(tmpdir(), "istara-rub-logger-"));
  try {
    const logger = new BenchmarkLogger({ rootDir, runId: "run", mode: "test" });
    logger.init();
    logger.setSanitizer((value) => {
      if (typeof value === "string") return value.replace(/secret-token/g, "[redacted]");
      if (Array.isArray(value)) return value.map((item) => logger.sanitize(item));
      if (value && typeof value === "object") {
        return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, logger.sanitize(item)]));
      }
      return value;
    });

    logger.action("ui.console", {
      text: "ws://localhost/ws?token=secret-token",
      nested: { values: ["secret-token"] },
    });

    const log = readFileSync(join(rootDir, "runs", "run", "action-log.jsonl"), "utf8");
    assert.match(log, /\[redacted\]/);
    assert.doesNotMatch(log, /secret-token/);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});
