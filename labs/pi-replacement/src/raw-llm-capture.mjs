import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { gzipSync, gunzipSync } from "node:zlib";

const DEEPSEEK_ESTIMATE_USD_PER_MILLION = {
  input: 0.55,
  output: 2.19,
  cacheRead: 0.14,
  cacheWrite: 0.55,
};

export function normalizeUsage(usage = {}) {
  const input = usage.input ?? usage.prompt_tokens ?? usage.promptTokens ?? usage.input_tokens ?? 0;
  const output = usage.output ?? usage.completion_tokens ?? usage.completionTokens ?? usage.output_tokens ?? 0;
  const cacheRead = usage.cacheRead ?? usage.cache_read_tokens ?? 0;
  const cacheWrite = usage.cacheWrite ?? usage.cache_write_tokens ?? 0;
  const totalTokens = usage.totalTokens ?? usage.total_tokens ?? input + output + cacheRead + cacheWrite;
  const estimatedCost = usage.cost?.total ?? usage.costTotalUsd ?? usage.estimated_cost_usd;
  return {
    input_tokens: input,
    output_tokens: output,
    reasoning_tokens: usage.reasoning ?? usage.reasoning_tokens ?? 0,
    cache_read_tokens: cacheRead,
    cache_write_tokens: cacheWrite,
    total_tokens: totalTokens,
    estimated_cost_usd: Number.isFinite(estimatedCost) ? estimatedCost : 0,
  };
}

export function estimateDeepSeekCostUsd(usage = {}) {
  const normalized = normalizeUsage(usage);
  if (normalized.estimated_cost_usd > 0) {
    return normalized.estimated_cost_usd;
  }
  const input = (normalized.input_tokens / 1_000_000) * DEEPSEEK_ESTIMATE_USD_PER_MILLION.input;
  const output = (normalized.output_tokens / 1_000_000) * DEEPSEEK_ESTIMATE_USD_PER_MILLION.output;
  const cacheRead = (normalized.cache_read_tokens / 1_000_000) * DEEPSEEK_ESTIMATE_USD_PER_MILLION.cacheRead;
  const cacheWrite = (normalized.cache_write_tokens / 1_000_000) * DEEPSEEK_ESTIMATE_USD_PER_MILLION.cacheWrite;
  return Number((input + output + cacheRead + cacheWrite).toFixed(8));
}

export function toJsonl(rows) {
  return rows.map((row) => JSON.stringify(row)).join("\n") + (rows.length ? "\n" : "");
}

export function readGzipJsonl(path) {
  if (!existsSync(path)) return [];
  const body = gunzipSync(readFileSync(path)).toString("utf8").trim();
  if (!body) return [];
  return body.split("\n").filter(Boolean).map((line) => JSON.parse(line));
}

function dedupeByCallId(rows) {
  const byId = new Map();
  for (const row of rows) {
    byId.set(row.call_id ?? `${row.scenario_id}:${row.timestamp_utc}:${byId.size}`, row);
  }
  return [...byId.values()];
}

function writeGzipJsonl(path, rows) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, gzipSync(toJsonl(rows)));
}

export function writeRawCapture(outDir, { promptRows = [], outputRows = [] }, options = {}) {
  const rawDir = join(outDir, "raw-llm-calls");
  const append = options.append ?? true;
  const dedupe = options.dedupe ?? true;
  mkdirSync(rawDir, { recursive: true });

  const promptPath = join(rawDir, "prompts.jsonl.gz");
  const outputPath = join(rawDir, "outputs.jsonl.gz");
  const prompts = append ? [...readGzipJsonl(promptPath), ...promptRows] : promptRows;
  const outputs = append ? [...readGzipJsonl(outputPath), ...outputRows] : outputRows;
  const finalPrompts = dedupe ? dedupeByCallId(prompts) : prompts;
  const finalOutputs = dedupe ? dedupeByCallId(outputs) : outputs;

  writeGzipJsonl(promptPath, finalPrompts);
  writeGzipJsonl(outputPath, finalOutputs);
  return {
    promptPath,
    outputPath,
    promptRecords: finalPrompts.length,
    outputRecords: finalOutputs.length,
  };
}

export function buildPromptRecord({
  callId,
  scenarioId,
  enginePath,
  provider,
  model,
  messages,
  systemPrompt,
  toolSchemas = [],
  skillMemoryContext = {},
  settings = {},
  adapterMode,
  sourceAssets = [],
  surfaces = [],
  timestampUtc = new Date().toISOString(),
  redactionSummary = "No secrets present in prompt payload.",
}) {
  return {
    schema_version: 3,
    call_id: callId,
    scenario_id: scenarioId,
    engine_path: enginePath,
    provider,
    model,
    timestamp_utc: timestampUtc,
    system_prompt: systemPrompt,
    messages,
    tool_schemas: toolSchemas,
    skill_memory_context: skillMemoryContext,
    settings,
    adapter_mode: adapterMode,
    prompt_payload: {
      source_assets: sourceAssets,
      surfaces,
    },
    redaction_summary: redactionSummary,
    redaction_metadata: {
      secrets_redacted: redactionSummary.includes("redacted") || redactionSummary.includes("omitted"),
      credentials_present: false,
      private_data_present: false,
      redacted_fields: redactionSummary.includes("DEEPSEEK_API_KEY") ? ["DEEPSEEK_API_KEY"] : [],
    },
  };
}

export function buildOutputRecord({
  callId,
  scenarioId,
  enginePath,
  provider,
  model,
  rawAssistantOutput = "",
  rawContentBlocks = [],
  toolCallRequests = [],
  stopReason,
  errors = [],
  latencyMs,
  usage = {},
  estimatedCostUsd,
  timestampUtc = new Date().toISOString(),
  redactionSummary = "No secrets present in output payload.",
}) {
  const normalizedUsage = normalizeUsage(usage);
  const cost = Number.isFinite(estimatedCostUsd)
    ? estimatedCostUsd
    : provider === "deepseek"
      ? estimateDeepSeekCostUsd(normalizedUsage)
      : normalizedUsage.estimated_cost_usd;

  return {
    schema_version: 3,
    call_id: callId,
    scenario_id: scenarioId,
    engine_path: enginePath,
    provider,
    model,
    timestamp_utc: timestampUtc,
    raw_assistant_output: rawAssistantOutput,
    raw_content_blocks: rawContentBlocks,
    tool_call_requests: toolCallRequests,
    stop_reason: stopReason,
    errors,
    latency_ms: latencyMs,
    token_usage: {
      ...normalizedUsage,
      estimated_cost_usd: cost,
    },
    estimated_cost_usd: cost,
    redaction_summary: redactionSummary,
    redaction_metadata: {
      secrets_redacted: redactionSummary.includes("redacted") || redactionSummary.includes("omitted"),
      credentials_present: false,
      private_data_present: false,
      redacted_fields: redactionSummary.includes("DEEPSEEK_API_KEY") ? ["DEEPSEEK_API_KEY"] : [],
    },
  };
}
