#!/usr/bin/env node
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { IstaraPiAdapter } from "../src/istara-pi-adapter.mjs";

function parseArg(argv, name, fallback) {
  const flag = argv.findIndex((arg) => arg === `--${name}`);
  if (flag >= 0) return argv[flag + 1];
  return fallback;
}

function makePrompt(role) {
  const shared = [
    "Context: isolated worktree <repo-root>-pi-replacement.",
    "Candidate code boundary: labs/pi-replacement only.",
    "Owner bar: real Pi replacement candidate, Pi owns loop/model/tool execution and trace emission, Istara harnesses are the scenario backbone.",
    "Required coverage: tools, features, final output, research spine, Autoresearch, memory/RAG/ReasoningBank/Memento, tokens, tool calls versus quality, skills, system prompt, A2A, channels/webhooks/Telegram-like lifecycle, documents, plan/review state, steering, benchmark/eval contracts, model routing, telemetry.",
    "Literal conductor limitation: cast routes to Codex CLI probes that hung in OpenClaw and also violate DeepSeek-only routing.",
  ].join("\n");
  if (role === "planner") {
    return `${shared}\n\nAs planner, return 5 concise implementation tasks and acceptance checks.`;
  }
  if (role === "architect") {
    return `${shared}\n\nAs architect, return boundary decisions and risks for expanding the lab adapter without touching production Istara app code.`;
  }
  if (role === "plan-reviewer") {
    return `${shared}\n\nAs plan reviewer/judge, identify any blocker in the plan and state pass/fail for proceeding with a lab-only implementation.`;
  }
  if (role === "code-reviewer") {
    return `${shared}\n\nAs code reviewer, review this intended diff surface: canonical facade includes tasks/findings, document create/search/read/attach, memory search/write, ReasoningBank, Memento, Autoresearch proposal/measurement, webhook receive, steering queue, system prompt audit, benchmark contract mapping, plan lifecycle, skills, A2A delegate/report, channels receive/respond, structured eval, research-step, model-route, telemetry tools; scenario catalog covers all of those surfaces; artifact collector writes surface map, coverage, inventory, scores, markdown, and raw gzipped JSONL. Return pass/fail and actionable findings.`;
  }
  if (role === "remediator") {
    return `${shared}\n\nAs remediator, respond to a prior code-review fail that alleged missing memory, skills, A2A, channels, system prompt, and plan/review coverage. The current candidate has memory search/write, skills.apply capped to three, A2A delegate/report, channels create/receive/respond, DEFAULT_SYSTEM_PROMPT adherence evidence, and task plan/update lifecycle scenarios. State what remediation evidence must be recorded.`;
  }
  if (role === "code-reviewer-rereview") {
    return `${shared}\n\nAs re-reviewer, judge the concrete evidence now available. Tests passed include deterministic no-model candidate tests and artifact collection. Run artifacts include scores.json, coverage-matrix.json, scenario-inventory.jsonl, surface-map.md, tool-call-metrics.json, research-spine-step-quality.json, feature-adherence.json, benchmark-readiness.md, raw-llm-calls/prompts.jsonl.gz, and raw-llm-calls/outputs.jsonl.gz. Expected evidence: 15 baseline and 15 Pi candidate scenarios, every mapped surface covered, Autoresearch governed proposal, ReasoningBank/Memento process memory, webhook/Telegram-like envelope, steering and prompt audit, benchmark-contract mapping, no local models, and explicit production blockers. Literal conductor limitation is recorded as fallback because cast uses Codex CLI probes/workers. Return pass/fail with any remaining blockers.`;
  }
  return `${shared}\n\nAs ${role}, return concise remediation guidance.`;
}

const argv = process.argv.slice(2);
const outDir = resolve(parseArg(argv, "out", "."));
const maxCalls = Number(parseArg(argv, "max-calls", "4"));
const requestedRoles = parseArg(argv, "roles", "");
const roles = (requestedRoles ? requestedRoles.split(",") : ["planner", "architect", "plan-reviewer", "code-reviewer"])
  .map((role) => role.trim())
  .filter(Boolean)
  .slice(0, maxCalls);
mkdirSync(outDir, { recursive: true });

const adapter = new IstaraPiAdapter({ mode: "deepseek", projectId: "pi-replacement-lab" });
const results = [];
for (const role of roles) {
  const result = await adapter.runDeepSeekRoleRound({
    role,
    prompt: makePrompt(role),
    outDir,
    settings: { maxTokens: 260, reasoning: "medium" },
  });
  results.push({
    role,
    ok: result.ok,
    stopReason: result.stopReason,
    latencyMs: result.latencyMs,
    usage: result.usage,
    estimatedCostUsd: result.estimatedCostUsd ?? 0,
    text: result.text,
    error: result.error,
  });
  if (!result.ok) break;
}

const totalEstimatedCostUsd = results.reduce((sum, row) => sum + (row.estimatedCostUsd ?? 0), 0);
const summary = {
  schema_version: 1,
  provider: "deepseek",
  model: "deepseek-v4-pro",
  roles,
  completed_roles: results.map((row) => row.role),
  ok: results.every((row) => row.ok),
  totalEstimatedCostUsd,
  raw_capture: {
    prompts: "raw-llm-calls/prompts.jsonl.gz",
    outputs: "raw-llm-calls/outputs.jsonl.gz",
  },
  results,
};

writeFileSync(`${outDir}/deepseek-role-rounds.json`, JSON.stringify(summary, null, 2) + "\n");
console.log(JSON.stringify(summary, null, 2));
process.exitCode = summary.ok ? 0 : 1;
