import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)));
const packageJson = JSON.parse(readFileSync(join(rootDir, "package.json"), "utf8"));
const runSource = readFileSync(join(rootDir, "run.mjs"), "utf8");

test("three-model deep probe does not permit host-managed Istara execution", () => {
  const command = packageJson.scripts["probe:deep:three-model"];

  assert.match(command, /ISTARA_BENCHMARK_DONOR_TOPOLOGY=macstudio-colima-qwen-gemma/);
  assert.match(command, /ISTARA_BENCHMARK_SKIP_SANDBOX=1/);
  assert.match(command, /ISTARA_BENCHMARK_START_SANDBOX=0/);
  assert.match(command, /ISTARA_BENCHMARK_START_CLIENT_SANDBOXES=1/);
  assert.match(command, /ISTARA_BENCHMARK_FORCE_DONATED_CHAT=1/);
  assert.match(command, /ISTARA_BENCHMARK_DONOR_COUNT=3/);
  assert.match(command, /ISTARA_BENCHMARK_RESEARCHER_COUNT=2/);
  assert.doesNotMatch(command, /--start-sandbox/);
  assert.doesNotMatch(command, /ISTARA_BENCHMARK_KEEP_DONOR_MODEL_CONTAINERS=1/);
  assert.match(runSource, /function failClosedForHostManagedThreeModelRun\(\)/);
  assert.match(runSource, /if \(failClosedForHostManagedThreeModelRun\(\)\) return;/);
});

test("three-model deep probe records and cleans up Docker benchmark resources", () => {
  const command = packageJson.scripts["probe:deep:three-model"];

  assert.match(command, /ISTARA_BENCHMARK_STOP_COLIMA_AFTER_RUN=1/);
  assert.match(command, /ISTARA_BENCHMARK_COLIMA_MEMORY=12/);
  assert.match(runSource, /const hostManagedThreeModelRun = useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes;/);
  assert.match(runSource, /Docker-only benchmark policy forbids the host-managed three-model topology/);
  assert.doesNotMatch(runSource, /cleanupHostManagedServerSandboxConflict\("pre-health"\)/);
  assert.match(runSource, /function stopColimaIfRequested\(label\)/);
  assert.match(runSource, /stopColimaIfRequested\("run-complete"\)/);
  assert.match(runSource, /stopColimaIfRequested\("crash"\)/);
});

test("three-model deep probe counts every required donor as an observable relay and gates relay start on preflight", () => {
  assert.match(runSource, /if \(hostManagedThreeModelRun\) {\s*return enabled\.filter\(\(profile\) => profile\.required\)\.length;/s);
  assert.match(runSource, /const preflight = preflightRelayLlmFromContainer\(donor\);/);
  assert.match(runSource, /preflightOk/);
  assert.match(runSource, /sandbox\.relay\.blocked_by_preflight/);
  assert.match(runSource, /technical_probe_results/);
  assert.match(runSource, /technical_probes_all_served/);
});

test("three-model Research Spine proof waits for healthy donor relays and requires distinct served routes", () => {
  assert.match(runSource, /function waitForHealthyRelayRoutes\(/);
  assert.match(runSource, /"before-research-spine-coding"/);
  assert.match(runSource, /research-spine-pre-coding-relay-health\.json/);
  assert.match(runSource, /expectedDistinctDonorRoutes: expectedResearchSpineDonorRoutes/);
  assert.match(runSource, /expectedDistinctSources: 0/);
  assert.match(runSource, /acceptanceProfile: mode === "plan-only" \? null : acceptanceProfile/);
  assert.match(runSource, /requireComputeDonation,/);
});

test("LM Studio donor preflight resolves served aliases without logging raw model identifiers", () => {
  assert.match(runSource, /const candidateModelsFor = \(configured, models, rawModels\) =>/);
  assert.match(runSource, /model\.startsWith\(configured \+ ":"\)/);
  assert.match(runSource, /selected_model: model/);
  assert.match(runSource, /donor\.model = resolvedModel;/);
  assert.match(runSource, /selected_model: parsed\.selected_model \? "\[redacted\]"/);
  assert.match(runSource, /redactStdout: true/);
  assert.match(runSource, /redactStderr: true/);
});

test("bounded topology probes can explicitly skip heavy corpus and workflow loops", () => {
  assert.match(runSource, /function nonNegativeIntArg\(name, fallback\)/);
  assert.match(runSource, /const maxUploads = nonNegativeIntArg\("max-uploads"/);
  assert.match(runSource, /const maxChatTurns = nonNegativeIntArg\("max-chat-turns"/);
  assert.match(runSource, /const maxTasks = nonNegativeIntArg\("max-tasks"/);
  assert.match(runSource, /const codingValidationLimit = nonNegativeIntArg\("coding-limit"/);
});
