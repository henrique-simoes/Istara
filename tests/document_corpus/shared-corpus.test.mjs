import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join } from "node:path";
import test from "node:test";

import {
  CANONICAL_CORPUS_SLICES,
  ISTARA_UPLOAD_PROCESSABLE_EXTENSIONS,
  SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
  canonicalCorpusSummary,
  loadCanonicalManifest,
  materializeSharedDocumentCorpus,
  selectCanonicalCorpus,
} from "./shared-corpus.mjs";

test("canonical corpus exposes representative full end-to-end research volume", () => {
  const summary = canonicalCorpusSummary();
  assert.ok(summary.total_sources >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
  assert.ok(summary.long_form_sources >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
  assert.ok(summary.total_words >= 1_000_000, "canonical corpus should be large enough for document-heavy research stress tests");
  assert.ok(summary.average_words_per_source >= 5_000, "canonical sources should be deeper than tiny fixtures");
  assert.ok(summary.slices["full-end-to-end"].source_count >= SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES);
});

test("canonical corpus exposes required named slices", () => {
  for (const slice of CANONICAL_CORPUS_SLICES) {
    const selected = selectCanonicalCorpus({ slice, minimumSources: 1 });
    assert.ok(selected.length > 0, `expected ${slice} to select canonical sources`);
    assert.ok(selected.every((entry) => entry.slices.includes(slice)));
  }
});

test("canonical corpus accepts documented slash-style selector aliases", () => {
  const findings = selectCanonicalCorpus({ slice: "findings/reporting", minimumSources: 1 });
  const malformed = selectCanonicalCorpus({ slice: "malformed/edge-case", minimumSources: 1 });
  assert.ok(findings.every((entry) => entry.slices.includes("findings-reporting")));
  assert.ok(malformed.every((entry) => entry.slices.includes("malformed-edge-case")));
});

test("canonical corpus exposes research-validity contract slices with representative volume", () => {
  const required = {
    "coding-reliability": 20,
    "graph-synthesis": 20,
    "low-consensus-review": 10,
  };
  for (const [slice, minimumSources] of Object.entries(required)) {
    const selected = selectCanonicalCorpus({ slice, minimumSources });
    assert.ok(
      selected.every((entry) => entry.intended_use === "canonical_product_level_synthetic_ux_research"),
      `${slice} must be manifest-backed canonical material`,
    );
    assert.ok(
      selected.every((entry) => entry.report_readiness === "raw_source_not_report_ready_until_done_task_approval"),
      `${slice} must preserve report-readiness gating metadata`,
    );
  }
});

test("canonical corpus sources use upload-processable Istara file types", () => {
  const manifest = loadCanonicalManifest();
  const supported = new Set(ISTARA_UPLOAD_PROCESSABLE_EXTENSIONS);
  const unsupported = manifest.sources
    .filter((entry) => !supported.has(extname(entry.relative_path || entry.path).toLowerCase()))
    .map((entry) => `${entry.id}:${entry.relative_path || entry.path}`);
  assert.deepEqual(unsupported, []);
});

test("canonical corpus preserves deep source-level word counts for realistic research material", () => {
  const manifest = loadCanonicalManifest();
  const deepSources = manifest.sources.filter((entry) => (entry.word_count || 0) >= 10_000);
  const interviewSources = manifest.sources.filter((entry) => entry.method === "interview");

  assert.ok(deepSources.length >= 40, "expected many sources with long-form research depth");
  assert.ok(interviewSources.length >= 20);
  assert.ok(interviewSources.every((entry) => (entry.word_count || 0) >= 25_000));
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
