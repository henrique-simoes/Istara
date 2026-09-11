// Capture wire fixtures for the pi compatibility authority wave
// (build-stream 2026-09-08-pi-capability-inheritance, plan W0.3/W4.4).
//
//   node scripts/capture-wire-fixtures.mjs            # fallback class -> test/fixtures/wire/pre-change/
//   node scripts/capture-wire-fixtures.mjs --class inherited  # -> test/fixtures/wire/inherited/
//
// It binds the real provider builder with synthetic endpoints (no network —
// the onPayload hook terminates before fetch), captures the exact request body
// pi-ai would send, and writes one JSON fixture per (endpoint, level). Fixtures
// contain no secrets and no private URLs; base URLs are synthetic .test hosts
// (or public provider hosts where pi-ai's URL detection is part of the
// contract).
//
// - fallback class: captured BEFORE the capability resolver lands; the
//   capability-inheritance test must reproduce them BYTE-IDENTICALLY (AC-1
//   additivity proof). Do not regenerate this class after W2.
// - inherited class: the CORRECTED payloads after the resolver landed — the
//   committed file is the contract; a pi version bump that changes these
//   bodies must be classified per the plan's §8 taxonomy (AC-11).

import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildRealProvider } from "../src/provider.mjs";

const fixtureClass = (() => {
  const index = process.argv.indexOf("--class");
  return index === -1 ? "fallback" : process.argv[index + 1];
})();
if (fixtureClass !== "fallback" && fixtureClass !== "inherited") {
  console.error("usage: node capture-wire-fixtures.mjs [--class fallback|inherited]");
  process.exit(2);
}
const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, "..", "test", "fixtures", "wire", fixtureClass === "fallback" ? "pre-change" : "inherited");

// Stable key order so the JSON files are diffable and byte-comparable.
// undefined-valued keys are skipped, exactly as JSON.stringify (the real wire
// serializer) drops them.
function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    const keys = Object.keys(value)
      .filter((k) => value[k] !== undefined)
      .sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

// Fallback-class endpoints: every (pi_provider, model) pair here must stay on
// the legacy path after the resolver lands (registry miss), so their bodies
// must be byte-identical pre/post change (AC-1).
const FALLBACK_ENDPOINTS = [
  {
    name: "dashscope-governed-custom",
    endpoint: {
      endpoint_id: "fixture-dashscope",
      provider_kind: "openai_compat",
      pi_provider: "dashscope",
      base_url: "https://dashscope.test/compatible-mode/v1",
      model: "qwen3.7-plus",
      api_key: "fixture-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high", "xhigh", "max"],
  },
  {
    name: "unknown-proxy-gateway",
    endpoint: {
      endpoint_id: "fixture-proxy",
      provider_kind: "openai_compat",
      pi_provider: "custom-gateway",
      base_url: "https://gateway.test/v1",
      model: "some-model",
      api_key: "fixture-key",
      params: {},
    },
    levels: ["low"],
  },
  {
    name: "legacy-deepseek-identity",
    endpoint: {
      endpoint_id: "fixture-deepseek",
      provider_kind: "openai_compat",
      pi_provider: "deepseek",
      // Public DeepSeek host so pi-ai's URL detection matches production
      // (supportsReasoningEffort:false, max_tokens field, thinking block).
      base_url: "https://api.deepseek.com/v1",
      model: "deepseek-chat",
      api_key: "fixture-key",
      params: {},
    },
    levels: ["low", "high"],
  },
  {
    name: "legacy-no-capability-binding",
    endpoint: {
      endpoint_id: "fixture-legacy",
      provider_kind: "openai_compat",
      pi_provider: "test-provider",
      base_url: "https://legacy.test/v1",
      model: "legacy-model",
      api_key: "fixture-key",
      params: {},
    },
    levels: ["low"],
  },
];

