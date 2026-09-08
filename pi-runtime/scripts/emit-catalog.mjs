// Pi-ai catalog emitter — the maintenance-time authority projection (tier 4).
//
// Build-stream: docs/build-stream/2026-09-08-pi-capability-inheritance.md
// (winning consensus plan §5.1, wave W1).
//
// pi-ai's generated registry is the SOLE authority for provider/model
// capability semantics. This script is the ONLY place outside the worker that
// imports the registry (`@earendil-works/pi-ai/providers/all`), and it emits a
// deterministic, provenance-stamped projection that the Istara backend reads
// so the backend never needs the pi-ai dependency at runtime.
//
// Per model, `thinkingLevels` is produced by calling pi-ai's own
// `getSupportedThinkingLevels(record)` — the filter is NEVER reimplemented
// here (plan DEC-M2: its asymmetric absent-means-supported / opt-in-xhigh-max
// rule is load-bearing and a hand-rolled copy is an architecture_drift
// finding). `thinkingLevelMap` and `compat` are emitted verbatim.
//
// Governed custom providers (e.g. dashscope) are merged from
// <data-dir>/custom_providers/*.json — hand-owned Istara identity data (tier 5)
// that regeneration must never delete or overwrite. The merge rejects
// provider/model collisions, unknown schema fields, and non-canonical ordering.
//
// Usage:
//   node emit-catalog.mjs --out <path> [--data-dir <dir>] [--emitted-at <iso>]
//
// The output is deterministic for a given pi-ai pin except `emitted_at`,
// which `scripts/generate_pi_catalog.py --check` masks when comparing.

import { createHash } from "node:crypto";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  getBuiltinModel,
  getBuiltinModelDataGeneratedAt,
  getBuiltinModels,
  getBuiltinProviders,
} from "@earendil-works/pi-ai/providers/all";
import { getSupportedThinkingLevels } from "@earendil-works/pi-ai";

const here = dirname(fileURLToPath(import.meta.url));

// Canonical emitted model field order. The union of these keys feeds
// `model_field_set_hash` so a NEW upstream field becomes visible at bump time
// instead of being silently inherited (plan §5.1 / R9).
const MODEL_FIELD_ORDER = [
  "id",
  "name",
  "api",
  "baseUrl",
  "contextWindow",
  "maxTokens",
  "reasoning",
  "input",
  "thinkingLevels",
  "cost",
  "thinkingLevelMap",
  "compat",
];
const KNOWN_MODEL_FIELDS = new Set(MODEL_FIELD_ORDER);

