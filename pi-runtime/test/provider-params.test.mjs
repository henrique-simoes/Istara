import test from "node:test";
import assert from "node:assert/strict";

import {
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