// Inherited-class endpoints: registry-KNOWN (pi_provider, model) pairs whose
// bodies carry the corrected tier-4 semantics (AC-2 codex, AC-3 zai, qwen
// record contract, anthropic messages contract).
const INHERITED_ENDPOINTS = [
  {
    name: "zai-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-zai",
      provider_kind: "openai_compat",
      pi_provider: "zai",
      base_url: "https://api.z.ai/api/paas/v4",
      model: "glm-5.3",
      api_key: "fixture-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high", "max"],
  },
  {
    name: "codex-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-codex",
      provider_kind: "openai_codex",
      pi_provider: "openai-codex",
      base_url: "https://chatgpt.com/backend-api",
      model: "gpt-5.6-luna",
      // Codex auth is a JWT account token; the adapter parses the account id
      // before the payload hook fires. Synthetic none-alg JWT (test-only).
      api_key: "eyJhbGciOiJub25lIn0.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsiY2hhdGdwdF9hY2NvdW50X2lkIjoiZml4dHVyZS1hY2NvdW50In19.sig",
      params: {},
    },
    levels: ["off", "minimal", "low", "high", "xhigh", "max"],
  },
  {
    name: "qwen-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-qwen",
      provider_kind: "openai_compat",
      pi_provider: "qwen-token-plan",
      base_url: "https://qwen.test/compatible-mode/v1",
      model: "qwen3.7-plus",
      api_key: "fixture-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high"],
  },
  {
    name: "anthropic-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-anthropic",
      provider_kind: "anthropic_compat",
      pi_provider: "anthropic",
      base_url: "https://anthropic.test/v1",
      model: "claude-opus-4-7",
      api_key: "fixture-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["low", "xhigh"],
  },
  {
    name: "openai-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-openai-responses",
      provider_kind: "openai_responses",
      pi_provider: "openai",
      // Public OpenAI host so pi-ai's URL detection matches production:
      // api.openai.com is EXCLUDED from the tier-5 developer-role URL default
      // (the record's own compat governs the role contract).
      base_url: "https://api.openai.com/v1",
      model: "gpt-4o",
      api_key: "fixture-key",
      params: {},
    },
    levels: ["off", "low", "max"],
  },
  {
    name: "xai-registry-inherited",
    endpoint: {
      endpoint_id: "fixture-xai-responses",
      provider_kind: "openai_responses",
      pi_provider: "xai",
      // Third-party OpenAI-protocol host: the tier-5 developer-role URL
      // default fires here exactly as on the pre-change chat path.
      base_url: "https://api.x.ai/v1",
      model: "grok-4.3",
      api_key: "fixture-key",
      params: {},
    },
    levels: ["low", "high"],
  },
];

const ENDPOINTS = fixtureClass === "fallback" ? FALLBACK_ENDPOINTS : INHERITED_ENDPOINTS;

async function captureBody(endpoint, level) {
  const binding = await buildRealProvider({
    ...endpoint.endpoint,
    params: { ...(endpoint.endpoint.params || {}), thinking_level: level },
  });
  let payload = null;
  try {
    const stream = binding.stream(
      binding.model,
      { messages: [{ role: "user", content: [{ type: "text", text: "fixture" }] }] },
      {
        fetch: async () => {
          throw new Error("network_should_not_be_called");
        },
        onPayload: (candidate) => {
          payload = candidate;
          throw new Error("payload_captured");
        },
      },
    );
    for await (const _event of stream) {
      // The payload hook terminates before any network I/O.
    }
  } finally {
    binding.dispose();
  }
  if (!payload) throw new Error(`no_payload_captured:${endpoint.name}:${level}`);
  return JSON.parse(stableStringify(payload));
}

await mkdir(outDir, { recursive: true });
const manifest = [];
for (const entry of ENDPOINTS) {
  for (const level of entry.levels) {
    const body = await captureBody(entry, level);
    const file = `${entry.name}__${entry.endpoint.model}__${level}.json`;
    const record = {
      fixture_class: fixtureClass,
      captured_at: new Date().toISOString(),
      endpoint: {
        provider_kind: entry.endpoint.provider_kind,
        pi_provider: entry.endpoint.pi_provider,
        model: entry.endpoint.model,
        supports_reasoning: entry.endpoint.supports_reasoning ?? null,
        supports_vision: entry.endpoint.supports_vision ?? null,
        base_url_host: new URL(entry.endpoint.base_url).host,
      },
      thinking_level: level,
      request_body: body,
    };
    await writeFile(join(outDir, file), `${JSON.stringify(record, null, 2)}\n`);
    manifest.push({ file, pi_provider: entry.endpoint.pi_provider, model: entry.endpoint.model, level });
    console.log(`captured ${file}`);
  }
}
await writeFile(join(outDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`done: ${manifest.length} fixtures in ${outDir}`);
