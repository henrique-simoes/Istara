import { existsSync, readFileSync, readdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Slices offered by the Harbor Ledger rich corpus (see rich/manifest.json). */
export const RICH_CORPUS_SLICES = [
  "interview-heavy",
  "survey-heavy",
  "usability-heavy",
  "full-end-to-end",
  "coding-reliability",
  "context-pack",
  "chat-packs",
];

function richRoot() {
  return join(__dirname, "rich");
}

export function loadRichManifest() {
  const raw = readFileSync(join(richRoot(), "manifest.json"), "utf8");
  return JSON.parse(raw);
}

/**
 * Select rich-corpus source files for a slice (mirrors selectCanonicalCorpus).
 * Returns absolute paths. Throws when minimumSources is not met.
 */
export function selectRichCorpus({ slice = "full-end-to-end", limit = null, minimumSources = 1 } = {}) {
  if (!RICH_CORPUS_SLICES.includes(slice)) {
    throw new Error(`Unknown rich corpus slice: ${slice}`);
  }
  const manifest = loadRichManifest();
  const ids = manifest.slices[slice] || [];
  const byId = new Map(manifest.files.map((f) => [f.id, f]));
  let selected = ids.map((id) => byId.get(id)).filter(Boolean);
  if (limit != null) selected = selected.slice(0, limit);
  if (selected.length < minimumSources) {
    throw new Error(
      `Rich corpus slice ${slice} has ${selected.length} sources, below required ${minimumSources}`,
    );
  }
  return selected.map((f) => ({ ...f, absolutePath: join(richRoot(), f.path) }));
}

export function richGroundTruth() {
  return loadRichManifest().ground_truth;
}
