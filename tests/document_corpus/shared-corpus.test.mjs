import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join } from "node:path";
import test from "node:test";

import {
  CANONICAL_CORPUS_DIR,
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

test("canonical markdown sources stay raw and do not ship pre-digested candidate evidence", () => {
  const manifest = loadCanonicalManifest();
  const forbiddenRawSourcePhrases = [
    "## Evidence unit candidate",
    "Coding hints:",
    "Implication candidate:",
    "Report gate reminder:",
    "This synthetic source supports",
    [
      "I can only approve a recommendation when the system shows which task,",
      "transcript, ticket, or survey row produced it",
    ].join(" "),
  ];
  const violations = [];

  for (const entry of manifest.sources.filter((source) => extname(source.path).toLowerCase() === ".md")) {
    const content = readFileSync(join(CANONICAL_CORPUS_DIR, entry.path), "utf8");
    for (const phrase of forbiddenRawSourcePhrases) {
      if (content.includes(phrase)) violations.push(`${entry.id}:${phrase}`);
    }
  }

  assert.deepEqual(violations, []);
});

test("canonical interviews are transcript-like raw sources with coherent participants and timestamps", () => {
  const manifest = loadCanonicalManifest();
  const failures = [];

  for (const entry of manifest.sources.filter((source) => source.method === "interview")) {
    const content = readFileSync(join(CANONICAL_CORPUS_DIR, entry.path), "utf8");
    const lines = content.split(/\r?\n/);
    const participant = entry.participant_ids?.[0];
    const speakerLines = lines.filter((line) => /^(Moderator|P\d{2}): /.test(line));
    const participantLines = speakerLines.filter((line) => /^P\d{2}: /.test(line));
    const wrongParticipantLines = participantLines.filter((line) => !line.startsWith(`${participant}: `));
    const timestamps = lines
      .map((line) => line.match(/^### (\d{2}):(\d{2}) - /))
      .filter(Boolean)
      .map((match) => Number(match[1]) * 60 + Number(match[2]));
    const nonMonotonic = timestamps.some((value, index) => index > 0 && value <= timestamps[index - 1]);
    const participantQuotes = participantLines.map((line) => line.replace(/^P\d{2}: /, ""));
    const uniqueQuoteRatio = new Set(participantQuotes).size / Math.max(participantQuotes.length, 1);

    if (speakerLines.length < 250) failures.push(`${entry.id}:too_few_speaker_turns:${speakerLines.length}`);
    if (wrongParticipantLines.length > 0) failures.push(`${entry.id}:mixed_participants:${wrongParticipantLines.length}`);
    if (timestamps.length < 80) failures.push(`${entry.id}:too_few_timestamps:${timestamps.length}`);
    if (nonMonotonic) failures.push(`${entry.id}:non_monotonic_timestamps`);
    if (uniqueQuoteRatio < 0.9) failures.push(`${entry.id}:repeated_participant_quotes:${uniqueQuoteRatio.toFixed(2)}`);
    if (entry.language === "es" && !/Necesito|Confio|permiso|evidencia/.test(content)) {
      failures.push(`${entry.id}:spanish_label_without_spanish_turns`);
    }
    if (entry.language === "pt-BR" && !/Preciso|confio|permissao|evidencia/.test(content)) {
      failures.push(`${entry.id}:portuguese_label_without_portuguese_turns`);
    }
  }

  assert.deepEqual(failures, []);
});

test("canonical raw source excerpts are varied enough to catch template repetition", () => {
  const manifest = loadCanonicalManifest();
  const excerptCounts = new Map();

  for (const entry of manifest.sources) {
    if (extname(entry.path).toLowerCase() !== ".md") continue;
    const content = readFileSync(join(CANONICAL_CORPUS_DIR, entry.path), "utf8");
    for (const line of content.split(/\r?\n/)) {
      if (!/^(Verbatim\/source excerpt:|P\d{2}: ")/.test(line)) continue;
      const normalized = line.trim();
      excerptCounts.set(normalized, (excerptCounts.get(normalized) || 0) + 1);
    }
  }

  const repeated = [...excerptCounts.entries()]
    .filter(([, count]) => count > 1)
    .map(([line, count]) => `${count}x ${line.slice(0, 120)}`);
  assert.deepEqual(repeated, []);
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
