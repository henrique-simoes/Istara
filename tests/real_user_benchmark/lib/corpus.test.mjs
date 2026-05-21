import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { generateCorpus } from "./corpus.mjs";

test("real-user corpus materializes representative shared document volume", () => {
  const root = mkdtempSync(join(tmpdir(), "istara-corpus-"));
  try {
    const summary = generateCorpus({ outputDir: join(root, "corpus") });
    assert.ok(summary.document_count >= 120);
    assert.ok(summary.canonical_corpus.total_sources >= 120);
    assert.ok(summary.shared_corpus.canonical_count >= 120);
    assert.equal(summary.shared_corpus.fixture_count, 0);
    assert.equal(summary.shared_corpus.generated_count, 0);
    assert.ok(summary.manifest.filter((item) => item.bytes >= 1000).length >= 120);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
