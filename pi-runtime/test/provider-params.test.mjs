import test from "node:test";
import assert from "node:assert/strict";

import { filterParamsForApi } from "../src/provider.mjs";

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
