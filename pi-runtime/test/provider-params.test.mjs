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

test("explicit non-reasoning catalog models do not inherit Qwen thinking", () => {
  assert.deepEqual(
    modelCapabilities(
      { pi_provider: "dashscope", supports_reasoning: false },
      "openai-completions",
    ),
    { reasoning: false, thinkingLevels: undefined, compat: undefined },
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

test("catalog vision capability reaches the embedded pi-ai model binding", () => {
  const binding = buildRealProvider({
    endpoint_id: "qwen-plus-vision",
    provider_kind: "openai_compat",
    pi_provider: "dashscope",
    base_url: "https://provider.test/v1",
    model: "qwen3.7-plus",
    api_key: "test-key",
    supports_vision: true,
    params: {},
  });
  try {
    assert.deepEqual(binding.model.input, ["text", "image"]);
  } finally {
    binding.dispose();
  }
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

test("Codex identity capture forces the observable SSE transport", async () => {
  const previousWebSocket = globalThis.WebSocket;
  let websocketAttempts = 0;
  let fetchCalls = 0;
  globalThis.WebSocket = class {
    constructor() {
      websocketAttempts += 1;
      throw new Error("websocket_should_not_be_used_for_identity_receipts");
    }
  };
  const binding = buildRealProvider({
    endpoint_id: "codex-luna",
    provider_kind: "openai_codex",
    pi_provider: "openai-codex",
    base_url: "https://provider.test/backend-api",
    model: "gpt-5.6-luna",
    api_key: "eyJhbGciOiJub25lIn0.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsiY2hhdGdwdF9hY2NvdW50X2lkIjoidGVzdC1hY2NvdW50In19.sig",
    params: { thinking_level: "high", max_tokens: 32 },
  });
  try {
    const stream = binding.stream(
      binding.model,
      { messages: [{ role: "user", content: [{ type: "text", text: "probe" }] }] },
      {
        fetch: async () => {
          fetchCalls += 1;
          return new Response("{}", { status: 401, statusText: "Unauthorized" });
        },
      },
    );
    for await (const _event of stream) { /* terminal error is expected */ }
  } finally {
    binding.dispose();
    if (previousWebSocket === undefined) delete globalThis.WebSocket;
    else globalThis.WebSocket = previousWebSocket;
  }
  assert.equal(websocketAttempts, 0);
  assert.equal(fetchCalls, 1);
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
