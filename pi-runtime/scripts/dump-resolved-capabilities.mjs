// Authority-equivalence dump (plan W4.1 / DEC-M1).
//
// Walks the ENTIRE live pi-ai registry through the worker's own capability
// resolver (src/provider.mjs resolveCapabilities) and prints a JSON document
// on stdout for the Python conformance tests to compare against the generated
// catalog projection:
//
//   node scripts/dump-resolved-capabilities.mjs --mode inventory
//     -> { "inventory": { "<provider>": ["<model-id>", ...], ... } }
//
//   node scripts/dump-resolved-capabilities.mjs --mode resolved
//     -> { "resolved": [{ pi_provider, model, reasoning, supported_pi_levels,
//                         thinking_level_map, compat, url_default_supports_developer_role,
//                         capability_source, applied_override_names }, ...] }
//
// Two read paths, one derivation, machine-checked: the projection (catalog
// consumers) and this resolver (worker binding) must agree for every model.

import { getBuiltinModel, getBuiltinModels, getBuiltinProviders } from "@earendil-works/pi-ai/providers/all";
import { resolveCapabilities } from "../src/provider.mjs";

const mode = (() => {
  const index = process.argv.indexOf("--mode");
  return index === -1 ? "resolved" : process.argv[index + 1];
})();
if (mode !== "inventory" && mode !== "resolved") {
  console.error("usage: node dump-resolved-capabilities.mjs --mode inventory|resolved");
  process.exit(2);
}

const providers = getBuiltinProviders();
if (!Array.isArray(providers) || providers.length === 0) {
  console.error("not_runnable:empty_registry");
  process.exit(3);
}

if (mode === "inventory") {
  const inventory = {};
  for (const provider of providers.sort()) {
    inventory[provider] = getBuiltinModels(provider).map((record) => record.id).sort();
  }
  process.stdout.write(JSON.stringify({ inventory }));
  process.exit(0);
}

const resolved = [];
for (const provider of providers.sort()) {
  for (const record of getBuiltinModels(provider)) {
    const endpoint = {
      pi_provider: provider,
      model: record.id,
      // The record's own baseUrl: detection stays inside pi-ai, and the
      // tier-5 developer-role URL default applies exactly as it would for a
      // real endpoint on that host. The dump reports whether the default
      // fired so the Python side can compare the record-derived fields
      // precisely.
      base_url: record.baseUrl || "",
      supports_reasoning: null,
      supports_vision: null,
    };
    let outcome;
    try {
      outcome = await resolveCapabilities(endpoint, record.api);
    } catch (error) {
      console.error(`resolve_failed:${provider}:${record.id}:${error?.message || error}`);
      process.exit(1);
    }
    resolved.push({
      pi_provider: provider,
      model: record.id,
      reasoning: outcome.capabilities.reasoning,
      supported_pi_levels: outcome.capabilities.supportedPiLevels,
      thinking_level_map: outcome.capabilities.thinkingLevelMap ?? null,
      compat: outcome.capabilities.compat ?? null,
      url_default_supports_developer_role: outcome.receipt.applied_override_names.includes(
        "supportsDeveloperRole:url_default",
      ),
      capability_source: outcome.receipt.capability_source,
      applied_override_names: outcome.receipt.applied_override_names,
    });
  }
}
process.stdout.write(JSON.stringify({ resolved }));
