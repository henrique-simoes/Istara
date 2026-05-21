import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "fs";
import { basename, dirname, join, relative, resolve } from "path";
import { fileURLToPath } from "url";

export const SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES = 120;
export const SHARED_DOCUMENT_CORPUS_MIN_BYTES = 1000;

const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(MODULE_DIR, "../..");
export const CANONICAL_CORPUS_DIR = join(MODULE_DIR, "canonical");
export const CANONICAL_MANIFEST_PATH = join(CANONICAL_CORPUS_DIR, "manifest.json");
export const CANONICAL_CORPUS_SLICES = [
  "interview-heavy",
  "survey-heavy",
  "usability-heavy",
  "accessibility-heavy",
  "findings-reporting",
  "multilingual",
  "malformed-edge-case",
  "upload-smoke",
  "full-end-to-end",
];

const CURATED_FIXTURE_DIRS = [
  "tests/simulation/data/fixtures",
  "tests/fixtures",
];

const researchDomains = [
  "appointment preparation",
  "caregiver permissions",
  "readiness timelines",
  "staff handoff",
  "multilingual reminders",
  "blocked-task recovery",
  "reporting trust",
  "source traceability",
];

function listFiles(root) {
  if (!existsSync(root)) return [];
  const output = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      output.push(...listFiles(path));
    } else if (/\.(csv|json|jsonl|md|txt)$/i.test(entry.name)) {
      output.push(path);
    }
  }
  return output;
}

function ensureUniqueRelativePath(relativePath, used) {
  if (!used.has(relativePath)) return relativePath;
  const extIndex = relativePath.lastIndexOf(".");
  const stem = extIndex >= 0 ? relativePath.slice(0, extIndex) : relativePath;
  const ext = extIndex >= 0 ? relativePath.slice(extIndex) : "";
  let index = 2;
  while (used.has(`${stem}-${index}${ext}`)) {
    index += 1;
  }
  return `${stem}-${index}${ext}`;
}

function generatedLongSource(index) {
  const domain = researchDomains[index % researchDomains.length];
  const contradiction = researchDomains[(index + 3) % researchDomains.length];
  const role = ["patient", "caregiver", "care coordinator", "nurse manager"][index % 4];
  const sections = [];
  for (let section = 1; section <= 12; section += 1) {
    sections.push([
      `## Observation ${section}`,
      "",
      `Participant group: ${role}. Domain: ${domain}.`,
      `Evidence says the team needs clearer source labels before trusting automation, especially when ${domain} overlaps with ${contradiction}.`,
      `Quote: "I can approve a workflow only when I know which document, transcript, or ticket produced the recommendation."`,
      "Counter-signal: analytics suggest some users skip details when reminders arrive late, so the synthesis must not overfit to interview enthusiasm.",
      "Research implication: findings should cite concrete files and distinguish approved tasks from material still waiting for human review.",
      "",
    ].join("\n"));
  }
  return [
    `# Shared UX Research Source ${String(index).padStart(3, "0")}`,
    "",
    "This synthetic long-form source belongs to Istara's shared document corpus fallback for tests that are not yet product-level research flows.",
    "",
    ...sections,
  ].join("\n");
}

