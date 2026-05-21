import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  CANONICAL_CORPUS_SLICES,
  SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
  canonicalCorpusSummary,
  materializeSharedDocumentCorpus,
  selectCanonicalCorpus,
} from "./shared-corpus.mjs";

test("canonical corpus exposes representative full end-to-end research volume", () => {
  const summary = canonicalCorpusSummary();
  assert.ok(summary.total_sources >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
  assert.ok(summary.long_form_sources >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
  assert.ok(summary.slices["full-end-to-end"].source_count >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
});

test("canonical corpus exposes required named slices", () => {
  for (const slice of CANONICAL_CORPUS_SLICES) {
    const selected = selectCanonicalCorpus({ slice, minimumSources: 1 });
    assert.ok(selected.length > 0, `expected ${slice} to select canonical sources`);
    assert.ok(selected.every((entry) => entry.slices.includes(slice)));
  }
});

test("shared corpus materialization can require canonical-only sources", () => {
  const root = mkdtempSync(join(tmpdir(), "istara-canonical-corpus-"));
  try {
    const materialized = materializeSharedDocumentCorpus({
      outputDir: join(root, "corpus"),
      slice: "interview-heavy",
      minimumSources: 10,
      canonicalOnly: true,
    });
    assert.equal(materialized.fixture_count, 0);
    assert.equal(materialized.generated_count, 0);
    assert.ok(materialized.canonical_count >= 10);
    assert.ok(materialized.manifest.every((entry) => entry.corpus_source === "canonical"));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
