import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "fs";
import { basename, dirname, join, relative, resolve } from "path";
import { fileURLToPath } from "url";

export const SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES = 120;
export const SHARED_DOCUMENT_CORPUS_MIN_BYTES = 1000;

const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(MODULE_DIR, "../..");
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
      `Counter-signal: analytics suggest some users skip details when reminders arrive late, so the synthesis must not overfit to interview enthusiasm.`,
      `Research implication: findings should cite concrete files and distinguish approved tasks from material still waiting for human review.`,
      "",
    ].join("\n"));
  }
  return [
    `# Shared UX Research Source ${String(index).padStart(3, "0")}`,
    "",
    "This synthetic long-form source belongs to Istara's shared document corpus for tests that need realistic research material.",
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

export function materializeSharedDocumentCorpus({
  outputDir,
  existingManifest = [],
  minimumSources = SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
  minBytes = SHARED_DOCUMENT_CORPUS_MIN_BYTES,
  logger,
} = {}) {
  if (!outputDir) {
    throw new Error("outputDir is required to materialize the shared document corpus");
  }
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

  logger?.action?.("shared_corpus.materialized", {
    fixture_count: manifest.filter((item) => item.corpus_source === "shared-fixture").length,
    generated_count: manifest.filter((item) => item.corpus_source === "shared-generated").length,
    total_added: manifest.length,
    minimum_sources: minimumSources,
    min_bytes: minBytes,
  });
  return {
    manifest,
    fixture_count: manifest.filter((item) => item.corpus_source === "shared-fixture").length,
    generated_count: manifest.filter((item) => item.corpus_source === "shared-generated").length,
  };
}
