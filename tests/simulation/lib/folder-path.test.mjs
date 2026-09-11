import test from "node:test";
import assert from "node:assert/strict";

import { resolveLinkedFolderPath } from "../scenarios/29-documents-system.mjs";

test("linked-folder simulation honors an explicitly shared path", () => {
  assert.deepEqual(
    resolveLinkedFolderPath({ configuredPath: "/app/data/simulation-shared", tempDir: "/tmp", now: 123 }),
    { path: "/app/data/simulation-shared", shared: true },
  );
});

test("linked-folder simulation keeps an isolated temporary fallback", () => {
  const result = resolveLinkedFolderPath({ configuredPath: "", tempDir: "/tmp", now: 123 });
  assert.equal(result.shared, false);
  assert.match(result.path, /^\/tmp\/istara-test-123$/);
});
