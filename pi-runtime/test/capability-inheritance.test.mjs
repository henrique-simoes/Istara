// Capability inheritance conformance harness (build-stream 2026-09-08
// pi-capability-inheritance, plan W4.3/W4.5).
//
// Two fixture classes, two different contracts:
//
// - fallback (test/fixtures/wire/pre-change/): endpoints whose
//   (pi_provider, model) pair the pi-ai registry does NOT know — governed
//   custom providers, unknown proxy gateways, legacy bindings. Their request
//   bodies must be BYTE-IDENTICAL to the pre-change captures (AC-1: the
//   resolver is strictly additive).
//
// - inherited (test/fixtures/wire/inherited/): registry-KNOWN pairs whose
//   bodies carry the corrected tier-4 semantics (AC-2 codex, AC-3 zai). The
//   committed fixture IS the contract: a pi version bump that changes one of
//   these bodies must be classified per the plan's §8 taxonomy before it
//   ships (intended-upstream | istara-fix | blocked) — never silently
//   regenerated.
//
// Every capture runs through the onPayload hook and terminates before any
// network I/O. No test in this file performs network I/O.

import test from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildRealProvider,
  getPiRegistry,
  resolveCapabilities,
} from "../src/provider.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURE_ROOT = join(here, "fixtures", "wire");

// Canonical body serialization: sorted keys, undefined-valued keys dropped —
// exactly what the real wire serializer (JSON.stringify) does, made stable for
// byte comparison. Must match scripts/capture-wire-fixtures.mjs.
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

// Synthetic none-alg JWT (test-only) — the codex adapter parses an account id
// out of the key before the payload hook fires.
const CODEX_TEST_JWT =
  "eyJhbGciOiJub25lIn0.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsiY2hhdGdwdF9hY2NvdW50X2lkIjoiZml4dHVyZS1hY2NvdW50In19.sig";

// Endpoint table mirroring scripts/capture-wire-fixtures.mjs. Keep the base
// URLs identical: detection on the URL is part of the pinned contract.
const ENDPOINTS = {
  // --- fallback class: registry misses, byte-identical to pre-change -------
  "dashscope-governed-custom__qwen3.7-plus": {
    fixture_class: "fallback",
    endpoint: {
      endpoint_id: "fixture-dashscope",
      provider_kind: "openai_compat",
      pi_provider: "dashscope",
      base_url: "https://dashscope.test/compatible-mode/v1",
      model: "qwen3.7-plus",
      api_key: "test-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high", "xhigh", "max"],
  },
  "unknown-proxy-gateway__some-model": {
    fixture_class: "fallback",
    endpoint: {
      endpoint_id: "fixture-proxy",
      provider_kind: "openai_compat",
      pi_provider: "custom-gateway",
      base_url: "https://gateway.test/v1",
      model: "some-model",
      api_key: "test-key",
      params: {},
    },
    levels: ["low"],
  },
  "legacy-deepseek-identity__deepseek-chat": {
    fixture_class: "fallback",
    endpoint: {
      endpoint_id: "fixture-deepseek",
      provider_kind: "openai_compat",
      pi_provider: "deepseek",
      base_url: "https://api.deepseek.com/v1",
      model: "deepseek-chat",
      api_key: "test-key",
      params: {},
    },
    levels: ["low", "high"],
  },
  "legacy-no-capability-binding__legacy-model": {
    fixture_class: "fallback",
    endpoint: {
      endpoint_id: "fixture-legacy",
      provider_kind: "openai_compat",
      pi_provider: "test-provider",
      base_url: "https://legacy.test/v1",
      model: "legacy-model",
      api_key: "test-key",
      params: {},
    },
    levels: ["low"],
  },
  // --- inherited class: registry hits, corrected tier-4 semantics ----------
  "zai-registry-inherited__glm-5.3": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-zai",
      provider_kind: "openai_compat",
      pi_provider: "zai",
      base_url: "https://api.z.ai/api/paas/v4",
      model: "glm-5.3",
      api_key: "test-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high", "max"],
  },
  "codex-registry-inherited__gpt-5.6-luna": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-codex",
      provider_kind: "openai_codex",
      pi_provider: "openai-codex",
      base_url: "https://chatgpt.com/backend-api",
      model: "gpt-5.6-luna",
      api_key: CODEX_TEST_JWT,
      params: {},
    },
    levels: ["off", "minimal", "low", "high", "xhigh", "max"],
  },
  "qwen-registry-inherited__qwen3.7-plus": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-qwen",
      provider_kind: "openai_compat",
      pi_provider: "qwen-token-plan",
      base_url: "https://qwen.test/compatible-mode/v1",
      model: "qwen3.7-plus",
      api_key: "test-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["off", "low", "high"],
  },
  "anthropic-registry-inherited__claude-opus-4-7": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-anthropic",
      provider_kind: "anthropic_compat",
      pi_provider: "anthropic",
      base_url: "https://anthropic.test/v1",
      model: "claude-opus-4-7",
      api_key: "test-key",
      supports_reasoning: true,
      params: {},
    },
    levels: ["low", "xhigh"],
  },
  // --- F-1: openai-responses transport (registry hits, corrected tier-4) ---
  "openai-registry-inherited__gpt-4o": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-openai-responses",
      provider_kind: "openai_responses",
      pi_provider: "openai",
      base_url: "https://api.openai.com/v1",
      model: "gpt-4o",
      api_key: "test-key",
      params: {},
    },
    levels: ["off", "low", "max"],
  },
  "xai-registry-inherited__grok-4.3": {
    fixture_class: "inherited",
    endpoint: {
      endpoint_id: "fixture-xai-responses",
      provider_kind: "openai_responses",
      pi_provider: "xai",
      base_url: "https://api.x.ai/v1",
      model: "grok-4.3",
      api_key: "test-key",
      params: {},
    },
    levels: ["low", "high"],
  },
};

