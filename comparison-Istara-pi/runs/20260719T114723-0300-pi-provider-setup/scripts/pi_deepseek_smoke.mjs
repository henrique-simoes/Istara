#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createGzip } from "node:zlib";
import { createWriteStream, writeFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const RUN_ROOT = resolve(dirname(SCRIPT_PATH), "..");
const LOG_DIR = resolve(RUN_ROOT, "logs");
const DEP_ROOT = resolve(RUN_ROOT, "tmp-pi-deps");
const PACKAGE_ROOT = resolve(DEP_ROOT, "node_modules", "@earendil-works", "pi-ai");
const MODEL_ID = "deepseek-v4-pro";

function capped(value, limit = 600) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length <= limit ? text : `${text.slice(0, limit)}...[truncated]`;
}

function keychainSecret() {
  const key = execFileSync(
    "security",
    ["find-generic-password", "-a", "openclaw", "-s", "istara-pi-deepseek", "-w"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  ).trim();
  if (!key) {
    throw new Error("DeepSeek key unavailable from macOS Keychain");
  }
  return key;
}

async function writeGzipJsonl(path, rows) {
  await new Promise((resolvePromise, rejectPromise) => {
    const gzip = createGzip();
    const out = createWriteStream(path);
    out.on("finish", resolvePromise);
    out.on("error", rejectPromise);
    gzip.on("error", rejectPromise);
    gzip.pipe(out);
    for (const row of rows) {
      gzip.write(`${JSON.stringify(row)}\n`);
    }
    gzip.end();
  });
}

function textBlocks(message) {
  return (message.content ?? [])
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("");
}

function thinkingBlockCount(message) {
  return (message.content ?? []).filter((block) => block.type === "thinking").length;
}

async function main() {
  await mkdir(LOG_DIR, { recursive: true });
  const started = Date.now();
  const result = {
    smoke: "pi_provider_deepseek",
    package: "@earendil-works/pi-ai",
    package_version: null,
    adapter_mode: "library_builtin_deepseek_provider",
    provider: "deepseek",
    base_url: "https://api.deepseek.com",
    model: MODEL_ID,
    api: null,
    reasoning_requested: "high",
    thinking_requested: true,
    max_tokens_requested: 16,
    deepseek_key_present: false,
    secret_value_logged: false,
    passed: false,
    status_code: null,
    latency_ms: null,
    usage: null,
    response_model: null,
    stop_reason: null,
    thinking_block_count: 0,
    output_text_capped: "",
    failure_reason_capped: "",
    provider_config: null,
  };

  try {
    const pkg = await import(pathToFileURL(resolve(PACKAGE_ROOT, "package.json")).href, {
      with: { type: "json" },
    });
    result.package_version = pkg.default.version;

    const [{ createModels }, { deepseekProvider }] = await Promise.all([
      import(pathToFileURL(resolve(PACKAGE_ROOT, "dist", "index.js")).href),
      import(pathToFileURL(resolve(PACKAGE_ROOT, "dist", "providers", "deepseek.js")).href),
    ]);

    const key = keychainSecret();
    process.env.DEEPSEEK_API_KEY = key;
    result.deepseek_key_present = true;

    const models = createModels();
    models.setProvider(deepseekProvider());
    const model = models.getModel("deepseek", MODEL_ID);
    if (!model) {
      throw new Error("deepseek-v4-pro not present in Pi DeepSeek model catalog");
    }

    result.api = model.api;
    result.provider_config = {
      catalog_model_id: model.id,
      catalog_provider: model.provider,
      catalog_base_url: model.baseUrl,
      reasoning: model.reasoning,
      compat: model.compat,
      thinking_level_map: model.thinkingLevelMap,
    };

    const context = {
      systemPrompt: "Return exactly the word pong.",
      messages: [
        {
          role: "user",
          content: "Connectivity smoke. Reply with pong.",
          timestamp: Date.now(),
        },
      ],
    };

    let observedPayload = null;
    const response = await models.completeSimple(model, context, {
      reasoning: "high",
      maxTokens: 16,
      temperature: 0,
      timeoutMs: 45000,
      cacheRetention: "none",
      onPayload: (payload) => {
        observedPayload = {
          model: payload?.model,
          stream: payload?.stream,
          max_completion_tokens_present: Object.hasOwn(payload ?? {}, "max_completion_tokens"),
          max_tokens_present: Object.hasOwn(payload ?? {}, "max_tokens"),
          reasoning_effort: payload?.reasoning_effort,
          thinking: payload?.thinking,
          store: payload?.store,
          message_count: Array.isArray(payload?.messages) ? payload.messages.length : null,
        };
      },
      onResponse: (responseMetadata) => {
        result.status_code = responseMetadata.status;
      },
    });

    const output = textBlocks(response).trim();
    result.passed = response.stopReason !== "error" && output.toLowerCase() === "pong";
    result.response_model = response.responseModel ?? response.model;
    result.stop_reason = response.stopReason;
    result.usage = response.usage;
    result.thinking_block_count = thinkingBlockCount(response);
    result.output_text_capped = capped(output);
    result.provider_config.observed_payload = observedPayload;

    if (!result.passed) {
      result.failure_reason_capped = capped(
        `Unexpected Pi response: stop=${response.stopReason}; text=${output}; error=${response.errorMessage ?? ""}`,
      );
    }

    await writeGzipJsonl(resolve(RUN_ROOT, "trace.jsonl.gz"), [
      {
        ts: new Date(started).toISOString(),
        event: "pi_provider_smoke_start",
        package: result.package,
        package_version: result.package_version,
        adapter_mode: result.adapter_mode,
        provider: result.provider,
        model: result.model,
        deepseek_key_present: result.deepseek_key_present,
      },
      {
        ts: new Date().toISOString(),
        event: "pi_provider_smoke_done",
        passed: result.passed,
        status_code: result.status_code,
        latency_ms: Date.now() - started,
        usage: result.usage,
        stop_reason: result.stop_reason,
      },
    ]);
    await writeGzipJsonl(resolve(RUN_ROOT, "outputs.jsonl.gz"), [
      {
        ts: new Date().toISOString(),
        output_text_capped: result.output_text_capped,
        response_model: result.response_model,
        stop_reason: result.stop_reason,
      },
    ]);
  } catch (error) {
    result.failure_reason_capped = capped(`${error?.name ?? "Error"}: ${error?.message ?? String(error)}`);
  } finally {
    delete process.env.DEEPSEEK_API_KEY;
    result.latency_ms = Date.now() - started;
    writeFileSync(resolve(LOG_DIR, "pi-provider-deepseek-smoke.json"), `${JSON.stringify(result, null, 2)}\n`);
    console.log(
      JSON.stringify(
        {
          smoke: result.smoke,
          passed: result.passed,
          status_code: result.status_code,
          latency_ms: result.latency_ms,
          usage: result.usage,
          response_model: result.response_model,
          failure_reason_capped: result.failure_reason_capped,
        },
        null,
        2,
      ),
    );
  }

  return result.passed ? 0 : 1;
}

process.exitCode = await main();
