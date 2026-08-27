import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)));
const packageJson = JSON.parse(readFileSync(join(rootDir, "package.json"), "utf8"));
const runSource = readFileSync(join(rootDir, "run.mjs"), "utf8");
const wrapperSource = readFileSync(join(rootDir, "../../scripts/runner/docker-run.sh"), "utf8");
const insideSource = readFileSync(join(rootDir, "../../scripts/runner/inside.sh"), "utf8");
const composeSource = readFileSync(join(rootDir, "../../docker-compose.vps.yml"), "utf8");

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
  assert.match(runSource, /const dockerRunnerMode = boolEnv\("ISTARA_BENCHMARK_DOCKER_RUNNER", false\);/);
  assert.match(runSource, /const hostManagedThreeModelRun = workload\.petals && useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes && !dockerRunnerMode;/);
  assert.match(wrapperSource, /-e ISTARA_BENCHMARK_DOCKER_RUNNER=1/);
});

test("three-model deep probe records and cleans up Docker benchmark resources", () => {
  const command = packageJson.scripts["probe:deep:three-model"];

  assert.match(command, /ISTARA_BENCHMARK_STOP_COLIMA_AFTER_RUN=1/);
  assert.match(command, /ISTARA_BENCHMARK_COLIMA_MEMORY=12/);
  assert.match(runSource, /const hostManagedThreeModelRun = workload\.petals && useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes && !dockerRunnerMode;/);
  assert.match(runSource, /const dockerOwnedThreeModelRun = workload\.petals && useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes && dockerRunnerMode;/);
  assert.match(runSource, /Docker-only benchmark policy forbids the host-managed three-model topology/);
  assert.doesNotMatch(runSource, /cleanupHostManagedServerSandboxConflict\("pre-health"\)/);
  assert.match(runSource, /function stopColimaIfRequested\(label\)/);
  assert.match(runSource, /stopColimaIfRequested\("run-complete"\)/);
  assert.match(runSource, /stopColimaIfRequested\("crash"\)/);
});

test("three-model deep probe counts every required donor as an observable relay and gates relay start on preflight", () => {
  assert.match(runSource, /if \(hostManagedThreeModelRun\) {\s*return enabled\.filter\(\(profile\) => profile\.required\)\.length;/s);
  assert.match(runSource, /async function preflightRelayLlmFromContainer\(donorProfile = donorProfiles\[0\]\)/);
  assert.match(runSource, /const preflight = await preflightRelayLlmFromContainer\(donor\);/);
  assert.match(runSource, /const preflightDeadline = Date\.now\(\) \+ 180 \* 1000;/);
  assert.match(runSource, /timeoutMs: 60 \* 1000/);
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
  assert.match(runSource, /ISTARA_BENCHMARK_BACKEND_NETWORK/);
  assert.match(wrapperSource, /ISTARA_BENCHMARK_BACKEND_NETWORK=\$BACKEND_NET/);
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
  assert.match(runSource, /const requestedMaxUploads = nonNegativeIntArg\("max-uploads"/);
  assert.match(runSource, /const requestedMaxChatTurns = nonNegativeIntArg\("max-chat-turns"/);
  assert.match(runSource, /const requestedMaxTasks = nonNegativeIntArg\("max-tasks"/);
  assert.match(runSource, /const requestedCodingValidationLimit = nonNegativeIntArg\("coding-limit"/);
});

test("acceptance profile wrapper defaults keep provider and Petals runs focused", () => {
  assert.match(wrapperSource, /provider\|petals\) ISTARA_RUNNER_SKIP_MARATHON=1/);
  assert.match(wrapperSource, /combined\) ISTARA_RUNNER_SKIP_MARATHON=0/);
  assert.match(wrapperSource, /provider\|petals\) ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=0/);
  assert.match(wrapperSource, /-e "ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=\$ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT"/);
  assert.match(insideSource, /acceptance profile/);
  assert.match(insideSource, /provider\|petals\) ISTARA_RUNNER_SKIP_MARATHON=1/);
});

test("runner records profile scope and revokes generated connection credentials", () => {
  assert.match(runSource, /benchmarkWorkloadForProfile/);
  assert.match(runSource, /workload_scope: workload/);
  assert.match(runSource, /featureResults\.distinctDonorEndpoints = workload\.petals && endpointDiversity\.ok/);
  assert.match(runSource, /function revokeGeneratedConnectionStrings\(/);
  assert.match(runSource, /connection-revocation-results\.json/);
  assert.match(runSource, /api\.delete\(`\/api\/connections\//);
});

test("Docker wrapper can select the containerized three-model probe and Compose donor", () => {
  assert.match(wrapperSource, /ISTARA_BENCHMARK_PROBE_SCRIPT/);
  assert.match(insideSource, /ISTARA_BENCHMARK_PROBE_SCRIPT/);
  assert.match(wrapperSource, /--profile three-model/);
  assert.match(composeSource, /donor-gemma:/);
  assert.match(runSource, /provider: "llamacpp"/);
  assert.match(runSource, /host: "http:\/\/donor-gemma:8080"/);
});

test("Docker-owned three-model runs leave explicit provenance in history and reports", () => {
  assert.match(runSource, /docker_runner_mode: Boolean\(dockerRunnerMode\)/);
  assert.match(runSource, /docker_owned_three_model_run: Boolean\(dockerOwnedThreeModelRun\)/);
  assert.match(runSource, /Docker-owned three-model topology:/);
});
