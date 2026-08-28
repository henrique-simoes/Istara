import test from "node:test";
import assert from "node:assert/strict";

import {
  buildRealProvider,
  captureProviderFetch,
  filterParamsForApi,
  modelCapabilities,
  modelLimits,
} from "../src/provider.mjs";

test("codex responses strips temperature, keeps retries and reasoning", () => {
  const params = { temperature: 0.7, maxRetries: 2, reasoning: "minimal", maxTokens: 512 };
  const wire = filterParamsForApi(params, "openai-codex-responses");
  assert.equal(wire.temperature, undefined);
  assert.equal(wire.maxRetries, 2);
  assert.equal(wire.reasoning, "minimal");
  assert.equal(wire.maxTokens, 512);
});

test("other apis keep every mapped param", () => {
  const params = { temperature: 0.4, maxTokens: 128 };
  const wire = filterParamsForApi(params, "openai-chat-completions");
  assert.deepEqual(wire, params);
});

test("null/undefined params yield an empty wire set without throwing", () => {
  assert.deepEqual(filterParamsForApi(null, "openai-codex-responses"), {});
});

test("provider model limits use resolved endpoint capabilities instead of a 4096 cap", () => {
  assert.deepEqual(
    modelLimits({ context_window: 128000, max_tokens: 16384 }, { maxTokens: 12000 }),
    { contextWindow: 128000, maxTokens: 16384 },
  );
  assert.deepEqual(
    modelLimits({ context_window: 0, max_tokens: 0 }, { maxTokens: 12000 }),
    { contextWindow: 128000, maxTokens: 12000 },
  );
});

test("deepseek identity enables explicit thinking controls for forced structured tools", () => {
  assert.deepEqual(
    modelCapabilities({ pi_provider: "deepseek" }, "openai-completions"),
    {
      reasoning: true,
      thinkingLevels: undefined,
      compat: { thinkingFormat: "deepseek" },
    },
  );
});

test("qwen identities emit the Qwen thinking compatibility contract", () => {
  assert.deepEqual(
    modelCapabilities({ pi_provider: "qwen-token-plan" }, "openai-completions"),
    {
      reasoning: true,
      thinkingLevels: undefined,
      compat: { thinkingFormat: "qwen", supportsReasoningEffort: false },
    },
  );
});

test("Qwen thinking level becomes enable_thinking without reasoning_effort", async () => {
  const binding = buildRealProvider({
    endpoint_id: "qwen-plus",
    provider_kind: "openai_compat",
    pi_provider: "qwen-token-plan",
    base_url: "https://provider.test/v1",
    model: "qwen3.7-plus",
    api_key: "test-key",
    params: { thinking_level: "high", max_tokens: 64 },
  });
  let payload;
  const stream = binding.stream(
    binding.model,
    { messages: [{ role: "user", content: [{ type: "text", text: "probe" }] }] },
    {
      fetch: async () => { throw new Error("network_should_not_be_called"); },
      onPayload: (candidate) => {
        payload = candidate;
        throw new Error("payload_captured");
      },
    },
  );
  for await (const _event of stream) { /* the payload hook terminates before network */ }
  binding.dispose();
  assert.equal(payload.enable_thinking, true);
  assert.equal(payload.reasoning_effort, undefined);
  assert.equal(payload.model, "qwen3.7-plus");
});

test("codex identity retains its responses reasoning contract", () => {
  assert.deepEqual(
    modelCapabilities({ pi_provider: "openai-codex" }, "openai-codex-responses"),
    {
      reasoning: true,
      thinkingLevels: ["xhigh", "max", "minimal"],
      compat: undefined,
    },
  );
});

test("provider identity observer captures a split non-SSE JSON response", async () => {
  const observed = [];
  const payload = JSON.stringify({ response: { model: "served-json-model" } });
  const encoded = new TextEncoder().encode(payload);
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(encoded.slice(0, 11));
      controller.enqueue(encoded.slice(11));
      controller.close();
    },
  });
  const wrapped = captureProviderFetch(
    async () => new Response(body, { headers: { "content-type": "application/json" } }),
    { add: (model) => { if (model) observed.push(model); } },
  );
  const response = await wrapped("http://provider.test/v1/chat/completions");
  assert.equal(await response.text(), payload);
  assert.deepEqual(observed, ["served-json-model"]);
});