async function captureBody(endpoint, level) {
  const binding = await buildRealProvider({
    ...endpoint,
    params: { ...(endpoint.params || {}), thinking_level: level },
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
  if (!payload) throw new Error(`no_payload_captured:${endpoint.endpoint_id}:${level}`);
  return payload;
}

test("registry accessor is memoised once per process (W2.1)", () => {
  const first = getPiRegistry();
  const second = getPiRegistry();
  assert.equal(first, second);
});

test("fallback-class bodies are byte-identical to the pre-change captures (AC-1)", async (t) => {
  const dir = join(FIXTURE_ROOT, "pre-change");
  const files = (await readdir(dir)).filter((name) => name.endsWith(".json") && name !== "manifest.json");
  assert.ok(files.length >= 9, `expected the full pre-change fixture set, found ${files.length}`);
  for (const file of files) {
    await t.test(file, async () => {
      const fixture = JSON.parse(await readFile(join(dir, file), "utf8"));
      const key = file.replace(/__[a-z0-9.\-]+\.json$/i, "");
      const spec = ENDPOINTS[key];
      assert.ok(spec, `no endpoint table entry for fixture ${file}`);
      const body = await captureBody(spec.endpoint, fixture.thinking_level);
      assert.equal(
        stableStringify(body),
        stableStringify(fixture.request_body),
        `fallback wire drift for ${file} — the resolver must be additive for registry misses (AC-1)`,
      );
    });
  }
});

test("inherited-class bodies match the corrected contracts (AC-2/AC-3)", async (t) => {
  const dir = join(FIXTURE_ROOT, "inherited");
  const files = (await readdir(dir)).filter((name) => name.endsWith(".json") && name !== "manifest.json");
  assert.ok(files.length >= 15, `expected the full inherited fixture set, found ${files.length}`);
  for (const file of files) {
    await t.test(file, async () => {
      const fixture = JSON.parse(await readFile(join(dir, file), "utf8"));
      const key = file.replace(/__[a-z0-9.\-]+\.json$/i, "");
      const spec = ENDPOINTS[key];
      assert.ok(spec, `no endpoint table entry for fixture ${file}`);
      const body = await captureBody(spec.endpoint, fixture.thinking_level);
      assert.equal(
        stableStringify(body),
        stableStringify(fixture.request_body),
        `inherited wire drift for ${file} — classify this diff per the §8 taxonomy before shipping`,
      );
    });
  }
});

test("codex xhigh reaches the wire unclamped and minimal maps to low (AC-2)", async () => {
  const spec = ENDPOINTS["codex-registry-inherited__gpt-5.6-luna"];
  const xhigh = await captureBody(spec.endpoint, "xhigh");
  assert.equal(xhigh.reasoning.effort, "xhigh");
  const minimal = await captureBody(spec.endpoint, "minimal");
  assert.equal(minimal.reasoning.effort, "low");
  const max = await captureBody(spec.endpoint, "max");
  assert.equal(max.reasoning.effort, "max");
});

test("zai registry hit transmits reasoning_effort per level (AC-3)", async () => {
  const spec = ENDPOINTS["zai-registry-inherited__glm-5.3"];
  for (const [level, effort] of [["low", "low"], ["high", "high"], ["max", "max"]]) {
    const body = await captureBody(spec.endpoint, level);
    assert.deepEqual(body.thinking, { type: "enabled", clear_thinking: false });
    assert.equal(body.reasoning_effort, effort, `zai ${level} must carry its reasoning_effort`);
  }
  // "off" omits the effort field entirely and disables the thinking block.
  const off = await captureBody(spec.endpoint, "off");
  assert.equal(off.reasoning_effort, undefined);
  assert.deepEqual(off.thinking, { type: "disabled" });
});

test("tier-2 operator veto: supports_reasoning:false silences every reasoning field (AC-4)", async () => {
  const spec = ENDPOINTS["zai-registry-inherited__glm-5.3"];
  const binding = await buildRealProvider({
    ...spec.endpoint,
    supports_reasoning: false,
    params: { thinking_level: "high" },
  });
  let payload;
  const stream = binding.stream(
    binding.model,
    { messages: [{ role: "user", content: [{ type: "text", text: "probe" }] }] },
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
  for await (const _event of stream) { /* terminated before network */ }
  binding.dispose();
  assert.equal(payload.thinking, undefined);
  assert.equal(payload.reasoning_effort, undefined);
  // The receipt names the tier-2 override that beat the tier-4 record.
  assert.equal(binding.capability_receipt.reasoning, false);
  assert.ok(binding.capability_receipt.applied_override_names.includes("supports_reasoning"));
  // The restricted model loses the level ladder entirely.
  assert.deepEqual(binding.capability_receipt.supported_pi_levels, ["off"]);
});

test("tri-state: absent supports_reasoning inherits the record (never collapses to false)", async () => {
  const spec = ENDPOINTS["zai-registry-inherited__glm-5.3"];
  const { capabilities, receipt } = await resolveCapabilities(
    { ...spec.endpoint, supports_reasoning: undefined },
    "openai-completions",
  );
  assert.equal(capabilities.reasoning, true);
  assert.equal(receipt.capability_source, "pi_builtin");
  assert.deepEqual(receipt.applied_override_names, []);
});

test("builtin/endpoint transport disagreement is a typed pre-network rejection (W2.6)", async () => {
  // claude-opus-4-7 is an anthropic-messages record; binding it through an
  // OpenAI-completions transport would send a body the record does not
  // describe. Must throw BEFORE any network I/O.
  await assert.rejects(
    () =>
      resolveCapabilities(
        { pi_provider: "anthropic", model: "claude-opus-4-7", base_url: "https://anthropic.test/v1" },
        "openai-completions",
      ),
    /^Error: provider_transport_mismatch:anthropic:claude-opus-4-7:registry_api=anthropic-messages:configured=openai-completions$/,
  );
});

test("F-1: openai-responses records bind through the openai_responses transport (regression)", async () => {
  // The reviewer's exact repro: _apply_catalog_fields("openai", "gpt-4o")
  // derives provider_kind=openai_responses, and the worker must bind it as
  // pi_builtin — pre-fix this threw provider_transport_mismatch because the
  // derived kind could never express the record's api.
  const { providerKindForRegistryApi } = await import("../src/provider.mjs");
  assert.equal(providerKindForRegistryApi("openai-responses"), "openai_responses");
  const spec = ENDPOINTS["openai-registry-inherited__gpt-4o"];
  const { capabilities, receipt } = await resolveCapabilities(spec.endpoint, "openai-responses");
  assert.equal(receipt.capability_source, "pi_builtin");
  assert.equal(capabilities.reasoning, false);
  const binding = await buildRealProvider({ ...spec.endpoint, params: { thinking_level: "low" } });
  try {
    assert.equal(binding.model.api, "openai-responses");
    assert.equal(binding.capability_receipt.capability_source, "pi_builtin");
  } finally {
    binding.dispose();
  }
  // The pre-change downgrade path (Responses-canonical record over the chat
  // transport) stays closed: it would silently send a body the record does
  // not describe. This rejection is intentional, not a recurrence.
  await assert.rejects(
    () =>
      resolveCapabilities(
        { pi_provider: "openai", model: "gpt-4o", base_url: "https://api.openai.com/v1" },
        "openai-completions",
      ),
    /^Error: provider_transport_mismatch:openai:gpt-4o:registry_api=openai-responses:configured=openai-completions$/,
  );
});

test("F-1: reasoning openai-responses models transmit effort per level (xai)", async () => {
  const spec = ENDPOINTS["xai-registry-inherited__grok-4.3"];
  for (const [level, effort] of [["low", "low"], ["high", "high"]]) {
    const body = await captureBody(spec.endpoint, level);
    assert.equal(body.reasoning.effort, effort, `xai ${level} must carry its reasoning effort`);
    assert.ok(Array.isArray(body.input), "Responses transport sends the input-array envelope");
  }
  // Third-party OpenAI-protocol host: the tier-5 developer-role URL default
  // fires exactly as on the pre-change chat path (role contract unchanged by
  // the transport upgrade); api.openai.com stays excluded (see openai fixture).
  const { receipt } = await (async () => {
    const { resolveCapabilities: resolve } = await import("../src/provider.mjs");
    const outcome = await resolve(spec.endpoint, "openai-responses");
    return { receipt: outcome.receipt };
  })();
  assert.ok(receipt.applied_override_names.includes("supportsDeveloperRole:url_default"));
});

test("F-1: native-transport records reject typed on the policy-derived kind", async () => {
  // bedrock/google/mistral/azure records have no Istara transport: the policy
  // derives openai_compat and the worker must reject LOUDLY pre-network —
  // never send a misshapen body to a native endpoint. Table mirrors
  // tests/pi_compat/test_transport_conformance.py CASES (non-bindable rows).
  const { providerKindForRegistryApi } = await import("../src/provider.mjs");
  const cases = [
    ["amazon-bedrock", "amazon.nova-lite-v1:0", "bedrock-converse-stream"],
    ["mistral", "codestral-latest", "mistral-conversations"],
    ["google", "gemini-2.5-flash", "google-generative-ai"],
  ];
  for (const [provider, model, registryApi] of cases) {
    const kind = providerKindForRegistryApi(registryApi);
    assert.equal(kind, "openai_compat");
    await assert.rejects(
      () =>
        resolveCapabilities({ pi_provider: provider, model, base_url: "https://native.test/v1" }, "openai-completions"),
      (error) =>
        String(error?.message) ===
        `provider_transport_mismatch:${provider}:${model}:registry_api=${registryApi}:configured=openai-completions`,
    );
  }
});

test("capability receipts are content-free: no URLs, keys, or fingerprints (AC-8 negative)", async () => {
  const spec = ENDPOINTS["zai-registry-inherited__glm-5.3"];
  const binding = await buildRealProvider({ ...spec.endpoint, params: { thinking_level: "low" } });
  const json = JSON.stringify(binding.capability_receipt);
  binding.dispose();
  for (const forbidden of [spec.endpoint.base_url, spec.endpoint.api_key, "api_key", "base_url", "authorization", "token"]) {
    assert.ok(!json.toLowerCase().includes(String(forbidden).toLowerCase()), `receipt leaks forbidden content: ${forbidden}`);
  }
  // Allowlisted keys only.
  assert.deepEqual(
    Object.keys(binding.capability_receipt).sort(),
    [
      "api",
      "applied_override_names",
      "capability_source",
      "fallback_reason",
      "model",
      "pi_ai_version",
      "pi_provider",
      "reasoning",
      "registry_generated_at",
      "supported_pi_levels",
    ],
  );
});
