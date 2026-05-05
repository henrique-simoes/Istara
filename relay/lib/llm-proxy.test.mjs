import assert from "node:assert/strict";
import test from "node:test";

import { LLMProxy, inferProviderType } from "./llm-proxy.mjs";

test("infers LM Studio for the default local OpenAI-compatible port", () => {
  assert.equal(inferProviderType("ollama", "http://10.0.10.142:1234"), "lmstudio");
  assert.equal(inferProviderType("", "http://localhost:1234"), "lmstudio");
});

test("infers OpenAI-compatible base paths without duplicating /v1", () => {
  assert.equal(inferProviderType("ollama", "https://example.test/v1"), "openai_compat");
  const proxy = new LLMProxy("openai_compat", "https://example.test/v1", "");

  assert.equal(
    proxy._openAIUrl("chat/completions"),
    "https://example.test/v1/chat/completions",
  );
});

test("keeps Gemini OpenAI-compatible base URL intact", () => {
  const proxy = new LLMProxy(
    "ollama",
    "https://generativelanguage.googleapis.com/v1beta/openai",
    "",
  );

  assert.equal(proxy.providerType, "gemini_openai");
  assert.equal(
    proxy._openAIUrl("chat/completions"),
    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
  );
});

test("uses LM Studio /v1/models when a 1234 host was mislabeled as Ollama", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return new Response(JSON.stringify({ data: [{ id: "qwen3.6-35b-a3b@q5_k_xl" }] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const proxy = new LLMProxy("ollama", "http://10.0.10.142:1234", "");
    const models = await proxy.listModels();

    assert.equal(proxy.providerType, "lmstudio");
    assert.deepEqual(models, ["qwen3.6-35b-a3b@q5_k_xl"]);
    assert.deepEqual(calls, ["http://10.0.10.142:1234/v1/models"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
