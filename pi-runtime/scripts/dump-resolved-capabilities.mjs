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
import { apiForKind, providerKindForRegistryApi, resolveCapabilities } from "../src/provider.mjs";

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
// Registry records whose api has no Istara transport (bedrock/google/mistral
// natives, azure): the endpoint policy still derives a kind for them, and the
// worker rejects the bind loudly. The dump records those rejections instead of
// crashing so the conformance sweep covers the REAL bind path for every model
// (FIX F-1: feeding record.api back in as the transport made the mismatch
// branch structurally unreachable and hid 346 unbindable models).
const unbindable = [];
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
    // Derive the CONFIGURED transport exactly as the backend endpoint policy
    // does (providerKindForRegistryApi mirrors endpoint_policy.py), never the
    // record's own api — that is the production bind path under test.
    const derivedKind = providerKindForRegistryApi(record.api);
    const { modelApi: configuredTransport } = apiForKind(derivedKind);
    let outcome;
    try {
      outcome = await resolveCapabilities(endpoint, configuredTransport);
    } catch (error) {
      const message = String(error?.message || error);
      if (message.startsWith("provider_transport_mismatch:")) {
        unbindable.push({
          pi_provider: provider,
          model: record.id,
          registry_api: record.api,
          derived_provider_kind: derivedKind,
          configured_model_api: configuredTransport,
          rejection: message,
        });
        continue;
      }
      console.error(`resolve_failed:${provider}:${record.id}:${message}`);
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
      // The policy-derived bind path, pinned per model so the sweep can never
      // silently drift off the production derivation again (F-1).
      derived_provider_kind: derivedKind,
      configured_model_api: configuredTransport,
    });
  }
}
process.stdout.write(JSON.stringify({ resolved, unbindable }));