function writeGenerated(outputDir, relativePath, content) {
  const path = join(outputDir, relativePath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
  return {
    path,
    file_name: basename(path),
    relative_path: relativePath,
    bytes: Buffer.byteLength(content),
    corpus_source: "shared-generated",
  };
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function loadCanonicalManifest() {
  if (!existsSync(CANONICAL_MANIFEST_PATH)) {
    throw new Error(
      `Canonical document corpus manifest is missing at ${relative(REPO_ROOT, CANONICAL_MANIFEST_PATH)}. Run node tests/document_corpus/generate-canonical-corpus.mjs.`,
    );
  }
  const manifest = readJson(CANONICAL_MANIFEST_PATH);
  if (!Array.isArray(manifest.sources)) {
    throw new Error("Canonical document corpus manifest must contain a sources array");
  }
  return manifest;
}

export function canonicalCorpusSummary() {
  const manifest = loadCanonicalManifest();
  return {
    total_sources: manifest.sources.length,
    long_form_sources: manifest.sources.filter((entry) => (entry.bytes || 0) >= SHARED_DOCUMENT_CORPUS_MIN_BYTES).length,
    slices: manifest.slices || {},
    project: manifest.project,
  };
}

export function selectCanonicalCorpus({
  slice = "full-end-to-end",
  limit,
  minimumSources = 0,
  minBytes = SHARED_DOCUMENT_CORPUS_MIN_BYTES,
} = {}) {
  const manifest = loadCanonicalManifest();
  if (!CANONICAL_CORPUS_SLICES.includes(slice)) {
    throw new Error(`Unknown canonical corpus slice: ${slice}`);
  }
  let selected = manifest.sources.filter((entry) => {
    const slices = Array.isArray(entry.slices) ? entry.slices : [];
    return slices.includes(slice) && (entry.bytes || 0) >= minBytes;
  });
  selected.sort((a, b) => a.id.localeCompare(b.id));
  if (limit != null) selected = selected.slice(0, limit);
  if (selected.length < minimumSources) {
    throw new Error(
      `Canonical corpus slice ${slice} has ${selected.length} long-form sources, below required ${minimumSources}`,
    );
  }
  return selected;
}

export function materializeCanonicalCorpus({
  outputDir,
  slice = "full-end-to-end",
  limit,
  minimumSources = 0,
  minBytes = SHARED_DOCUMENT_CORPUS_MIN_BYTES,
  logger,
} = {}) {
  if (!outputDir) {
    throw new Error("outputDir is required to materialize the canonical document corpus");
  }
  const selected = selectCanonicalCorpus({ slice, limit, minimumSources, minBytes });
  const manifest = [];
  const used = new Set();
  for (const entry of selected) {
    const sourcePath = join(CANONICAL_CORPUS_DIR, entry.path || entry.relative_path);
    const relativePath = ensureUniqueRelativePath(entry.relative_path || entry.path, used);
    const destinationPath = join(outputDir, relativePath);
    mkdirSync(dirname(destinationPath), { recursive: true });
    copyFileSync(sourcePath, destinationPath);
    used.add(relativePath);
    manifest.push({
      ...entry,
      path: destinationPath,
      file_name: basename(destinationPath),
      relative_path: relativePath,
      corpus_source: "canonical",
      canonical_id: entry.id,
    });
  }
  logger?.action?.("canonical_corpus.materialized", {
    slice,
    canonical_count: manifest.length,
    minimum_sources: minimumSources,
    min_bytes: minBytes,
  });
  return {
    manifest,
    canonical_count: manifest.length,
    slice,
  };
}

function materializeCuratedAndGeneratedFallback({
  outputDir,
  existingManifest,
  minimumSources,
  minBytes,
}) {
  const manifest = [];
  const used = new Set(existingManifest.map((item) => item.relative_path).filter(Boolean));

  for (const fixtureDir of CURATED_FIXTURE_DIRS) {
    const absoluteDir = join(REPO_ROOT, fixtureDir);
    for (const sourcePath of listFiles(absoluteDir)) {
      const stats = statSync(sourcePath);
      if (stats.size < minBytes) continue;
      const sourceRelative = relative(absoluteDir, sourcePath);
      const relativePath = ensureUniqueRelativePath(
        join("shared-fixtures", fixtureDir.replace(/^tests\//, ""), sourceRelative),
        used,
      );
      const destinationPath = join(outputDir, relativePath);
      mkdirSync(dirname(destinationPath), { recursive: true });
      copyFileSync(sourcePath, destinationPath);
      used.add(relativePath);
      manifest.push({
        path: destinationPath,
        file_name: basename(destinationPath),
        relative_path: relativePath,
        bytes: stats.size,
        corpus_source: "shared-fixture",
        fixture_path: relative(REPO_ROOT, sourcePath),
      });
    }
  }

  let generatedIndex = 1;
  const existingLongSourceCount = existingManifest.filter((item) => (item.bytes || 0) >= minBytes).length;
  while (
    existingLongSourceCount + manifest.filter((item) => (item.bytes || 0) >= minBytes).length
    < minimumSources
  ) {
    const relativePath = ensureUniqueRelativePath(
      `shared-generated/shared-ux-source-${String(generatedIndex).padStart(3, "0")}.md`,
      used,
    );
    const item = writeGenerated(outputDir, relativePath, generatedLongSource(generatedIndex));
    used.add(relativePath);
    manifest.push(item);
    generatedIndex += 1;
  }

  return manifest;
}

export function materializeSharedDocumentCorpus({
  outputDir,
  existingManifest = [],
  minimumSources = SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
  minBytes = SHARED_DOCUMENT_CORPUS_MIN_BYTES,
  slice = "full-end-to-end",
  limit,
  canonicalOnly = false,
  logger,
} = {}) {
  if (!outputDir) {
    throw new Error("outputDir is required to materialize the shared document corpus");
  }

  const existingLongSourceCount = existingManifest.filter((item) => (item.bytes || 0) >= minBytes).length;
  const canonicalMinimum = Math.max(minimumSources - existingLongSourceCount, 0);
  const canonical = materializeCanonicalCorpus({
    outputDir,
    slice,
    limit,
    minimumSources: canonicalOnly ? canonicalMinimum : 0,
    minBytes,
    logger,
  });
  const manifest = [...canonical.manifest];

  if (!canonicalOnly) {
    const totalLong = existingLongSourceCount + manifest.filter((item) => (item.bytes || 0) >= minBytes).length;
    if (totalLong < minimumSources) {
      manifest.push(...materializeCuratedAndGeneratedFallback({
        outputDir,
        existingManifest: [...existingManifest, ...manifest],
        minimumSources,
        minBytes,
      }));
    }
  }

  const fixtureCount = manifest.filter((item) => item.corpus_source === "shared-fixture").length;
  const generatedCount = manifest.filter((item) => item.corpus_source === "shared-generated").length;
  const canonicalCount = manifest.filter((item) => item.corpus_source === "canonical").length;
  logger?.action?.("shared_corpus.materialized", {
    canonical_count: canonicalCount,
    fixture_count: fixtureCount,
    generated_count: generatedCount,
    total_added: manifest.length,
    minimum_sources: minimumSources,
    min_bytes: minBytes,
    slice,
  });
  return {
    manifest,
    canonical_count: canonicalCount,
    fixture_count: fixtureCount,
    generated_count: generatedCount,
    slice,
  };
}
