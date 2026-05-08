import assert from "node:assert/strict";
import test from "node:test";

import {
  LLMProxy,
  applyThinkingControl,
  detectLocalLLM,
  inferProviderType,
  normalizeThinkingMode,
  stripThinkingBlocks,
} from "./llm-proxy.mjs";

test("infers LM Studio for the default local OpenAI-compatible port", () => {
  assert.equal(inferProviderType("ollama", "http://192.0.2.142:1234"), "lmstudio");
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
    const proxy = new LLMProxy("ollama", "http://192.0.2.142:1234", "");
    const probe = await proxy.probeModels();

    assert.equal(proxy.providerType, "lmstudio");
    assert.deepEqual(probe.models, ["qwen3.6-35b-a3b"]);
    assert.equal(probe.modelCapabilities["qwen3.6-35b-a3b"].supports_vision, true);
    assert.equal(probe.modelCapabilities["qwen3.6-35b-a3b"].is_loaded, true);
    assert.deepEqual(calls, ["http://192.0.2.142:1234/api/v1/models"]);
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

test("passes requested context length through LM Studio model loads without unloading by default", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url === "http://localhost:1234/api/v1/models") {
      return new Response(JSON.stringify({
        models: [{
          key: "qwen3",
          type: "llm",
          loaded_instances: [{ id: "qwen3", config: { context_length: 4096 } }],
        }],
      }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url === "http://localhost:1234/api/v1/models/load") {
      return new Response(JSON.stringify({ loaded: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error(`unexpected fetch ${url}`);
  };

  try {
    const proxy = new LLMProxy("lmstudio", "http://localhost:1234", "");
    await proxy.loadModel("qwen3", { contextLength: 8192 });

    assert.deepEqual(calls[0], {
      url: "http://localhost:1234/api/v1/models/load",
      body: {
        model: "qwen3",
        echo_load_config: true,
        context_length: 8192,
      },
    });
    assert.equal(calls[1].url, "http://localhost:1234/api/v1/models");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("unloads LM Studio instances only when explicitly allowed", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url === "http://localhost:1234/api/v1/models") {
      return new Response(JSON.stringify({
        models: [{
          key: "qwen3",
          type: "llm",
          loaded_instances: [{ id: "qwen3", config: { context_length: 4096 } }],
        }],
      }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url === "http://localhost:1234/api/v1/models/unload") {
      return new Response(JSON.stringify({ instance_id: "qwen3" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url === "http://localhost:1234/api/v1/models/load") {
      return new Response(JSON.stringify({ loaded: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error(`unexpected fetch ${url}`);
  };

  try {
    const proxy = new LLMProxy("lmstudio", "http://localhost:1234", "");
    await proxy.loadModel("qwen3", { contextLength: 8192, allowUnload: true });

    assert.equal(calls[0].url, "http://localhost:1234/api/v1/models");
    assert.deepEqual(calls[1], {
      url: "http://localhost:1234/api/v1/models/unload",
      body: { instance_id: "qwen3" },
    });
    assert.deepEqual(calls[2], {
      url: "http://localhost:1234/api/v1/models/load",
      body: {
        model: "qwen3",
        echo_load_config: true,
        context_length: 8192,
      },
    });
    assert.equal(calls[3].url, "http://localhost:1234/api/v1/models");
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
      content: [
        { type: "thinking", thinking: "private reasoning" },
        { type: "redacted_thinking", data: "opaque" },
        { type: "text", text: "hello from claude" },
      ],
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

test("strips inline thinking blocks", () => {
  assert.equal(stripThinkingBlocks("<think>private</think>\n\nvisible"), "visible");
  assert.equal(
    stripThinkingBlocks("<|channel>thought\nprivate\n<channel|>visible<turn|>"),
    "visible",
  );
});

test("applies thinking controls without provider payload fields", () => {
  assert.equal(normalizeThinkingMode("server-default"), "server_default");
  assert.equal(normalizeThinkingMode("show_raw"), "server_default");

  const messages = applyThinkingControl(
    [{ role: "user", content: "hello" }],
    "off",
  );
  const again = applyThinkingControl(messages, "off");

  assert.equal(messages[0].role, "system");
  assert.match(messages[0].content, /Istara thinking mode is OFF/);
  assert.equal(again[0].content.match(/Istara thinking mode is OFF/g).length, 1);
});

test("suppresses reasoning fields from OpenAI-compatible responses", async () => {
  const originalFetch = globalThis.fetch;
  let capturedPayload;
  globalThis.fetch = async (_url, init = {}) => {
    capturedPayload = JSON.parse(init.body);
    return new Response(JSON.stringify({
    choices: [{
      message: {
        role: "assistant",
        content: "<think>private reasoning</think>\n\nvisible answer",
        reasoning_content: "also private",
      },
    }],
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const proxy = new LLMProxy("openai_compat", "http://localhost:1234", "");
    const result = await proxy.handleRequest({
      model: "qwen3",
      messages: [{ role: "user", content: "Hi" }],
      thinking_mode: "off",
    });

    assert.deepEqual(result, { message: { role: "assistant", content: "visible answer" } });
    assert.equal(capturedPayload.thinking_mode, undefined);
    assert.match(capturedPayload.messages[0].content, /Istara thinking mode is OFF/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("forwards tools and response_format through OpenAI-compatible relay requests", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, body: JSON.parse(options.body) });
    return new Response(JSON.stringify({
      choices: [{ message: { role: "assistant", content: "ok" } }],
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const proxy = new LLMProxy("openai_compat", "http://localhost:1234", "");
    const tools = [{ type: "function", function: { name: "lookup", parameters: {} } }];
    const responseFormat = { type: "json_schema", json_schema: { name: "out" } };
    await proxy.handleRequest({
      model: "qwen3",
      messages: [{ role: "user", content: "Hi" }],
      tools,
      response_format: responseFormat,
    });

    assert.equal(calls[0].url, "http://localhost:1234/v1/chat/completions");
    assert.deepEqual(calls[0].body.tools, tools);
    assert.deepEqual(calls[0].body.response_format, responseFormat);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("suppresses reasoning fields from Ollama responses", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    message: {
      role: "assistant",
      content: "<think>private reasoning</think>\n\nvisible answer",
      reasoning_content: "also private",
      thinking: "private too",
    },
    done: true,
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

  try {
    const proxy = new LLMProxy("ollama", "http://localhost:11434", "");
    const result = await proxy.handleRequest({
      model: "qwen3",
      messages: [{ role: "user", content: "Hi" }],
    });

    assert.deepEqual(result, {
      message: { role: "assistant", content: "visible answer" },
      done: true,
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("suppresses Gemma thought channels from OpenAI-compatible responses", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    choices: [{
      message: {
        role: "assistant",
        content: "<|channel>thought\nprivate reasoning\n<channel|>visible answer<turn|>",
      },
    }],
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

  try {
    const proxy = new LLMProxy("openai_compat", "http://localhost:1234", "");
    const result = await proxy.handleRequest({
      model: "gemma-4",
      messages: [{ role: "user", content: "Hi" }],
    });

    assert.deepEqual(result, { message: { role: "assistant", content: "visible answer" } });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