function sha256(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

async function resolvePiAiVersion() {
  // The worker receipt and the projection provenance both name the installed
  // pi-ai version. Resolve it from the installed package rather than from
  // package.json so what is written is what is actually running.
  const candidates = [
    join(here, "..", "node_modules", "@earendil-works", "pi-ai", "package.json"),
    join(here, "..", "..", "node_modules", "@earendil-works", "pi-ai", "package.json"),
  ];
  for (const candidate of candidates) {
    try {
      const pkg = JSON.parse(await readFile(candidate, "utf8"));
      if (pkg?.version) return String(pkg.version);
    } catch {
      // try next candidate
    }
  }
  throw new Error("not_runnable:pi_ai_package_json_not_found");
}

function canonicalModel(record) {
  const emitted = {};
  for (const field of MODEL_FIELD_ORDER) {
    if (field === "thinkingLevels") {
      // pi-ai computes the supported level menu (DEC-M2). Never reimplemented.
      emitted[field] = getSupportedThinkingLevels(record);
      continue;
    }
    if (field === "thinkingLevelMap" || field === "compat") {
      emitted[field] = record[field] ?? null;
      continue;
    }
    if (record[field] === undefined) {
      emitted[field] = field === "baseUrl" ? "" : field === "input" ? ["text"] : null;
      continue;
    }
    emitted[field] = record[field];
  }
  return emitted;
}

async function loadGovernedOverlays(dataDir) {
  // Hand-owned custom-provider overlays (tier 5). Structure per file:
  // { "__overlay_provenance": { ..., "wire_fixtures": [...] }, "<provider_id>": [models...] }
  const overlayDir = join(dataDir, "custom_providers");
  const overlays = [];
  let entries = [];
  try {
    entries = await readdir(overlayDir);
  } catch {
    return overlays; // no overlays yet — registry-only projection
  }
  for (const entry of entries.filter((name) => name.endsWith(".json")).sort()) {
    const parsed = JSON.parse(await readFile(join(overlayDir, entry), "utf8"));
    const provenance = parsed.__overlay_provenance;
    if (!provenance || !Array.isArray(provenance.wire_fixtures) || provenance.wire_fixtures.length === 0) {
      throw new Error(`overlay_schema_invalid:${entry}:missing_wire_fixtures`);
    }
    const providers = Object.keys(parsed).filter((key) => !key.startsWith("__")).sort();
    if (providers.length === 0) {
      throw new Error(`overlay_schema_invalid:${entry}:no_providers`);
    }
    for (const providerId of providers) {
      const models = parsed[providerId];
      if (!Array.isArray(models) || models.length === 0) {
        throw new Error(`overlay_schema_invalid:${entry}:${providerId}:models_must_be_non_empty_array`);
      }
      let previousId = null;
      const seen = new Set();
      for (const model of models) {
        const unknown = Object.keys(model).filter((key) => !KNOWN_MODEL_FIELDS.has(key));
        if (unknown.length > 0) {
          throw new Error(`overlay_schema_invalid:${entry}:${providerId}:${model.id}:unknown_fields:${unknown.sort().join(",")}`);
        }
        if (typeof model.id !== "string" || !model.id) {
          throw new Error(`overlay_schema_invalid:${entry}:${providerId}:model_id_required`);
        }
        if (seen.has(model.id)) {
          throw new Error(`overlay_collision:${entry}:${providerId}:${model.id}:duplicate_model`);
        }
        seen.add(model.id);
        if (previousId !== null && model.id < previousId) {
          throw new Error(`overlay_order_invalid:${entry}:${providerId}:${model.id}:models_must_be_sorted_by_id`);
        }
        previousId = model.id;
      }
      overlays.push({ file: entry, providerId, models, provenance });
    }
  }
  return overlays;
}

export async function emitCatalog({ outPath, dataDir, emittedAt } = {}) {
  const dataDirResolved = resolve(dataDir || join(here, "..", "..", "backend", "app", "core", "pi_runtime", "data"));
  const registryProviders = getBuiltinProviders();
  if (!Array.isArray(registryProviders) || registryProviders.length === 0) {
    throw new Error("not_runnable:empty_registry");
  }

  const overlays = await loadGovernedOverlays(dataDirResolved);
  const overlayProviderIds = new Set(overlays.map((overlay) => overlay.providerId));
  for (const overlay of overlays) {
    if (registryProviders.includes(overlay.providerId)) {
      throw new Error(`overlay_collision:${overlay.file}:${overlay.providerId}:provider_exists_in_registry`);
    }
  }

  const catalog = {};
  const governed = [];
  for (const providerId of [...registryProviders].sort()) {
    // Enumerate through pi-ai's own public accessors so the projection reads
    // the registry exactly as the worker resolver does — one authority, one
    // access path (plan DEC-M1).
    const records = getBuiltinModels(providerId);
    if (!Array.isArray(records) || records.length === 0) {
      throw new Error(`not_runnable:registry_walk_failed:${providerId}:no_models`);
    }
    const modelIds = records.map((record) => record.id).sort();
    const models = [];
    for (const modelId of modelIds) {
      const record = getBuiltinModel(providerId, modelId);
      if (!record) throw new Error(`registry_miss:${providerId}:${modelId}`);
      models.push(canonicalModel(record));
    }
    catalog[providerId] = models;
  }
  for (const overlay of overlays) {
    // Governed custom records are hand-owned verbatim (tier 5). They are
    // merged exactly as authored — never normalized, never regenerated — so a
    // future bump cannot silently rewrite or delete Istara's identity data.
    catalog[overlay.providerId] = overlay.models.map((model) => ({ ...model }));
    governed.push(overlay.providerId);
  }

  const fieldSet = new Set();
  for (const models of Object.values(catalog)) {
    for (const model of models) for (const key of Object.keys(model)) fieldSet.add(key);
  }

  const provenance = {
    generator: "pi-runtime/scripts/emit-catalog.mjs",
    pi_ai_version: await resolvePiAiVersion(),
    pi_ai_generated_at: getBuiltinModelDataGeneratedAt() ?? null,
    emitted_at: emittedAt || new Date().toISOString(),
    emitter_sha256: sha256(await readFile(join(here, "emit-catalog.mjs"), "utf8")),
    model_field_set_hash: sha256([...fieldSet].sort().join("\n")),
    governed_custom_providers: governed.sort(),
  };

  const output = { __provenance: provenance, ...catalog };
  const text = `${JSON.stringify(output, null, 2)}\n`;
  if (outPath) {
    await mkdir(dirname(resolve(outPath)), { recursive: true });
    await writeFile(outPath, text);
  }
  return { text, provenance, providerCount: Object.keys(catalog).length, modelCount: Object.values(catalog).reduce((sum, models) => sum + models.length, 0) };
}

// CLI entry: `node emit-catalog.mjs --out <path> [--data-dir <dir>] [--emitted-at <iso>]`
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isMain) {
  const args = process.argv.slice(2);
  const readArg = (name) => {
    const index = args.indexOf(name);
    return index === -1 ? undefined : args[index + 1];
  };
  const out = readArg("--out");
  if (!out) {
    console.error("usage: node emit-catalog.mjs --out <path> [--data-dir <dir>] [--emitted-at <iso>]");
    process.exit(2);
  }
  try {
    const result = await emitCatalog({ outPath: out, dataDir: readArg("--data-dir"), emittedAt: readArg("--emitted-at") });
    console.log(`emitted ${result.modelCount} models across ${result.providerCount} providers -> ${out}`);
    console.log(`pi_ai_version=${result.provenance.pi_ai_version} generated_at=${result.provenance.pi_ai_generated_at}`);
    console.log(`governed_custom_providers=${result.provenance.governed_custom_providers.join(",") || "(none)"}`);
  } catch (error) {
    console.error(`emit_failed:${error?.message || error}`);
    process.exit(1);
  }
}
