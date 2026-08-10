#!/usr/bin/env node
import { IstaraContractBaseline, IstaraPiAdapter } from "../src/istara-pi-adapter.mjs";
import { ISTARA_PI_SCENARIOS } from "../src/scenario-catalog.mjs";

function parseArg(argv, name, fallback) {
  const flag = argv.findIndex((arg) => arg === `--${name}`);
  if (flag >= 0) {
    return argv[flag + 1];
  }
  return fallback;
}

const argv = process.argv.slice(2);
const mode = parseArg(argv, "mode", "no-model");
const scenario = parseArg(argv, "scenario", "chat.tool_loop.task_and_finding");
const engine = parseArg(argv, "engine", "pi");
const outDir = parseArg(argv, "out", undefined);

const adapter = new IstaraPiAdapter({ mode, projectId: "pi-replacement-lab" });
const prepared = adapter.prepareRun({
  scenario: mode === "deepseek" ? "provider.deepseek_v4_pro" : scenario,
  scenarioCount: scenario === "all" ? ISTARA_PI_SCENARIOS.length : 1,
});

let result;
if (mode === "deepseek") {
  result = await adapter.runDeepSeekProviderSmoke({ outDir });
} else if (engine === "baseline") {
  const baseline = new IstaraContractBaseline({ projectId: "pi-replacement-lab" });
  result = scenario === "all" ? await baseline.runAllScenarios() : await baseline.runScenario(scenario);
} else if (engine === "both") {
  const baseline = new IstaraContractBaseline({ projectId: "pi-replacement-lab" });
  result = {
    baseline: scenario === "all" ? await baseline.runAllScenarios() : await baseline.runScenario(scenario),
    candidate: scenario === "all" ? await adapter.runAllNoModelScenarios() : await adapter.runNoModelScenario(scenario),
  };
} else {
  result = scenario === "all" ? await adapter.runAllNoModelScenarios() : await adapter.runNoModelScenario(scenario);
}

function isOk(value) {
  if (Array.isArray(value)) return value.every((item) => item.ok);
  if (value?.baseline || value?.candidate) return isOk(value.baseline) && isOk(value.candidate);
  return Boolean(value?.ok);
}

console.log(JSON.stringify({ prepared, result }, null, 2));
process.exitCode = isOk(result) ? 0 : 1;
