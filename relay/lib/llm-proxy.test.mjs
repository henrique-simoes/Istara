import assert from "node:assert/strict";
import test from "node:test";

import { LLMProxy, detectLocalLLM, inferProviderType } from "./llm-proxy.mjs";

test("infers LM Studio for the default local OpenAI-compatible port", () => {
  assert.equal(inferProviderType("ollama", "http://10.0.10.142:1234"), "lmstudio");
  assert.equal(inferProviderType("", "http://localhost:1234"), "lmstudio");
});

test("infers OpenAI-compatible base paths without duplicating /v1", () => {
  assert.equal(inferProviderType("ollama", "https://example.test/v1"), "openai_compat");
  assert.equal(inferProviderType("vllm", "http://localhost:8000"), "vllm");
  assert.equal(inferProviderType("llama.cpp", "http://localhost:8080"), "llamacpp");
  assert.equal(inferProviderType("", "https://api.anthropic.com"), "anthropic");
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

test("uses LM Studio native model metadata when a 1234 host was mislabeled as Ollama", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return new Response(JSON.stringify({
      models: [{
        key: "qwen3.6-35b-a3b",
        type: "llm",
        capabilities: { vision: true, trained_for_tool_use: true },
        loaded_instances: [{ id: "qwen3.6-35b-a3b", config: { context_length: 100000 } }],
      }],
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const proxy = new LLMProxy("ollama", "http://10.0.10.142:1234", "");
    const probe = await proxy.probeModels();

    assert.equal(proxy.providerType, "lmstudio");
    assert.deepEqual(probe.models, ["qwen3.6-35b-a3b"]);
    assert.equal(probe.modelCapabilities["qwen3.6-35b-a3b"].supports_vision, true);
    assert.equal(probe.modelCapabilities["qwen3.6-35b-a3b"].is_loaded, true);
    assert.deepEqual(calls, ["http://10.0.10.142:1234/api/v1/models"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("detects the first reachable local OpenAI-compatible server", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    if (url === "http://localhost:1234/api/v1/models") {
      return new Response(JSON.stringify({ models: [{ key: "local-openai", type: "llm" }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error("unreachable");
  };

  try {
    const detected = await detectLocalLLM({
      candidates: [
        { providerType: "lmstudio", host: "http://localhost:1234" },
        { providerType: "ollama", host: "http://localhost:11434" },
      ],
    });

    assert.equal(detected.providerType, "lmstudio");
    assert.equal(detected.host, "http://localhost:1234");
    assert.deepEqual(detected.models, ["local-openai"]);
    assert.equal(detected.modelCapabilities["local-openai"].source, "lmstudio");
    assert.equal(detected.modelCapabilities["local-openai"].supports_vision, false);
    assert.deepEqual(calls, ["http://localhost:1234/api/v1/models"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("detects an empty but reachable local LLM server so heartbeat can advertise later", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ data: [] }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

  try {
    const detected = await detectLocalLLM({
      candidates: [{ providerType: "lmstudio", host: "http://localhost:1234" }],
    });

    assert.equal(detected.providerType, "lmstudio");
    assert.equal(detected.host, "http://localhost:1234");
    assert.deepEqual(detected.models, []);
    assert.deepEqual(detected.modelCapabilities, {});
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("falls back to Ollama when OpenAI-compatible local servers are unreachable", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url === "http://localhost:11434/api/tags") {
      return new Response(JSON.stringify({ models: [{ name: "llama3" }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error("unreachable");
  };

  try {
    const detected = await detectLocalLLM({
      candidates: [
        { providerType: "lmstudio", host: "http://localhost:1234" },
        { providerType: "ollama", host: "http://localhost:11434" },
      ],
    });

    assert.equal(detected.providerType, "ollama");
    assert.equal(detected.host, "http://localhost:11434");
    assert.deepEqual(detected.models, ["llama3"]);
    assert.equal(detected.modelCapabilities.llama3.source, "ollama");
    assert.equal(detected.modelCapabilities.llama3.endpoint_family, "ollama");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("uses Anthropic headers and Messages API normalization", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, headers: options.headers, body: options.body });
    return new Response(JSON.stringify({
      content: [{ type: "text", text: "hello from claude" }],
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const proxy = new LLMProxy("anthropic", "https://api.anthropic.com", "test-key");
    const result = await proxy.handleRequest({
      model: "claude-sonnet-4-20250514",
      messages: [{ role: "user", content: "Hi" }],
    });

    assert.equal(calls[0].url, "https://api.anthropic.com/v1/messages");
    assert.equal(calls[0].headers["x-api-key"], "test-key");
    assert.equal(calls[0].headers["anthropic-version"], "2023-06-01");
    assert.deepEqual(result, { message: { role: "assistant", content: "hello from claude" } });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
