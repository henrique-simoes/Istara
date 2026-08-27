#!/usr/bin/env node

import { existsSync, readFileSync } from "fs";
import { createHash, randomBytes } from "crypto";
import { dirname, join, resolve } from "path";
import { homedir } from "os";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";
import { createInterface } from "readline/promises";

import { IstaraApiClient } from "./lib/api-client.mjs";
import { generateCorpus, PROJECT_CONTEXT } from "./lib/corpus.mjs";
import { runIntegrationMatrix } from "./lib/integration-discovery.mjs";
import { BenchmarkLogger, makeRunId } from "./lib/logger.mjs";
import {
  RESEARCHER_PERSONAS,
  buildChatTurns,
  buildCollaborativeChatTurns,
  buildInterviewProcessPlan,
  buildTaskPlan,
  reviewerAssessment,
} from "./lib/persona.mjs";
import { runUiJourney } from "./lib/playwright-ui.mjs";
import {
  exerciseResearchSpineValidation,
  exerciseSelfImprovementGovernance,
} from "./lib/research-spine-probes.mjs";
import {
  benchmarkExitCode,
  benchmarkWorkloadForProfile,
  liveAcceptanceBlockers,
  normalizeAcceptanceProfile,
  scoreRun,
  writeScorecardMarkdown,
} from "./lib/scoring.mjs";
import {
  buildDonorModelSandboxConfig,
  dockerArgsForDonorModelSandbox,
  donorEndpointDiversity,
  q4EvidenceFrom,
  summarizeDonorModelSandbox,
  validateDonorModelSandbox,
} from "./lib/donor-sandboxes.mjs";
import { inferProviderType } from "../../relay/lib/llm-proxy.mjs";
import {
  buildBenchmarkProvenance,
  resolveGitCommitWithoutGit,
  validateBenchmarkProvenance,
} from "./lib/provenance.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "../..");
const benchmarkModelRoot = resolve(
  process.env.ISTARA_BENCHMARK_MODEL_ROOT || join(homedir(), "Istara-Projects", "models"),
);
const systemPromptPath = join(__dirname, "system-prompt.md");
const benchmarkRegistryPath = join(__dirname, "benchmark-registry.json");
const systemPromptContent = readFileSync(systemPromptPath, "utf8");
const benchmarkRegistry = JSON.parse(readFileSync(benchmarkRegistryPath, "utf8"));
const systemPromptHash = createHash("sha256").update(systemPromptContent).digest("hex");
const benchmarkRegistryHash = createHash("sha256")
  .update(readFileSync(benchmarkRegistryPath))
  .digest("hex");
const systemPromptVersion = systemPromptContent.match(/^Version:\s*(.+)$/m)?.[1]?.trim() || "unknown";
const LIVE_LLM_ENV_FILES = [
  join(repoRoot, ".env"),
  join(repoRoot, ".env.local"),
  join(repoRoot, "backend", ".env"),
  join(repoRoot, "backend", ".env.local"),
];
const LIVE_LLM_ENV_KEYS = new Set([
  "ISTARA_LIVE_LLM_BASE_URL",
  "ISTARA_PRIMARY_LLM_TEST_BASE_URL",
  "LMSTUDIO_HOST",
  "ISTARA_LIVE_LLM_API_KEY",
  "ISTARA_LLM_TEST_API_KEY",
  "ISTARA_PRIMARY_LLM_TEST_API_KEY",
  "LMSTUDIO_API_KEY",
  "ISTARA_LIVE_LLM_KEYCHAIN_SERVICE",
]);
const LIVE_LLM_BASE_URL_KEYS = [
  "ISTARA_LIVE_LLM_BASE_URL",
  "ISTARA_PRIMARY_LLM_TEST_BASE_URL",
  "LMSTUDIO_HOST",
];
const LIVE_LLM_API_KEY_KEYS = [
  "ISTARA_LIVE_LLM_API_KEY",
  "ISTARA_LLM_TEST_API_KEY",
  "ISTARA_PRIMARY_LLM_TEST_API_KEY",
  "LMSTUDIO_API_KEY",
];
const PRIMARY_TEST_MODEL = "google/gemma-4-e4b";
const FUTURE_QWEN_DONOR_MODEL = "Qwen3.5-4B";
const DEFAULT_LIVE_LLM_KEYCHAIN_SERVICE = "istara-live-openai-compatible-tests";
const startupConfigWarnings = [];
const THREE_MODEL_DONOR_TOPOLOGY_ALIASES = new Set([
  "3-model",
  "3model",
  "three-model",
  "macstudio-colima",
  "macstudio-colima-qwen-gemma",
  "macstudio+colima",
  "local-three-model",
]);

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0) return process.argv[index + 1] || "true";
  return fallback;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function intArg(name, fallback) {
  const value = arg(name, process.env[`ISTARA_BENCHMARK_${name.toUpperCase().replace(/-/g, "_")}`]);
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function nonNegativeIntArg(name, fallback) {
  const value = arg(name, process.env[`ISTARA_BENCHMARK_${name.toUpperCase().replace(/-/g, "_")}`]);
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function floatEnv(name, fallback) {
  const parsed = Number.parseFloat(process.env[name]);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function boolEnv(name, fallback = false) {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function parseEnvAssignment(rawLine, allowedKeys = null) {
  let line = rawLine.trim();
  if (!line || line.startsWith("#") || !line.includes("=")) return null;
  if (line.startsWith("export ")) line = line.slice("export ".length).trim();
  const index = line.indexOf("=");
  const key = line.slice(0, index).trim();
  if (allowedKeys && !allowedKeys.has(key)) return null;
  let value = line.slice(index + 1).trim();
  if (value.length >= 2 && value[0] === value[value.length - 1] && ["'", "\""].includes(value[0])) {
    value = value.slice(1, -1);
  }
  return [key, value];
}

function loadBackendEnv() {
  const files = [
    join(repoRoot, "backend", ".env"),
    join(repoRoot, "backend", ".env.local"),
  ];
  const values = {};
  const sources = {};
  for (const file of files) {
    try {
      const content = readFileSync(file, "utf8");
      for (const line of content.split(/\r?\n/)) {
        const parsed = parseEnvAssignment(line);
        if (!parsed) continue;
        const [key, value] = parsed;
        values[key] = value;
        sources[key] = file.replace(`${repoRoot}/`, "");
      }
    } catch {}
  }
  values.__sources = sources;
  return values;
}

function configuredValue(config, key, fallback = "") {
  return (process.env[key] ?? config[key] ?? fallback ?? "").trim();
}

function loadLiveLlmEnv() {
  const values = {};
  const sources = {};
  const loadedFiles = [];
  for (const key of LIVE_LLM_ENV_KEYS) {
    if (Object.prototype.hasOwnProperty.call(process.env, key)) {
      values[key] = process.env[key] || "";
      sources[key] = "process-env";
    }
  }
  for (const file of LIVE_LLM_ENV_FILES) {
    if (!existsSync(file)) continue;
    let loaded = false;
    try {
      const content = readFileSync(file, "utf8");
      for (const line of content.split(/\r?\n/)) {
        const parsed = parseEnvAssignment(line, LIVE_LLM_ENV_KEYS);
        if (!parsed) continue;
        const [key, value] = parsed;
        if (!Object.prototype.hasOwnProperty.call(values, key)) {
          values[key] = value;
          sources[key] = file.replace(`${repoRoot}/`, "");
        }
        loaded = true;
      }
    } catch {}
    if (loaded) loadedFiles.push(file.replace(`${repoRoot}/`, ""));
  }
  values.__sources = sources;
  values.__loadedFiles = loadedFiles;
  return values;
}

function pickFirstPresent(config, keys) {
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(config, key)) {
      return {
        key,
        value: String(config[key] || "").trim(),
        source: config.__sources?.[key] || "configured",
      };
    }
  }
  return { key: "", value: "", source: "unset" };
}

function pickFirstNonEmpty(config, keys) {
  for (const key of keys) {
    const value = String(config[key] || "").trim();
    if (value) {
      return {
        key,
        value,
        source: config.__sources?.[key] || "configured",
      };
    }
  }
  return { key: "", value: "", source: "unset" };
}

function readKeychainSecret(service) {
  if (!existsSync("/usr/bin/security")) return "";
  try {
    const result = spawnSync("/usr/bin/security", [
      "find-generic-password",
      "-a",
      process.env.USER || "istara",
      "-s",
      service || DEFAULT_LIVE_LLM_KEYCHAIN_SERVICE,
      "-w",
    ], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 5000,
    });
    return result.status === 0 ? result.stdout.trim() : "";
  } catch {
    return "";
  }
}

function liveLlmProfileFromTestingContract() {
  const env = loadLiveLlmEnv();
  const base = pickFirstPresent(env, LIVE_LLM_BASE_URL_KEYS);
  const key = pickFirstNonEmpty(env, LIVE_LLM_API_KEY_KEYS);
  const keychainService = String(env.ISTARA_LIVE_LLM_KEYCHAIN_SERVICE || DEFAULT_LIVE_LLM_KEYCHAIN_SERVICE).trim();
  let apiKey = key.value;
  let apiKeySource = key.source;
  if (!apiKey) {
    apiKey = readKeychainSecret(keychainService);
    apiKeySource = apiKey ? "macos-keychain" : "unset";
  }
  return {
    baseUrl: base.value,
    baseUrlKey: base.key,
    baseUrlSource: base.source,
    apiKey,
    apiKeySource,
    keychainServiceConfigured: keychainService !== DEFAULT_LIVE_LLM_KEYCHAIN_SERVICE,
    keychainServiceSource: env.__sources?.ISTARA_LIVE_LLM_KEYCHAIN_SERVICE || "default",
    model: PRIMARY_TEST_MODEL,
    modelSource: "tests/llm_test_config.py:PRIMARY_TEST_MODEL",
    loadedEnvFiles: env.__loadedFiles || [],
  };
}

function replaceLocalhostForContainer(url) {
  if (!url) return url;
  try {
    const parsed = new URL(url);
    if (["localhost", "127.0.0.1", "::1"].includes(parsed.hostname)) {
      parsed.hostname = "host.docker.internal";
    }
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return url;
  }
}

function stripOpenAIPathForNativeLMStudio(url, provider) {
  if (provider !== "lmstudio" || !url) return url;
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/\/+$/, "");
    if (path === "/v1") {
      parsed.pathname = "";
      return parsed.toString().replace(/\/$/, "");
    }
  } catch {}
  return url.replace(/\/$/, "");
}

function hostSummary(url) {
  try {
    const parsed = new URL(url);
    const local = ["localhost", "127.0.0.1", "::1"].includes(parsed.hostname);
    return {
      configured: Boolean(url),
      scheme: parsed.protocol.replace(":", ""),
      host_kind: local ? "localhost" : parsed.hostname === "host.docker.internal" ? "docker-host" : "non-localhost",
      port_set: Boolean(parsed.port),
      has_path: Boolean(parsed.pathname && parsed.pathname !== "/"),
    };
  } catch {
    return { configured: Boolean(url), parseable: false };
  }
}

function parseJsonConfig(raw, source) {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    startupConfigWarnings.push({
      source,
      error: `Invalid JSON: ${error.message}`,
    });
    return null;
  }
}

function readJsonConfigFile(filePath, source) {
  if (!filePath) return null;
  try {
    return parseJsonConfig(readFileSync(resolve(filePath), "utf8"), source);
  } catch (error) {
    startupConfigWarnings.push({
      source,
      error: `Could not read ${filePath}: ${error.message}`,
    });
    return null;
  }
}

function asArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function parseConnectionStringList(raw) {
  if (!raw) return [];
  const trimmed = String(raw).trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    const parsed = parseJsonConfig(trimmed, "connection-string-list");
    if (Array.isArray(parsed)) return parsed.map(String).map((item) => item.trim()).filter(Boolean);
    if (parsed && typeof parsed === "object") {
      return asArray(
        parsed.connection_strings
          || parsed.connectionStrings
          || parsed.compute_donations
          || parsed.computeDonations
          || parsed.user_invites
          || parsed.userInvites,
      ).map(String).map((item) => item.trim()).filter(Boolean);
    }
    return [];
  }
  return trimmed.split(/\r?\n|[,|]/).map((item) => item.trim()).filter(Boolean);
}

function decodeConnectionStringPayloadUnsafe(connectionString) {
  const value = String(connectionString || "");
  if (!value.startsWith("rcl_")) return null;
  const body = value.slice("rcl_".length);
  const parts = body.split(".");
  if (parts.length !== 2) return null;
  try {
    const padded = parts[0].padEnd(parts[0].length + ((4 - (parts[0].length % 4)) % 4), "=");
    const payload = JSON.parse(Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));
    return { payload, signature: parts[1] };
  } catch {
    return null;
  }
}

function rewriteRelayConnectionStringForContainer(connectionString) {
  const decoded = decodeConnectionStringPayloadUnsafe(connectionString);
  if (!decoded) return { connectionString, rewritten: false };
  const payload = decoded.payload;
  const before = {
    server_url: payload.server_url || "",
    ws_url: payload.ws_url || "",
  };
  const after = {
    server_url: payload.server_url ? replaceLocalhostForContainer(payload.server_url) : "",
    ws_url: payload.ws_url ? replaceLocalhostForContainer(payload.ws_url) : "",
  };
  const wouldNeedRewrite = before.server_url !== after.server_url || before.ws_url !== after.ws_url;
  return {
    connectionString,
    rewritten: false,
    needsContainerReachableUrl: wouldNeedRewrite,
    before: {
      server_url: hostSummary(before.server_url),
      ws_url: hostSummary(before.ws_url),
    },
    after: {
      server_url: hostSummary(after.server_url),
      ws_url: hostSummary(after.ws_url),
    },
    note: wouldNeedRewrite
      ? "The relay container needs a Docker-reachable server URL, but compute donation strings are HMAC-signed by the server and cannot be rewritten locally. Generate the string with ISTARA_BENCHMARK_CONNECTION_SERVER_URL/WS_URL or let the benchmark generate Docker-reachable URLs."
      : "Connection string already uses container-reachable relay URLs; no local payload rewrite was applied.",
  };
}

function rememberConnectionStringSensitiveValues(connectionString) {
  const decoded = decodeConnectionStringPayloadUnsafe(connectionString);
  if (!decoded?.payload) return;
  for (const value of [
    decoded.payload.server_url,
    decoded.payload.ws_url,
    decoded.payload.network_token,
    decoded.payload.jwt,
  ]) {
    if (typeof value === "string" && value.trim()) extraSensitiveLogValues.add(value.trim());
  }
}

function firstNonEmpty(...values) {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    const stringValue = String(value).trim();
    if (stringValue) return stringValue;
  }
  return "";
}

function firstExistingPath(...paths) {
  for (const path of paths) {
    if (path && existsSync(path)) return path;
  }
  return firstNonEmpty(...paths);
}

function envDonorValue(index, keys) {
  for (const key of keys) {
    const value = process.env[`ISTARA_BENCHMARK_DONOR_${index}_${key}`];
    if (value !== undefined && String(value).trim()) {
      return {
        value: String(value).trim(),
        source: `ISTARA_BENCHMARK_DONOR_${index}_${key}`,
      };
    }
  }
  return { value: "", source: "" };
}

function loadConfiguredDonorProfiles() {
  const profiles = [];
  const fileConfig = readJsonConfigFile(
    process.env.ISTARA_BENCHMARK_DONOR_PROFILES_FILE,
    "ISTARA_BENCHMARK_DONOR_PROFILES_FILE",
  );
  const inlineConfig = parseJsonConfig(
    process.env.ISTARA_BENCHMARK_DONOR_PROFILES_JSON || "",
    "ISTARA_BENCHMARK_DONOR_PROFILES_JSON",
  );
  for (const config of [fileConfig, inlineConfig]) {
    if (!config) continue;
    const list = Array.isArray(config)
      ? config
      : (config.donor_profiles || config.donorProfiles || config.donors || []);
    for (const item of asArray(list)) {
      if (item && typeof item === "object") profiles.push(item);
    }
  }
  return profiles;
}

function modelFamilyFromId(model) {
  const value = String(model || "").toLowerCase();
  if (value.includes("gemma")) return "gemma";
  if (value.includes("qwen")) return "qwen";
  if (value.includes("llama")) return "llama";
  if (value.includes("mistral")) return "mistral";
  if (value.includes("claude")) return "anthropic";
  return value ? "other" : "unset";
}

const startSandbox = hasFlag("start-sandbox") || ["1", "true", "yes"].includes(String(process.env.ISTARA_BENCHMARK_START_SANDBOX || "").toLowerCase());
const skipSandbox = ["1", "true", "yes"].includes(String(process.env.ISTARA_BENCHMARK_SKIP_SANDBOX || "").toLowerCase());
// `--plan-only` is an ergonomic flag alias for `--mode plan-only` (benchmark
// task B0-2): it resolves the engine plan without attempting live services.
const mode = hasFlag("plan-only")
  ? "plan-only"
  : arg("mode", process.env.ISTARA_BENCHMARK_MODE || "probe");
const runId = arg("run-id", makeRunId());
const acceptanceProfileRaw = String(
  arg("acceptance-profile", process.env.ISTARA_BENCHMARK_ACCEPTANCE_PROFILE || "combined") || "combined",
).trim().toLowerCase();
const acceptanceProfile = normalizeAcceptanceProfile(acceptanceProfileRaw);
if (acceptanceProfileRaw !== acceptanceProfile) {
  console.error(`Invalid --acceptance-profile=${acceptanceProfileRaw}; expected one of provider|petals|combined.`);
  process.exit(2);
}
const providerAcceptanceSelected = acceptanceProfile !== "petals";
const petalsAcceptanceSelected = acceptanceProfile !== "provider";
const workload = benchmarkWorkloadForProfile(acceptanceProfile);

// ── Benchmark engine plumbing (benchmark task B0-2) ────────────────────────
// `--engine pi|legacy|both` selects the AgenticDispatcher engine per request via
// the `x-istara-agent-engine` header, threaded into every IstaraApiClient below.
// `both` is a planning concept (the paired Python runner drives real pairing);
// a single live client carries exactly one engine.
const AGENT_ENGINE_HEADER = "x-istara-agent-engine";
function resolveBenchmarkEngines(raw) {
  const value = String(raw || "").trim().toLowerCase();
  if (!value) return [];
  if (value === "both") return ["legacy", "pi"];
  if (value === "pi" || value === "legacy") return [value];
  console.error(`Invalid --engine=${raw}; expected one of pi|legacy|both.`);
  process.exit(2);
}
const benchmarkEngines = resolveBenchmarkEngines(
  arg("engine", process.env.ISTARA_BENCHMARK_ENGINE || ""),
);
// One live client carries a single engine header; `both` defers pairing to the
// Python runner, so live mode leaves the header unset (dispatcher default).
const benchmarkAgentEngine = benchmarkEngines.length === 1 ? benchmarkEngines[0] : "";
const donorTopology = String(arg("donor-topology", process.env.ISTARA_BENCHMARK_DONOR_TOPOLOGY || "") || "").trim().toLowerCase();
const useLocalThreeModelDonorTopology = THREE_MODEL_DONOR_TOPOLOGY_ALIASES.has(donorTopology);
const dockerRunnerMode = boolEnv("ISTARA_BENCHMARK_DOCKER_RUNNER", false);
const resultsRoot = resolve(arg("results-dir", process.env.ISTARA_BENCHMARK_RESULTS_DIR || join(__dirname, ".results")));
const externalConnectionStringMode = boolEnv("ISTARA_BENCHMARK_EXTERNAL_CONNECTION_STRINGS", false)
  || boolEnv("ISTARA_BENCHMARK_INTERACTIVE_CONNECTION_STRINGS", false)
  || Boolean(
    process.env.ISTARA_BENCHMARK_CONNECTION_STRINGS_FILE
      || process.env.ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRINGS
      || process.env.ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRING
      || process.env.ISTARA_BENCHMARK_USER_INVITE_CONNECTION_STRINGS
      || process.env.ISTARA_BENCHMARK_USER_INVITE_CONNECTION_STRING,
  );
const requireComputeDonation = boolEnv(
  "ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION",
  petalsAcceptanceSelected && mode !== "plan-only",
);
const startClientSandboxes = boolEnv(
  "ISTARA_BENCHMARK_START_CLIENT_SANDBOXES",
  startSandbox || externalConnectionStringMode || (mode !== "plan-only" && workload.petals && requireComputeDonation),
);
let runtimeResearcherCount = intArg("researcher-count", 1);
const backendEnv = loadBackendEnv();
const liveLlmProfile = liveLlmProfileFromTestingContract();
const requireLiveChat = boolEnv("ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT", workload.chat && (requireComputeDonation || mode === "full"));
const forceDonatedChat = boolEnv("ISTARA_BENCHMARK_FORCE_DONATED_CHAT", false);
const defaultApiBase = startSandbox && !skipSandbox ? "http://localhost:18000" : "http://localhost:8000";
const defaultFrontendUrl = startSandbox && !skipSandbox ? "http://localhost:13000" : "http://localhost:3000";
const apiBase = (process.env.ISTARA_API_URL || defaultApiBase).replace(/\/$/, "");
const frontendUrl = (process.env.ISTARA_FRONTEND_URL || defaultFrontendUrl).replace(/\/$/, "");
const benchmarkAdminUsername = process.env.ISTARA_BENCHMARK_ADMIN_USERNAME || process.env.ISTARA_ADMIN_USERNAME || process.env.ADMIN_USERNAME || "admin";
const benchmarkAdminPassword = (
  process.env.ISTARA_BENCHMARK_ADMIN_PASSWORD ||
  process.env.ISTARA_ADMIN_PASSWORD ||
  process.env.ADMIN_PASSWORD ||
  (startSandbox && !skipSandbox ? "IstaraBenchmarkAdmin123!" : "")
).trim();
const benchmarkTeamMode = (
  process.env.ISTARA_BENCHMARK_TEAM_MODE ||
  (startSandbox && !skipSandbox ? "true" : "")
).trim();
const freshSandbox = !["0", "false", "no"].includes(
  String(process.env.ISTARA_BENCHMARK_FRESH_SANDBOX ?? "1").toLowerCase(),
);
const backgroundAgentsDisabled = (
  process.env.ISTARA_BENCHMARK_DISABLE_BACKGROUND_AGENTS ||
  (mode === "probe" ? "true" : "false")
).trim();
const benchmarkNetworkToken = (
  process.env.ISTARA_NETWORK_ACCESS_TOKEN ||
  process.env.NETWORK_ACCESS_TOKEN ||
  process.env.ISTARA_BENCHMARK_NETWORK_ACCESS_TOKEN ||
  (requireComputeDonation && startSandbox && !skipSandbox ? `ruben-${randomBytes(24).toString("base64url")}` : "") ||
  ""
).trim();
const configuredLmStudioHost = (
  liveLlmProfile.baseUrl ||
  configuredValue(backendEnv, "LMSTUDIO_HOST", "http://host.docker.internal:1234")
).trim();
const configuredLmStudioHostSource = liveLlmProfile.baseUrl
  ? liveLlmProfile.baseUrlSource
  : backendEnv.__sources?.LMSTUDIO_HOST || "default";
const relayLlmHostRaw = (
  process.env.ISTARA_BENCHMARK_RELAY_LLM_HOST ||
  configuredLmStudioHost
).trim();
const relayLlmHostSource = process.env.ISTARA_BENCHMARK_RELAY_LLM_HOST
  ? "ISTARA_BENCHMARK_RELAY_LLM_HOST"
  : configuredLmStudioHostSource;
const relayLlmHostForContainer = replaceLocalhostForContainer(relayLlmHostRaw);
const explicitRelayLlmProvider = (process.env.ISTARA_BENCHMARK_RELAY_LLM_PROVIDER || "").trim();
const relayLlmProvider = inferProviderType(explicitRelayLlmProvider || null, relayLlmHostForContainer);
const relayLlmProviderSource = explicitRelayLlmProvider
  ? "ISTARA_BENCHMARK_RELAY_LLM_PROVIDER"
  : liveLlmProfile.baseUrl
    ? "inferred-from-testing-live-llm-base-url"
    : "inferred-from-relay-host";
const relayLlmHost = stripOpenAIPathForNativeLMStudio(relayLlmHostForContainer, relayLlmProvider);
const relayLlmHostNormalized = relayLlmHost !== relayLlmHostForContainer;
const relayLlmModel = (
  process.env.ISTARA_BENCHMARK_RELAY_LLM_MODEL ||
  liveLlmProfile.model ||
  configuredValue(backendEnv, "LMSTUDIO_MODEL", "default") ||
  "default"
).trim();
const relayLlmModelSource = process.env.ISTARA_BENCHMARK_RELAY_LLM_MODEL
  ? "ISTARA_BENCHMARK_RELAY_LLM_MODEL"
  : liveLlmProfile.modelSource;
const relayLlmApiKey = (
  process.env.ISTARA_BENCHMARK_RELAY_LLM_API_KEY ||
  liveLlmProfile.apiKey ||
  configuredValue(backendEnv, "LMSTUDIO_API_KEY", "")
).trim();
const relayLlmApiKeySource = process.env.ISTARA_BENCHMARK_RELAY_LLM_API_KEY
  ? "ISTARA_BENCHMARK_RELAY_LLM_API_KEY"
  : liveLlmProfile.apiKey
    ? liveLlmProfile.apiKeySource
    : backendEnv.__sources?.LMSTUDIO_API_KEY || "unset";

function profileValue(profile, keys) {
  for (const key of keys) {
    const value = profile?.[key];
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
  }
  return "";
}

function localThreeModelDonorPreset(index) {
  if (!useLocalThreeModelDonorTopology) return null;
  if (index === 1) {
    if (dockerRunnerMode) {
      return {
        id: "donor-1-gemma4",
        provider: "llamacpp",
        host: "http://donor-gemma:8080",
        model: process.env.ISTARA_BENCHMARK_DONOR_GEMMA_MODEL || PRIMARY_TEST_MODEL,
      };
    }
    return {
      id: "donor-1-gemma4",
      provider: "lmstudio",
      model: relayLlmModel || PRIMARY_TEST_MODEL,
    };
  }
  if (index === 2) {
    return {
      id: "sim-qwen35-4b",
      model_server: "llamacpp",
      model_server_container: "istara-donor-qwen35-4b",
      model_server_port: 18112,
      model_file: firstExistingPath(
        process.env.ISTARA_BENCHMARK_QWEN_GGUF,
        join(benchmarkModelRoot, "qwen3.5-4b-q4_k_m", "Qwen3.5-4B-Q4_K_M.gguf"),
      ),
      model: "Qwen3.5-4B-Q4_K_M.gguf",
      context_length: 12288,
      reasoning: "off",
    };
  }
  if (index === 3) {
    return {
      id: "sim-gemma4-e2b",
      model_server: "llamacpp",
      model_server_container: "istara-donor-gemma4-e2b",
      model_server_port: 18113,
      model_file: firstExistingPath(
        process.env.ISTARA_BENCHMARK_GEMMA_E2B_GGUF,
        join(benchmarkModelRoot, "gemma-4-e2b-it-q4_k_m", "gemma-4-E2B-it-Q4_K_M.gguf"),
        join(repoRoot, "LLMs", "quantized_models", "gemma-4-e2b-it-istara-ux-research", "gemma-4-e2b-it-istara-ux-research-Q4_K_M.gguf"),
      ),
      model: "gemma-4-E2B-it-Q4_K_M.gguf",
      context_length: 12288,
      reasoning: "off",
    };
  }
  return null;
}

function normalizeDonorProfile(rawProfile, index, { required = true, defaultKind = "" } = {}) {
  const raw = {
    ...(localThreeModelDonorPreset(index) || {}),
    ...(rawProfile || {}),
  };
  const envId = envDonorValue(index, ["ID", "NAME", "LABEL"]);
  const envHost = envDonorValue(index, ["LLM_HOST", "HOST", "BASE_URL"]);
  const envProvider = envDonorValue(index, ["LLM_PROVIDER", "PROVIDER"]);
  const envModel = envDonorValue(index, ["LLM_MODEL", "MODEL"]);
  const envApiKey = envDonorValue(index, ["LLM_API_KEY", "API_KEY"]);
  const envApiKeyName = envDonorValue(index, ["LLM_API_KEY_ENV", "API_KEY_ENV"]);
  const envConnection = envDonorValue(index, ["CONNECTION_STRING", "COMPUTE_CONNECTION_STRING"]);
  const isFirstLegacyDefault = index === 1 && !defaultKind;
  const isQwenDefault = defaultKind === "qwen";
  const profileProvider = profileValue(raw, ["provider", "llm_provider", "llmProvider"]);

  const id = firstNonEmpty(
    envId.value,
    raw.id,
    raw.name,
    isQwenDefault ? `donor-${index}-qwen35-4b` : "",
    isFirstLegacyDefault ? "donor-1-gemma4" : "",
    `donor-${index}`,
  ).replace(/[^a-z0-9_-]+/gi, "-").toLowerCase();
  const rawHost = firstNonEmpty(
    envHost.value,
    profileValue(raw, ["llm_host", "llmHost", "host", "base_url", "baseUrl"]),
    isQwenDefault ? process.env.ISTARA_BENCHMARK_QWEN_LLM_HOST : "",
    isFirstLegacyDefault ? relayLlmHostRaw : "",
  );
  const hostForContainer = replaceLocalhostForContainer(rawHost);
  const providerRaw = firstNonEmpty(
    envProvider.value,
    profileProvider,
    isQwenDefault ? (process.env.ISTARA_BENCHMARK_QWEN_LLM_PROVIDER || "lmstudio") : "",
    isFirstLegacyDefault ? relayLlmProvider : "",
  );
  const provider = inferProviderType(providerRaw || null, hostForContainer);
  const host = stripOpenAIPathForNativeLMStudio(hostForContainer, provider);
  const apiKeyEnvName = firstNonEmpty(
    envApiKeyName.value,
    profileValue(raw, ["api_key_env", "apiKeyEnv", "llm_api_key_env", "llmApiKeyEnv"]),
    isQwenDefault ? process.env.ISTARA_BENCHMARK_QWEN_LLM_API_KEY_ENV : "",
  );
  const apiKeyFromNamedEnv = apiKeyEnvName ? String(process.env[apiKeyEnvName] || "").trim() : "";
  const apiKey = firstNonEmpty(
    envApiKey.value,
    apiKeyFromNamedEnv,
    profileValue(raw, ["api_key", "apiKey", "llm_api_key", "llmApiKey"]),
    isQwenDefault ? process.env.ISTARA_BENCHMARK_QWEN_LLM_API_KEY : "",
    isFirstLegacyDefault ? relayLlmApiKey : "",
  );
  const model = firstNonEmpty(
    envModel.value,
    profileValue(raw, ["model", "llm_model", "llmModel", "model_id", "modelId"]),
    isQwenDefault ? (process.env.ISTARA_BENCHMARK_QWEN_LLM_MODEL || FUTURE_QWEN_DONOR_MODEL) : "",
    isFirstLegacyDefault ? relayLlmModel : "",
    "default",
  );
  const connectionString = firstNonEmpty(
    envConnection.value,
    profileValue(raw, ["connection_string", "connectionString", "compute_connection_string", "computeConnectionString"]),
  );
  const modelSandbox = buildDonorModelSandboxConfig(raw, index, {
    donorId: id,
    model,
    runId,
  });
  const effectiveProvider = modelSandbox.requested ? modelSandbox.kind : provider;
  const effectiveHostRaw = modelSandbox.requested ? modelSandbox.hostUrl : rawHost;
  const effectiveHostForContainer = modelSandbox.requested ? modelSandbox.hostUrl : hostForContainer;
  const effectiveHost = modelSandbox.requested ? modelSandbox.hostUrl : host;
  const provisionedOnly = Boolean(raw.provisioned_only ?? raw.provisionedOnly ?? isQwenDefault);
  const disabledByConfig = raw.enabled === false || raw.disabled === true;
  const enabled = !disabledByConfig && Boolean(effectiveHost);
  const blockedReason = enabled
    ? ""
    : disabledByConfig
      ? "donor-disabled-by-config"
      : "donor-llm-endpoint-not-configured";

  return {
    id,
    index,
    required,
    enabled,
    blockedReason,
    provisionedOnly,
    provider: effectiveProvider,
    providerSource: modelSandbox.requested ? `model-sandbox:${modelSandbox.source}` : envProvider.source || (profileProvider ? "donor-profile" : isFirstLegacyDefault ? relayLlmProviderSource : isQwenDefault ? "future-qwen-profile" : providerRaw ? "configured" : "inferred"),
    hostRaw: effectiveHostRaw,
    hostForContainer: effectiveHostForContainer,
    host: effectiveHost,
    hostSource: modelSandbox.requested ? `model-sandbox:${modelSandbox.source}` : envHost.source || (rawHost ? (isFirstLegacyDefault ? relayLlmHostSource : "donor-profile") : "unset"),
    hostNormalized: effectiveHost !== effectiveHostForContainer,
    apiKey,
    apiKeySource: envApiKey.source || (apiKeyFromNamedEnv ? `env:${apiKeyEnvName}` : isFirstLegacyDefault && apiKey ? relayLlmApiKeySource : apiKey ? "donor-profile" : "unset"),
    model,
    modelSource: envModel.source || (isQwenDefault ? "future-qwen-profile" : isFirstLegacyDefault ? relayLlmModelSource : "donor-profile"),
    modelFamily: modelFamilyFromId(model),
    connectionString,
    connectionStringSource: envConnection.source || (connectionString ? "donor-profile" : "unset"),
    modelSandbox,
  };
}

function buildDonorProfiles({ donorCountOverride = null } = {}) {
  const configuredProfiles = loadConfiguredDonorProfiles();
  const requested = Number.isFinite(donorCountOverride) && donorCountOverride > 0
    ? donorCountOverride
    : intArg("donor-count", Math.max(useLocalThreeModelDonorTopology ? 3 : 1, configuredProfiles.length || 1));
  const total = Math.max(requested, configuredProfiles.length, 1);
  const profiles = [];
  for (let index = 1; index <= total; index += 1) {
    const configured = configuredProfiles[index - 1];
    const defaultKind = configured ? "" : index === 1 ? "" : "qwen";
    profiles.push(normalizeDonorProfile(configured || {}, index, {
      required: index <= requested,
      defaultKind,
    }));
  }
  return profiles;
}

function summarizeDonorProfile(profile) {
  return {
    id: profile.id,
    index: profile.index,
    required: Boolean(profile.required),
    enabled: Boolean(profile.enabled),
    blocked_reason: profile.blockedReason || "",
    provisioned_only: Boolean(profile.provisionedOnly),
    provider: profile.provider,
    provider_source: profile.providerSource,
    host: hostSummary(profile.host),
    host_source: profile.hostSource,
    host_localhost_translated_for_container: profile.hostRaw !== profile.hostForContainer,
    host_openai_path_stripped_for_native_lmstudio: Boolean(profile.hostNormalized),
    api_key_configured: Boolean(profile.apiKey),
    api_key_source: profile.apiKeySource,
    model_family: profile.modelFamily,
    model_configured: Boolean(profile.model && profile.model !== "default"),
    model_source: profile.modelSource,
    model_id_redacted: true,
    connection_string_configured: Boolean(profile.connectionString),
    connection_string_source: profile.connectionStringSource,
    model_sandbox: summarizeDonorModelSandbox(profile.modelSandbox),
  };
}

let donorProfiles = buildDonorProfiles();
const requireDistinctDonorEndpoints = boolEnv(
  "ISTARA_BENCHMARK_REQUIRE_DISTINCT_DONOR_ENDPOINTS",
  workload.petals && donorProfiles.filter((profile) => profile.required).length > 1,
);
const serverLmstudioModel = (
  process.env.ISTARA_BENCHMARK_SERVER_LMSTUDIO_MODEL ||
  relayLlmModel ||
  "default"
).trim();
const serverLlmProvider = (
  process.env.ISTARA_BENCHMARK_SERVER_LLM_PROVIDER ||
  (forceDonatedChat || relayLlmProvider === "lmstudio" || liveLlmProfile.baseUrl ? "lmstudio" : "ollama")
).trim();
const serverLmstudioHost = forceDonatedChat
  ? "http://127.0.0.1:9"
  : stripOpenAIPathForNativeLMStudio(
      replaceLocalhostForContainer(process.env.ISTARA_BENCHMARK_SERVER_LMSTUDIO_HOST || configuredLmStudioHost),
      inferProviderType(serverLlmProvider, configuredLmStudioHost),
    );
const serverOllamaHost = (
  process.env.ISTARA_BENCHMARK_SERVER_OLLAMA_HOST ||
  (forceDonatedChat ? "http://127.0.0.1:9" : "http://ollama:11434")
).trim();
const serverNeedsOllama = serverLlmProvider === "ollama" && !forceDonatedChat;
const serverLmstudioAutoLoadEnabled = (
  process.env.ISTARA_BENCHMARK_LMSTUDIO_AUTO_LOAD_ENABLED ||
  (requireComputeDonation ? "true" : "false")
).trim();
const serverLmstudioAutoContextReload = (
  process.env.ISTARA_BENCHMARK_LMSTUDIO_AUTO_CONTEXT_RELOAD ||
  (requireComputeDonation ? "true" : "false")
).trim();
const serverStrictAutoRouting = (
  process.env.ISTARA_BENCHMARK_STRICT_AUTO_ROUTING ||
  (forceDonatedChat ? "true" : "false")
).trim();
const requestedMaxChatTurns = nonNegativeIntArg("max-chat-turns", mode === "full" ? 100 : mode === "probe" ? 8 : 0);
const requestedMaxTasks = nonNegativeIntArg("max-tasks", mode === "full" ? 55 : mode === "probe" ? 8 : 0);
const requestedMaxUploads = nonNegativeIntArg("max-uploads", mode === "full" ? 140 : mode === "probe" ? 120 : 0);
const maxChatTurns = workload.chat ? requestedMaxChatTurns : 0;
const maxTasks = workload.tasks ? requestedMaxTasks : 0;
const maxUploads = workload.corpus ? requestedMaxUploads : 0;
const codingValidationEnabled = workload.coding && boolEnv(
  "ISTARA_BENCHMARK_RUN_CODING_VALIDATION",
  mode !== "plan-only",
);
const requestedCodingValidationLimit = nonNegativeIntArg("coding-limit", mode === "full" ? 50 : mode === "probe" ? 12 : 0);
const codingValidationLimit = workload.coding ? requestedCodingValidationLimit : 0;
const selfImprovementProbeEnabled = workload.selfImprovement && boolEnv("ISTARA_BENCHMARK_SELF_IMPROVEMENT_PROBE", mode !== "plan-only");
const startAutoresearchExperiment = boolEnv("ISTARA_BENCHMARK_START_AUTORESEARCH_EXPERIMENT", false) && workload.selfImprovement;
// ISTARA_BENCHMARK_CHAT_TIMEOUT_MS <= 0 (or "none") disables the client
 // abort timer entirely — reasoning-model turns run as long as they run.
 const _rawChatTimeout = process.env.ISTARA_BENCHMARK_CHAT_TIMEOUT_MS ?? "";
 const chatTimeoutMs = /^none$/i.test(_rawChatTimeout.trim())
   ? 0
   : Number.parseInt(_rawChatTimeout, 10) > 0
     ? Number.parseInt(_rawChatTimeout, 10)
     : 0;
const keepClientContainers = ["1", "true", "yes"].includes(
  String(process.env.ISTARA_BENCHMARK_KEEP_CLIENT_CONTAINERS || "").toLowerCase(),
);
const keepDonorModelContainers = ["1", "true", "yes"].includes(
  String(process.env.ISTARA_BENCHMARK_KEEP_DONOR_MODEL_CONTAINERS || "").toLowerCase(),
);
const hostManagedThreeModelRun = workload.petals && useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes && !dockerRunnerMode;
const dockerOwnedThreeModelRun = workload.petals && useLocalThreeModelDonorTopology && skipSandbox && startClientSandboxes && dockerRunnerMode;
const stopColimaAfterRun = boolEnv("ISTARA_BENCHMARK_STOP_COLIMA_AFTER_RUN", hostManagedThreeModelRun);
let colimaAutostartAttempted = false;
let colimaStartedByBenchmark = false;
const colimaStoragePolicy = (process.env.ISTARA_BENCHMARK_COLIMA_STORAGE_POLICY || "warn").trim().toLowerCase();
const enforceColimaApparentStorage = boolEnv("ISTARA_BENCHMARK_COLIMA_ENFORCE_APPARENT_STORAGE", false);
const colimaStorageBudget = {
  actualGb: floatEnv("ISTARA_BENCHMARK_COLIMA_MAX_ACTUAL_GB", 10),
  apparentGb: floatEnv("ISTARA_BENCHMARK_COLIMA_MAX_APPARENT_GB", 20),
  toleranceGb: floatEnv("ISTARA_BENCHMARK_COLIMA_STORAGE_TOLERANCE_GB", 0.25),
};
let latestColimaStorageSnapshot = null;

const logger = new BenchmarkLogger({ rootDir: resultsRoot, runId, mode });
logger.init();
const benchmarkProvenance = buildBenchmarkProvenance({
  sourceSha: process.env.ISTARA_BENCHMARK_SOURCE_SHA || resolveGitCommitWithoutGit(repoRoot),
  sourceState: process.env.ISTARA_BENCHMARK_SOURCE_STATE,
  runnerImage: process.env.ISTARA_BENCHMARK_RUNNER_IMAGE,
  runnerImageId: process.env.ISTARA_BENCHMARK_RUNNER_IMAGE_ID,
  backendImageId: process.env.ISTARA_BENCHMARK_BACKEND_IMAGE_ID,
  frontendImageId: process.env.ISTARA_BENCHMARK_FRONTEND_IMAGE_ID,
  engine: benchmarkAgentEngine,
  isolation: process.env.ISTARA_BENCHMARK_STATE_ISOLATION,
  stackProject: process.env.ISTARA_BENCHMARK_STACK_PROJECT,
  runGroup: process.env.ISTARA_BENCHMARK_RUN_GROUP,
  runOrder: process.env.ISTARA_BENCHMARK_RUN_ORDER,
  armIndex: Number.parseInt(process.env.ISTARA_BENCHMARK_ARM_INDEX || "0", 10),
  sourceSnapshotSha256: process.env.ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256,
});
logger.writeJson("run-metadata.json", {
  run_id: runId,
  mode,
  acceptance_profile: acceptanceProfile,
  provider_acceptance_selected: providerAcceptanceSelected,
  petals_acceptance_selected: petalsAcceptanceSelected,
  workload_scope: workload,
  requested_limits: {
    chat_turns: requestedMaxChatTurns,
    tasks: requestedMaxTasks,
    uploads: requestedMaxUploads,
    coding_units: requestedCodingValidationLimit,
  },
  effective_limits: {
    chat_turns: maxChatTurns,
    tasks: maxTasks,
    uploads: maxUploads,
    coding_units: codingValidationLimit,
  },
  started_at: new Date().toISOString(),
  cwd: process.cwd(),
  node: process.version,
  provenance: benchmarkProvenance,
  benchmark_registry_sha256: benchmarkRegistryHash,
  system_prompt: {
    source_path: systemPromptPath,
    version: systemPromptVersion,
    sha256: systemPromptHash,
    bytes: Buffer.byteLength(systemPromptContent, "utf8"),
  },
});
logger.writeText("system-prompt.md", systemPromptContent);
logger.writeJson("benchmark-registry-snapshot.json", benchmarkRegistry);
logger.action("system_prompt.loaded", {
  source_path: systemPromptPath,
  version: systemPromptVersion,
  sha256: systemPromptHash,
  bytes: Buffer.byteLength(systemPromptContent, "utf8"),
});
for (const warning of startupConfigWarnings) {
  logger.action("config.warning", warning);
}
logger.action("llm.config.sources", {
  acceptance_profile: acceptanceProfile,
  provider_acceptance_selected: providerAcceptanceSelected,
  petals_acceptance_selected: petalsAcceptanceSelected,
  relay_provider: relayLlmProvider,
  relay_provider_source: relayLlmProviderSource,
  live_base_url_configured: Boolean(liveLlmProfile.baseUrl),
  live_base_url_key: liveLlmProfile.baseUrlKey || "unset",
  live_base_url_source: liveLlmProfile.baseUrlSource,
  live_env_files_with_relevant_keys: liveLlmProfile.loadedEnvFiles,
  relay_host_source: relayLlmHostSource,
  relay_host: hostSummary(relayLlmHost),
  relay_host_localhost_translated_for_container: relayLlmHostRaw !== relayLlmHostForContainer,
  relay_host_openai_path_stripped_for_native_lmstudio: relayLlmHostNormalized,
  relay_model_source: relayLlmModelSource,
  relay_api_key_source: relayLlmApiKeySource,
  start_client_sandboxes: startClientSandboxes,
  host_managed_three_model_run: hostManagedThreeModelRun,
  docker_runner_mode: dockerRunnerMode,
  docker_owned_three_model_run: dockerOwnedThreeModelRun,
  stop_colima_after_run: stopColimaAfterRun,
  external_connection_string_mode: externalConnectionStringMode,
  researcher_count: runtimeResearcherCount,
  donor_topology: donorTopology || "manual/default",
  local_three_model_donor_topology: useLocalThreeModelDonorTopology,
  donor_count_requested: workload.petals ? donorProfiles.filter((profile) => profile.required).length : 0,
  donor_profiles: donorProfiles.map(summarizeDonorProfile),
  require_distinct_donor_endpoints: requireDistinctDonorEndpoints,
  coding_validation_enabled: codingValidationEnabled,
  coding_validation_limit: codingValidationLimit,
  self_improvement_probe_enabled: selfImprovementProbeEnabled,
  autoresearch_experiment_enabled: startAutoresearchExperiment,
  keychain_service_configured: liveLlmProfile.keychainServiceConfigured,
  keychain_service_source: liveLlmProfile.keychainServiceSource,
  model_configured: Boolean(relayLlmModel && relayLlmModel !== "default"),
  model_id_redacted: true,
  api_key_configured: Boolean(relayLlmApiKey),
  server_needs_ollama: serverNeedsOllama,
  server_lmstudio_auto_load_enabled: serverLmstudioAutoLoadEnabled,
  server_lmstudio_auto_context_reload: serverLmstudioAutoContextReload,
  server_strict_auto_routing: serverStrictAutoRouting,
  requested_limits: {
    chat_turns: requestedMaxChatTurns,
    tasks: requestedMaxTasks,
    uploads: requestedMaxUploads,
    coding_units: requestedCodingValidationLimit,
  },
  effective_limits: {
    chat_turns: maxChatTurns,
    tasks: maxTasks,
    uploads: maxUploads,
    coding_units: codingValidationLimit,
  },
});
logger.action("benchmark.registry.loaded", {
  registry_version: benchmarkRegistry.version,
  companion_suites: benchmarkRegistry.companion_suites?.map((suite) => suite.path) || [],
  live_model_profile: benchmarkRegistry.live_model_profile || {},
  agentic_eval_focus: benchmarkRegistry.agentic_eval_focus?.map((item) => item.area) || [],
  future_multi_donor_profiles: benchmarkRegistry.future_multi_donor_profiles?.map((item) => ({
    id: item.id,
    enabled_by_default: Boolean(item.enabled_by_default),
    model_download_allowed: Boolean(item.model_download_allowed),
  })) || [],
});
logger.appendReport(`# Istara Real User Benchmark Report\n\nRun ID: ${runId}\nMode: ${mode}\nStarted: ${new Date().toISOString()}\n\n`);

const blockers = [];
const unrelatedWorkflowFailures = [];
if (boolEnv("ISTARA_BENCHMARK_REQUIRE_REPRODUCIBLE_RUN", mode === "full")) {
  blockers.push(...validateBenchmarkProvenance(benchmarkProvenance));
}
let securityIntegrityBaseline = null;
const featureResults = {
  uiVisited: false,
  uiOnboarding: false,
  uploadedAndQueried: false,
  citedSources: false,
  findingsCreated: false,
  reportGenerated: false,
  loops: false,
  urlFetch: false,
  interfaces: false,
  multiDonorCompute: false,
  distinctDonorEndpoints: false,
  researcherUi: false,
  adminUiRoleContract: false,
  multiUserCollaboration: false,
  taskReviewLoop: false,
  approvedTaskFindings: false,
  interviewEvidence: false,
  interviewProcess: false,
  naturalComputeOrchestration: false,
  codingValidation: false,
  researchSpineTraceability: false,
  telemetryEvidence: false,
  reasoningBankEvidence: false,
  mementoSkillEvidence: false,
  metaHyperagentEvidence: false,
  selfImprovementGovernance: false,
  autoresearchEvidence: false,
  ragTraceabilityEvidence: false,
};

const sandbox = {
  serverAttempted: false,
  serverStarted: false,
  clientAttempted: false,
  clientStarted: false,
  relayAttempted: false,
  relayStarted: false,
  clientSandboxRequested: startClientSandboxes,
  relayExpectedCount: workload.petals ? donorProfiles.filter((profile) => profile.required).length : 0,
  relayStartedCount: 0,
  researcherExpectedCount: workload.commonWorkflow ? runtimeResearcherCount : 0,
  researcherStartedCount: 0,
  modelServerAttempted: false,
  modelServerExpectedCount: workload.petals ? donorProfiles.filter((profile) => profile.required && profile.modelSandbox?.requested).length : 0,
  modelServerStartedCount: 0,
};
const relayClientContainers = [];
const donorModelContainers = [];
const extraSensitiveLogValues = new Set();
let relayClientImageBuilt = false;
let clientDockerReady = null;

function buildScorecard(input) {
  return scoreRun({
    ...input,
    acceptanceProfile: mode === "plan-only" ? null : acceptanceProfile,
    codingValidationEnabled,
    requireComputeDonation,
    workloadScope: workload,
    unrelatedWorkflowFailures,
    connectionRevocation: input.connectionRevocation || null,
  });
}

function failClosedForHostManagedThreeModelRun() {
  if (!hostManagedThreeModelRun || mode === "plan-only") return false;
  const message = "Docker-only benchmark policy forbids the host-managed three-model topology; run the Docker wrapper against the Compose stack instead.";
  const evidence = {
    policy: "docker-only",
    host_managed_three_model_run: true,
    start_sandbox: startSandbox,
    skip_sandbox: skipSandbox,
    start_client_sandboxes: startClientSandboxes,
    api_base: apiBase,
    frontend_url: frontendUrl,
    action: "refused-before-live-services",
  };
  logger.writeJson("docker-only-policy.json", evidence);
  logger.action("benchmark.docker_only.refused", evidence);
  logger.issue({
    area: "benchmark",
    severity: "critical",
    title: "Host-managed three-model topology refused",
    detail: message,
    evidence,
  });
  blockers.push(message);
  const scorecard = buildScorecard({
    mode,
    metrics: logger.metrics,
    integrationMatrix: [],
    blockers,
    completedTasks: 0,
    chatTurns: 0,
    uploadedDocuments: 0,
    sandbox,
    featureResults,
  });
  logger.writeJson("scorecard.json", scorecard);
  logger.appendReport("The requested host-managed three-model topology was refused before any live service, model, or package operation because this benchmark is Docker-only. Use scripts/runner/docker-run.sh against the Compose stack.\n\n");
  logger.appendReport(writeScorecardMarkdown(scorecard));
  logger.finalize({ scorecard });
  process.exitCode = benchmarkExitCode({ mode, blockers });
  return true;
}

function redactForLog(value) {
  if (typeof value !== "string") return value;
  if (value.startsWith("rcl_")) return `${value.slice(0, 18)}...[redacted:${value.length}]`;
  return value.replace(/rcl_[A-Za-z0-9_.-]{24,}/g, (match) => `${match.slice(0, 18)}...[redacted:${match.length}]`);
}

function sensitiveLogValues() {
  return [
    benchmarkNetworkToken,
    liveLlmProfile.baseUrl,
    relayLlmHostRaw,
    relayLlmHostForContainer,
    relayLlmHost,
    relayLlmModel,
    relayLlmApiKey,
    ...donorProfiles.flatMap((profile) => [
      profile.hostRaw,
      profile.hostForContainer,
      profile.host,
      profile.apiKey,
      profile.connectionString,
      profile.model,
      profile.modelSandbox?.hostUrl,
      profile.modelSandbox?.hostProbeUrl,
    ]),
    configuredLmStudioHost,
    serverLmstudioHost,
    serverLmstudioModel,
    serverOllamaHost,
    ...Array.from(extraSensitiveLogValues),
  ].filter((value) => typeof value === "string" && value.length > 0 && value !== "default");
}

function sanitizeLogText(text) {
  let output = redactForLog(String(text || ""));
  for (const value of sensitiveLogValues()) {
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    output = output.replace(new RegExp(escaped, "g"), `[redacted:${value.length}]`);
  }
  output = output.replace(/Failed to load LLM '([^']+)'/g, "Failed to load LLM '[redacted-model]'");
  output = output.replace(/failed to load model \S+ on/gi, "failed to load model [redacted-model] on");
  output = output.replace(/Model load failed: \S+:/g, "Model load failed: [redacted-model]:");
  output = output.replace(/([?&](?:token|access_token|network_token)=)[^&\s'"<>]+/gi, "$1[redacted]");
  output = output.replace(/\b(Bearer\s+)[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, "$1[redacted]");
  output = output.replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, "[redacted-jwt]");
  return output;
}

function sanitizeLogPayload(value) {
  if (typeof value === "string") return sanitizeLogText(value);
  if (Array.isArray(value)) return value.map((item) => sanitizeLogPayload(item));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, sanitizeLogPayload(item)]),
    );
  }
  return value;
}

logger.setSanitizer(sanitizeLogPayload);

function redactArgForLog(value, index, args) {
  const previous = args[index - 1] || "";
  if (["--llm-host", "--llm-api-key", "--model"].includes(previous)) {
    return `[redacted-arg:${String(value || "").length}]`;
  }
  return sanitizeLogText(value);
}

function runCommand(label, command, args, options = {}) {
  const started = Date.now();
  const loggedArgs = args.map((value, index) => redactArgForLog(value, index, args));
  logger.action("command.start", { label, command, args: loggedArgs });
  const result = spawnSync(command, args, {
    cwd: options.cwd || repoRoot,
    encoding: "utf8",
    timeout: options.timeoutMs || 15 * 60 * 1000,
    env: { ...process.env, ...(options.env || {}) },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const payload = {
    label,
    command,
    args: loggedArgs,
    status: result.status,
    signal: result.signal,
    duration_ms: Date.now() - started,
    stdout: options.redactStdout
      ? `[redacted-stdout:${String(result.stdout || "").length}]`
      : sanitizeLogText(result.stdout || "").slice(-12000),
    stderr: options.redactStderr
      ? `[redacted-stderr:${String(result.stderr || "").length}]`
      : sanitizeLogText(result.stderr || "").slice(-12000),
    error: sanitizeLogText(result.error?.message || ""),
  };
  logger.action("command.finish", payload);
  logger.writeText(`logs/${label.replace(/[^a-z0-9_-]+/gi, "-")}.log`, [
    `$ ${command} ${loggedArgs.join(" ")}`,
    "",
    "## stdout",
    payload.stdout,
    "",
    "## stderr",
    payload.stderr,
    payload.error ? `\n## error\n${payload.error}` : "",
  ].join("\n"));
  return result;
}

function pruneDanglingDockerImages(label) {
  if (!boolEnv("ISTARA_BENCHMARK_PRUNE_DANGLING_IMAGES", true)) {
    logger.action("docker.prune_dangling.skip", { label });
    return;
  }
  runCommand(`docker-prune-dangling-${label}`, "docker", ["image", "prune", "-f"], {
    timeoutMs: 5 * 60 * 1000,
  });
}

function hasExecutable(command) {
  const result = spawnSync("sh", ["-lc", `command -v ${command}`], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return result.status === 0 && Boolean(result.stdout.trim());
}

function dockerDaemonIsReady() {
  const result = spawnSync("docker", ["info", "--format", "{{.ServerVersion}}"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return {
    ok: result.status === 0,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    status: result.status,
  };
}

function formatGiB(bytes) {
  return Number((bytes / (1024 ** 3)).toFixed(2));
}

function readDuKiB(target, apparent = false) {
  if (!existsSync(target)) {
    return { ok: false, path: target, kib: 0, gib: 0, supported: true, reason: "missing" };
  }
  const attempts = apparent
    ? [["-sk", "-A", target], ["-sk", "--apparent-size", target]]
    : [["-sk", target]];
  for (const args of attempts) {
    const result = spawnSync("du", args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (result.status !== 0) continue;
    const kib = Number.parseInt(String(result.stdout || "").trim().split(/\s+/)[0], 10);
    if (Number.isFinite(kib)) {
      return {
        ok: true,
        path: target,
        kib,
        gib: formatGiB(kib * 1024),
        supported: true,
      };
    }
  }
  return { ok: false, path: target, kib: 0, gib: 0, supported: false, reason: "du-unsupported" };
}

function summarizeColimaStorage(snapshot) {
  const total = snapshot?.paths?.find((entry) => entry.name === "colima-home");
  return total
    ? {
        actual_gb: total.actual?.gib ?? null,
        apparent_gb: total.apparent?.gib ?? null,
        over_budget: snapshot.over_budget || [],
      }
    : null;
}

function captureColimaStorageSnapshot(label, { recordIssue = false } = {}) {
  const home = process.env.HOME || "";
  if (!home) return null;
  const paths = [
    { name: "colima-home", path: join(home, ".colima") },
    { name: "lima-disks", path: join(home, ".colima", "_lima", "_disks") },
    { name: "lima-colima-profile", path: join(home, ".colima", "_lima", "colima") },
  ];
  const entries = paths.map((item) => ({
    ...item,
    exists: existsSync(item.path),
    actual: readDuKiB(item.path, false),
    apparent: readDuKiB(item.path, true),
  }));
  const total = entries.find((entry) => entry.name === "colima-home");
  const overBudget = [];
  const apparentOverBudget = [];
  if (total?.actual?.ok && total.actual.gib > colimaStorageBudget.actualGb + colimaStorageBudget.toleranceGb) {
    overBudget.push({
      measure: "actual",
      path: total.path,
      observed_gb: total.actual.gib,
      budget_gb: colimaStorageBudget.actualGb,
    });
  }
  if (total?.apparent?.ok && total.apparent.gib > colimaStorageBudget.apparentGb + colimaStorageBudget.toleranceGb) {
    const apparentEntry = {
      measure: "apparent",
      path: total.path,
      observed_gb: total.apparent.gib,
      budget_gb: colimaStorageBudget.apparentGb,
      advisory: !enforceColimaApparentStorage,
      detail: "Apparent Colima size includes sparse disk image capacity; actual disk usage is the enforced cap unless ISTARA_BENCHMARK_COLIMA_ENFORCE_APPARENT_STORAGE=1.",
    };
    apparentOverBudget.push(apparentEntry);
    if (enforceColimaApparentStorage) overBudget.push(apparentEntry);
  }
  const snapshot = {
    label,
    captured_at: new Date().toISOString(),
    policy: colimaStoragePolicy,
    budgets_gb: colimaStorageBudget,
    enforce_apparent_storage: enforceColimaApparentStorage,
    paths: entries,
    over_budget: overBudget,
    apparent_over_budget: apparentOverBudget,
    remediation: overBudget.length
      ? "Use a fresh Colima profile with --root-disk 10 --disk 10, or explicitly raise ISTARA_BENCHMARK_COLIMA_MAX_*_GB for larger benchmark images."
      : "",
  };
  latestColimaStorageSnapshot = snapshot;
  logger.action("storage.colima.snapshot", snapshot);
  logger.writeJson(`storage/colima-${label.replace(/[^a-z0-9_-]+/gi, "-")}.json`, snapshot);
  if (recordIssue && overBudget.length) {
    logger.issue({
      area: "storage",
      severity: colimaStoragePolicy === "fail" ? "critical" : "medium",
      title: "Colima storage budget exceeded",
      detail: overBudget.map((item) => `${item.measure} ${item.observed_gb}GB > ${item.budget_gb}GB`).join("; "),
    });
    if (colimaStoragePolicy === "fail") {
      blockers.push(`Colima storage budget exceeded: ${overBudget.map((item) => `${item.measure} ${item.observed_gb}GB>${item.budget_gb}GB`).join(", ")}`);
    }
  }
  return snapshot;
}

function dockerHostAccessArgs() {
  return process.platform === "linux" ? ["--add-host", "host.docker.internal:host-gateway"] : [];
}

function dockerBenchmarkNetworkArgs() {
  const network = String(process.env.ISTARA_BENCHMARK_BACKEND_NETWORK || "").trim();
  return network ? ["--network", network] : [];
}

function containerReachableUrl(url) {
  return replaceLocalhostForContainer(url).replace(/\/$/, "");
}

function ensureDockerDaemon() {
  const first = dockerDaemonIsReady();
  if (first.ok) {
    logger.action("docker.daemon.ready", { server_version: first.stdout.trim() });
    return first;
  }

  logger.action("docker.daemon.unavailable", {
    status: first.status,
    stderr: first.stderr.slice(0, 800),
  });

  const allowColimaAutostart = !["0", "false", "no"].includes(
    String(process.env.ISTARA_BENCHMARK_AUTOSTART_COLIMA ?? "1").toLowerCase(),
  );
  if (!allowColimaAutostart || !hasExecutable("colima")) {
    return first;
  }

  captureColimaStorageSnapshot("before-colima-autostart", { recordIssue: true });
  const cpu = process.env.ISTARA_BENCHMARK_COLIMA_CPU || "4";
  const memory = process.env.ISTARA_BENCHMARK_COLIMA_MEMORY || "6";
  const disk = process.env.ISTARA_BENCHMARK_COLIMA_DISK || "10";
  const rootDisk = process.env.ISTARA_BENCHMARK_COLIMA_ROOT_DISK || "10";
  logger.action("colima.autostart.config", {
    cpu,
    memory_gb: memory,
    disk_gb: disk,
    root_disk_gb: rootDisk,
    storage_policy: colimaStoragePolicy,
    budgets_gb: colimaStorageBudget,
  });
  colimaAutostartAttempted = true;
  const colimaStart = runCommand("colima-start", "colima", [
    "start",
    "--cpu",
    cpu,
    "--memory",
    memory,
    "--disk",
    disk,
    "--root-disk",
    rootDisk,
    "--runtime",
    "docker",
  ], {
    timeoutMs: 15 * 60 * 1000,
  });
  colimaStartedByBenchmark = colimaStart.status === 0;
  captureColimaStorageSnapshot("after-colima-autostart", { recordIssue: true });
  const second = dockerDaemonIsReady();
  logger.action("docker.daemon.after_colima", {
    ok: second.ok,
    server_version: second.stdout.trim(),
    stderr: second.stderr.slice(0, 800),
  });
  return second;
}

function ensureClientDockerDaemon(label) {
  if (!startClientSandboxes) {
    logger.action("docker.client_daemon.skip", { label, startClientSandboxes });
    return { ok: false, skipped: true };
  }
  if (clientDockerReady) return clientDockerReady;
  clientDockerReady = ensureDockerDaemon();
  if (!clientDockerReady.ok) {
    blockers.push("Client/donor sandbox containers could not start because Docker was unavailable.");
    logger.issue({
      area: "client-install",
      severity: "critical",
      title: "Docker unavailable for client/donor sandboxes",
      detail: clientDockerReady.stderr || clientDockerReady.stdout || "docker info failed",
    });
  }
  return clientDockerReady;
}

function composeCommand() {
  const configArgs = [
    "-p",
    "istara-real-user-benchmark-server",
    "-f",
    "docker-compose.yml",
    "-f",
    "tests/real_user_benchmark/docker-compose.benchmark.yml",
    "config",
    "--services",
  ];
  const errors = [];
  const plugin = spawnSync("docker", ["compose", "version"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (plugin.status === 0) {
    const config = spawnSync("docker", ["compose", ...configArgs], {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (config.status === 0) {
      return { command: "docker", prefixArgs: ["compose"], flavor: "docker compose" };
    }
    errors.push(`docker compose config failed: ${(config.stderr || config.stdout || "").slice(0, 500)}`);
  } else {
    errors.push((plugin.stderr || plugin.stdout || "docker compose not available").slice(0, 500));
  }
  if (hasExecutable("docker-compose")) {
    const legacy = spawnSync("docker-compose", ["version"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (legacy.status === 0) {
      const config = spawnSync("docker-compose", configArgs, {
        cwd: repoRoot,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      });
      if (config.status === 0) {
        return { command: "docker-compose", prefixArgs: [], flavor: "docker-compose" };
      }
      errors.push(`docker-compose config failed: ${(config.stderr || config.stdout || "").slice(0, 500)}`);
    }
  }
  return {
    command: "",
    prefixArgs: [],
    flavor: "none",
    error: errors.join("\n").slice(0, 1200) || "No Docker Compose command found.",
  };
}

async function waitForHealth(api, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const health = await api.health();
    logger.action("health.poll", health);
    if (health.ok) return health;
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 3000));
  }
  return { ok: false, error: "Timed out waiting for /api/health" };
}

function startServerSandboxIfRequested() {
  if (!startSandbox || skipSandbox || mode === "plan-only") {
    logger.action("sandbox.server.skip", { startSandbox, skipSandbox, mode });
    return;
  }
  sandbox.serverAttempted = true;
  const model = process.env.ISTARA_BENCHMARK_LLM_MODEL || process.env.OLLAMA_MODEL || "qwen3:latest";
  const profile = process.env.ISTARA_BENCHMARK_LLM_PROFILE || "local-bounded";
  logger.action("sandbox.server.llm_profile", {
    profile,
    provider: serverLlmProvider,
    model_configured: Boolean(serverLmstudioModel),
    model_id_redacted: true,
    forceDonatedChat,
    relay_provider: relayLlmProvider,
    relay_provider_source: relayLlmProviderSource,
    relay_host: hostSummary(relayLlmHost),
    relay_host_source: relayLlmHostSource,
    relay_host_localhost_translated_for_container: relayLlmHostRaw !== relayLlmHostForContainer,
    relay_host_openai_path_stripped_for_native_lmstudio: relayLlmHostNormalized,
    relay_api_key_configured: Boolean(relayLlmApiKey),
    relay_api_key_source: relayLlmApiKeySource,
    relay_model_source: relayLlmModelSource,
    donor_profiles: donorProfiles.map(summarizeDonorProfile),
    server_needs_ollama: serverNeedsOllama,
    server_lmstudio_auto_load_enabled: serverLmstudioAutoLoadEnabled,
    server_lmstudio_auto_context_reload: serverLmstudioAutoContextReload,
    server_strict_auto_routing: serverStrictAutoRouting,
    note: "Benchmark is bounded to this single configured LLM model/profile. Sensitive endpoint and model values are redacted.",
  });
  const daemon = ensureDockerDaemon();
  let result;
  if (!daemon.ok) {
    result = { status: daemon.status || 1, stderr: daemon.stderr, stdout: daemon.stdout };
  } else {
    const compose = composeCommand();
    logger.action("docker.compose.detected", { flavor: compose.flavor, error: compose.error || "" });
    if (compose.command) {
      const composeBaseArgs = [
        ...compose.prefixArgs,
        "-p",
        "istara-real-user-benchmark-server",
        "-f",
        "docker-compose.yml",
        "-f",
        "tests/real_user_benchmark/docker-compose.benchmark.yml",
      ];
      if (freshSandbox) {
        runCommand("docker-compose-server-down", compose.command, [
          ...composeBaseArgs,
          "down",
          "--remove-orphans",
        ], {
          env: {
            ISTARA_BENCHMARK_TEAM_MODE: benchmarkTeamMode,
            ISTARA_BENCHMARK_ADMIN_USERNAME: benchmarkAdminUsername,
            ISTARA_BENCHMARK_ADMIN_PASSWORD: benchmarkAdminPassword,
            ISTARA_BENCHMARK_DISABLE_BACKGROUND_AGENTS: backgroundAgentsDisabled,
            NETWORK_ACCESS_TOKEN: benchmarkNetworkToken,
            ISTARA_BENCHMARK_SERVER_LLM_PROVIDER: serverLlmProvider,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_HOST: serverLmstudioHost,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_MODEL: serverLmstudioModel,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_API_KEY: forceDonatedChat ? "" : relayLlmApiKey,
            ISTARA_BENCHMARK_LMSTUDIO_AUTO_LOAD_ENABLED: serverLmstudioAutoLoadEnabled,
            ISTARA_BENCHMARK_LMSTUDIO_AUTO_CONTEXT_RELOAD: serverLmstudioAutoContextReload,
            ISTARA_BENCHMARK_STRICT_AUTO_ROUTING: serverStrictAutoRouting,
            ISTARA_BENCHMARK_SERVER_OLLAMA_HOST: serverOllamaHost,
          },
          timeoutMs: 5 * 60 * 1000,
        });
        for (const volumeName of [
          "istara-real-user-benchmark-server_istara_benchmark_backend_data",
          "istara-real-user-benchmark-server_istara_benchmark_watch",
        ]) {
          runCommand(`docker-volume-rm-${volumeName}`, "docker", ["volume", "rm", volumeName], {
            timeoutMs: 60 * 1000,
          });
        }
      }
      const composeArgs = [
        ...composeBaseArgs,
        "up",
        "-d",
        "--build",
        ...(serverNeedsOllama ? [] : ["--no-deps"]),
        "backend",
        "frontend",
      ];
      result = runCommand(
        "docker-compose-server-up",
        compose.command,
        composeArgs,
        {
          env: {
            OLLAMA_MODEL: model,
            ISTARA_FIXED_LLM_TEST_MODEL: model,
            ISTARA_BENCHMARK_TEAM_MODE: benchmarkTeamMode,
            ISTARA_BENCHMARK_ADMIN_USERNAME: benchmarkAdminUsername,
            ISTARA_BENCHMARK_ADMIN_PASSWORD: benchmarkAdminPassword,
            ISTARA_BENCHMARK_DISABLE_BACKGROUND_AGENTS: backgroundAgentsDisabled,
            NETWORK_ACCESS_TOKEN: benchmarkNetworkToken,
            ISTARA_BENCHMARK_SERVER_LLM_PROVIDER: serverLlmProvider,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_HOST: serverLmstudioHost,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_MODEL: serverLmstudioModel,
            ISTARA_BENCHMARK_SERVER_LMSTUDIO_API_KEY: forceDonatedChat ? "" : relayLlmApiKey,
            ISTARA_BENCHMARK_LMSTUDIO_AUTO_LOAD_ENABLED: serverLmstudioAutoLoadEnabled,
            ISTARA_BENCHMARK_LMSTUDIO_AUTO_CONTEXT_RELOAD: serverLmstudioAutoContextReload,
            ISTARA_BENCHMARK_STRICT_AUTO_ROUTING: serverStrictAutoRouting,
            ISTARA_BENCHMARK_SERVER_OLLAMA_HOST: serverOllamaHost,
          },
          timeoutMs: 25 * 60 * 1000,
        },
      );
      if (result.status === 0) {
        pruneDanglingDockerImages("server-compose-build");
      }
    } else {
      logger.action("docker.compose.unavailable", { error: compose.error || "" });
      result = startServerSandboxWithDocker(model);
    }
  }
  sandbox.serverStarted = result.status === 0;
  if (!sandbox.serverStarted) {
    blockers.push("Server sandbox did not start successfully. See logs/docker-* in the run folder.");
    logger.issue({
      area: "install",
      severity: "high",
      title: "Server sandbox start failed",
      detail: result.stderr || result.error?.message || "docker compose returned non-zero status",
    });
  }
}

function startServerSandboxWithDocker(model) {
  const network = "istara-real-user-benchmark-net";
  const commands = [
    ["docker", ["rm", "-f", "istara-benchmark-frontend", "istara-benchmark-backend", "istara-benchmark-ollama"], { allowFailure: true }],
    ["docker", ["network", "create", network], { allowFailure: true }],
    ...(freshSandbox ? [["docker", ["volume", "rm", "istara_benchmark_backend_data"], { allowFailure: true }]] : []),
    ...(serverNeedsOllama ? [["docker", ["volume", "create", "istara_benchmark_ollama"], {}]] : []),
    ["docker", ["volume", "create", "istara_benchmark_backend_data"], {}],
    ...(serverNeedsOllama ? [["docker", [
      "run",
      "-d",
      "--name",
      "istara-benchmark-ollama",
      "--network",
      network,
      "-v",
      "istara_benchmark_ollama:/root/.ollama",
      "ollama/ollama:latest",
    ], { timeoutMs: 10 * 60 * 1000 }]] : []),
    ["docker", [
      "build",
      "--build-arg",
      `INSTALL_WHISPER=${process.env.ISTARA_BENCHMARK_INSTALL_WHISPER || "false"}`,
      "-t",
      "istara-real-user-benchmark-backend",
      "backend",
    ], { timeoutMs: 25 * 60 * 1000 }],
    ["docker", [
      "run",
      "-d",
      "--name",
      "istara-benchmark-backend",
      "--network",
      network,
      ...dockerHostAccessArgs(),
      "-p",
      "18000:8000",
      "-v",
      "istara_benchmark_backend_data:/app/data",
      "-e",
      "DATABASE_URL=sqlite+aiosqlite:///./data/istara.db",
      "-e",
      "LANCE_DB_PATH=./data/lance_db",
      "-e",
      "UPLOAD_DIR=./data/uploads",
      "-e",
      "PROJECTS_DIR=./data/projects",
      "-e",
      `LLM_PROVIDER=${serverLlmProvider}`,
      "-e",
      `LMSTUDIO_AUTO_LOAD_ENABLED=${serverLmstudioAutoLoadEnabled}`,
      "-e",
      `LMSTUDIO_AUTO_CONTEXT_RELOAD=${serverLmstudioAutoContextReload}`,
      "-e",
      `STRICT_AUTO_ROUTING=${serverStrictAutoRouting}`,
      "-e",
      "LMSTUDIO_MAX_LOAD_ATTEMPTS_PER_REQUEST=1",
      "-e",
      "LLM_CAPABILITY_ACTIVE_PROBE_ENABLED=false",
      "-e",
      `LMSTUDIO_HOST=${serverLmstudioHost}`,
      "-e",
      `LMSTUDIO_MODEL=${serverLmstudioModel}`,
      "-e",
      `LMSTUDIO_API_KEY=${forceDonatedChat ? "" : relayLlmApiKey}`,
      "-e",
      `TEAM_MODE=${benchmarkTeamMode || "true"}`,
      "-e",
      `ADMIN_USERNAME=${benchmarkAdminUsername}`,
      "-e",
      `ADMIN_PASSWORD=${benchmarkAdminPassword}`,
      "-e",
      "RATE_LIMIT_ENABLED=false",
      "-e",
      "JWT_SECRET=istara-real-user-benchmark-jwt-secret",
      "-e",
      `NETWORK_ACCESS_TOKEN=${benchmarkNetworkToken}`,
      "-e",
      "CORS_ORIGINS=http://localhost:13000,http://127.0.0.1:13000",
      "-e",
      `OLLAMA_HOST=${serverOllamaHost}`,
      "-e",
      `OLLAMA_MODEL=${model}`,
      "-e",
      "AUTORESEARCH_ENABLED=false",
      "-e",
      "MCP_SERVER_ENABLED=false",
      "-e",
      `ISTARA_DISABLE_BACKGROUND_AGENTS=${backgroundAgentsDisabled}`,
      "istara-real-user-benchmark-backend",
    ], { timeoutMs: 2 * 60 * 1000 }],
    ["docker", [
      "build",
      "-t",
      "istara-real-user-benchmark-frontend",
      "--build-arg",
      "NEXT_PUBLIC_API_URL=http://localhost:18000",
      "--build-arg",
      "NEXT_PUBLIC_WS_URL=ws://localhost:18000",
      "frontend",
    ], { timeoutMs: 25 * 60 * 1000 }],
    ["docker", [
      "run",
      "-d",
      "--name",
      "istara-benchmark-frontend",
      "--network",
      network,
      "-p",
      "13000:3000",
      "-e",
      "NEXT_PUBLIC_API_URL=http://localhost:18000",
      "-e",
      "NEXT_PUBLIC_WS_URL=ws://localhost:18000",
      "istara-real-user-benchmark-frontend",
    ], { timeoutMs: 2 * 60 * 1000 }],
  ];

  let final = { status: 0 };
  for (const [command, args, options] of commands) {
    const label = `docker-manual-${args.slice(0, 3).join("-")}`.replace(/[^a-z0-9_-]+/gi, "-");
    const result = runCommand(label, command, args, options);
    if (result.status !== 0 && !options.allowFailure) {
      final = result;
      break;
    }
  }
  if (final.status === 0) {
    pruneDanglingDockerImages("server-manual-build");
  }
  return final;
}

function ensureRelayClientImage() {
  if (relayClientImageBuilt) return true;
  const daemon = ensureClientDockerDaemon("relay-client-build");
  if (!daemon.ok) return false;
  const build = runCommand("docker-build-relay-client", "docker", ["build", "-t", "istara-real-user-benchmark-relay", "relay"], {
    timeoutMs: 10 * 60 * 1000,
  });
  if (build.status !== 0) {
    blockers.push("Relay/client sandbox image did not build.");
    return false;
  }
  pruneDanglingDockerImages("relay-client-build");
  relayClientImageBuilt = true;
  return true;
}

async function waitForDonorModelEndpoint(donor, timeoutMs = 120000) {
  const config = donor?.modelSandbox;
  if (!config?.requested) return { skipped: true };
  const endpoint = config.kind === "ollama"
    ? `${config.hostProbeUrl}/api/tags`
    : `${config.hostProbeUrl}/v1/models`;
  const deadline = Date.now() + timeoutMs;
  let lastError = "";
  while (Date.now() < deadline) {
    try {
      const response = await fetch(endpoint, { signal: AbortSignal.timeout(5000) });
      const text = await response.text();
      if (response.ok) {
        logger.action("sandbox.donor_model.ready", {
          donor_id: donor.id,
          kind: config.kind,
          container_name: config.containerName,
          endpoint: config.kind,
          response_chars: text.length,
        });
        return { ok: true };
      }
      lastError = `${response.status} ${text.slice(0, 200)}`;
    } catch (error) {
      lastError = error.message;
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 3000));
  }
  return { ok: false, error: lastError || "timed out waiting for donor model endpoint" };
}

async function startDonorModelSandbox(donor) {
  const config = donor?.modelSandbox;
  if (!config?.requested || mode === "plan-only") {
    logger.action("sandbox.donor_model.skip", {
      donor_id: donor?.id || "unknown",
      requested: Boolean(config?.requested),
      mode,
    });
    return { skipped: true };
  }
  sandbox.modelServerAttempted = true;
  const validationIssues = validateDonorModelSandbox(config);
  const validation = {
    donor_id: donor.id,
    ok: validationIssues.length === 0,
    model_sandbox: summarizeDonorModelSandbox(config),
    issues: validationIssues,
  };
  logger.writeJson(`donor-model-sandbox-${donor.id}.json`, validation);
  logger.action("sandbox.donor_model.validation", validation);
  if (validationIssues.length > 0) {
    blockers.push(`Donor ${donor.id} model sandbox is not runnable: ${validationIssues.map((issue) => issue.code).join(", ")}.`);
    for (const issue of validationIssues) {
      logger.issue({
        area: "compute-donation",
        severity: issue.severity || "critical",
        title: `Donor model sandbox validation failed: ${issue.code}`,
        detail: issue.detail,
      });
    }
    return { ok: false, validation };
  }

  const daemon = ensureClientDockerDaemon(`donor-model-${donor.id}`);
  if (!daemon.ok) return { ok: false, skipped: true };
  if (keepDonorModelContainers) {
    const inspect = runCommand(`docker-inspect-donor-model-${donor.id}`, "docker", [
      "inspect",
      "-f",
      "{{.State.Running}}",
      config.containerName,
    ], {
      allowFailure: true,
      timeoutMs: 30 * 1000,
    });
    if (inspect.status === 0) {
      const alreadyRunning = String(inspect.stdout || "").trim() === "true";
      if (!alreadyRunning) {
        const start = runCommand(`docker-start-donor-model-${donor.id}`, "docker", ["start", config.containerName], {
          timeoutMs: 60 * 1000,
        });
        if (start.status !== 0) {
          blockers.push(`Donor ${donor.id} model sandbox exists but could not be started.`);
          logger.issue({
            area: "compute-donation",
            severity: "critical",
            title: "Donor model sandbox reuse failed",
            detail: sanitizeLogText(start.stderr || start.error?.message || "docker start returned non-zero status"),
          });
          return { ok: false, start_status: start.status };
        }
      }
      if (!donorModelContainers.includes(config.containerName)) donorModelContainers.push(config.containerName);
      sandbox.modelServerStartedCount += 1;
      logger.action("sandbox.donor_model.reuse", {
        donor_id: donor.id,
        container_name: config.containerName,
        already_running: alreadyRunning,
      });
      const readiness = await waitForDonorModelEndpoint(donor);
      return { ok: Boolean(readiness.ok), reused: true, readiness };
    }
  }
  if (!keepDonorModelContainers) {
    runCommand(`docker-rm-donor-model-${donor.id}`, "docker", ["rm", "-f", config.containerName], {
      allowFailure: true,
      timeoutMs: 60 * 1000,
    });
  }
  const run = runCommand(`docker-run-donor-model-${donor.id}`, "docker", dockerArgsForDonorModelSandbox(config, dockerHostAccessArgs()), {
    timeoutMs: 5 * 60 * 1000,
  });
  if (run.status !== 0) {
    blockers.push(`Donor ${donor.id} model sandbox did not start.`);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Donor model sandbox failed to start",
      detail: sanitizeLogText(run.stderr || run.error?.message || "docker run returned non-zero status"),
    });
    return { ok: false, run_status: run.status };
  }
  donorModelContainers.push(config.containerName);
  sandbox.modelServerStartedCount += 1;
  const readiness = await waitForDonorModelEndpoint(donor);
  if (!readiness.ok) {
    blockers.push(`Donor ${donor.id} model sandbox started but did not become ready.`);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Donor model sandbox readiness failed",
      detail: readiness.error || "model endpoint did not respond",
    });
  }
  return { ok: Boolean(readiness.ok), readiness };
}

function startRelayClientSandbox(connectionString, donorProfile = donorProfiles[0], donorIndex = 0) {
  const donor = donorProfile || donorProfiles[0];
  if (!startClientSandboxes || !connectionString || mode === "plan-only") {
    logger.action("sandbox.relay.skip", {
      donor_id: donor?.id || `donor-${donorIndex + 1}`,
      hasConnectionString: Boolean(connectionString),
      startClientSandboxes,
      mode,
    });
    return;
  }
  if (!donor?.enabled) {
    if (donor?.required || requireComputeDonation) {
      blockers.push(`Compute donor ${donor?.id || donorIndex + 1} could not start: ${donor?.blockedReason || "profile disabled"}.`);
      logger.issue({
        area: "compute-donation",
        severity: "critical",
        title: "Required donor profile is not runnable",
        detail: `Donor ${donor?.id || donorIndex + 1}: ${donor?.blockedReason || "profile disabled"}`,
      });
    }
    logger.action("sandbox.relay.profile_skip", {
      donor: summarizeDonorProfile(donor),
    });
    return;
  }
  sandbox.relayAttempted = true;
  const decodedConnection = decodeConnectionStringPayloadUnsafe(connectionString);
  const embeddedNetworkToken = String(decodedConnection?.payload?.network_token || "").trim();
  const embeddedJwt = String(decodedConnection?.payload?.jwt || "").trim();
  if (!embeddedNetworkToken && !embeddedJwt) {
    if (requireComputeDonation) {
      blockers.push("Compute donation was required, but no network access token was available for relay authentication.");
      logger.issue({
        area: "compute-donation",
        severity: "critical",
        title: "Missing network access token for required compute donation",
        detail: "Relay connections to /ws/relay require either a network token or JWT. The compute donation string did not include one.",
      });
    }
    logger.action("sandbox.relay.skip", {
      donor_id: donor.id,
      connection_string_kind: decodedConnection?.payload?.kind || "",
      reason: "Compute donation relay auth was unavailable. Generate a fresh compute donation string from a server with NETWORK_ACCESS_TOKEN configured or let the current server auto-provision one before generation.",
    });
    return;
  }
  if (!ensureRelayClientImage()) return;
  const containerName = `istara-rub-relay-${runId}-${donor.id}`.replace(/[^a-z0-9_.-]+/gi, "-").slice(0, 120);
  const relayNetwork = String(process.env.ISTARA_BENCHMARK_BACKEND_NETWORK || "").trim();
  rememberConnectionStringSensitiveValues(connectionString);
  const relayConnection = rewriteRelayConnectionStringForContainer(connectionString);
  rememberConnectionStringSensitiveValues(relayConnection.connectionString);
  const relayBootstrapScript = [
    "mkdir -p \"$HOME/.istara\"",
    "node -e 'const fs=require(\"fs\"); const cfg={connection_string:process.env.ISTARA_CONNECTION_STRING, provider:process.env.ISTARA_RELAY_LLM_PROVIDER, llm_host:process.env.ISTARA_RELAY_LLM_HOST, llm_api_key:process.env.ISTARA_RELAY_LLM_API_KEY}; fs.writeFileSync(`${process.env.HOME}/.istara/config.json`, JSON.stringify(cfg));'",
    "exec node index.mjs --heartbeat-interval \"${ISTARA_RELAY_HEARTBEAT_INTERVAL:-10}\"",
  ].join(" && ");
  logger.action("sandbox.relay.start", {
    donor: summarizeDonorProfile(donor),
    container_name: containerName,
    connection_string_present: Boolean(connectionString),
    connection_string_has_embedded_network_token: Boolean(embeddedNetworkToken),
    connection_string_has_embedded_jwt: Boolean(embeddedJwt),
    connection_string_rewritten_for_container: Boolean(relayConnection.rewritten),
    connection_string_needs_container_reachable_url: Boolean(relayConnection.needsContainerReachableUrl),
    docker_network: relayNetwork || null,
    rewrite_evidence: relayConnection.rewritten
      ? {
          before: relayConnection.before,
          after: relayConnection.after,
        }
      : relayConnection.needsContainerReachableUrl
        ? {
            before: relayConnection.before,
            suggested: relayConnection.after,
            note: relayConnection.note,
          }
      : null,
  });
  if (relayConnection.needsContainerReachableUrl) {
    blockers.push(`Relay/client sandbox for donor ${donor.id} received a signed connection string with localhost URLs that Docker cannot use.`);
    logger.issue({
      area: "connection-string",
      severity: "critical",
      title: "Relay connection string is not Docker-reachable",
      detail: relayConnection.note,
    });
    return;
  }
  const run = runCommand(`docker-run-relay-client-${donor.id}`, "docker", [
    "run",
    "-d",
    "--name",
    containerName,
    ...dockerHostAccessArgs(),
    ...dockerBenchmarkNetworkArgs(),
    "-e",
    "ISTARA_CONNECTION_STRING",
    "-e",
    "ISTARA_RELAY_LLM_PROVIDER",
    "-e",
    "ISTARA_RELAY_LLM_HOST",
    "-e",
    "ISTARA_RELAY_LLM_API_KEY",
    "-e",
    "ISTARA_RELAY_HEARTBEAT_INTERVAL",
    "istara-real-user-benchmark-relay",
    "sh",
    "-lc",
    relayBootstrapScript,
  ], {
    env: {
      ISTARA_CONNECTION_STRING: relayConnection.connectionString,
      ISTARA_RELAY_LLM_PROVIDER: donor.provider,
      ISTARA_RELAY_LLM_HOST: donor.host,
      ISTARA_RELAY_LLM_API_KEY: donor.apiKey,
      ISTARA_RELAY_HEARTBEAT_INTERVAL: process.env.ISTARA_BENCHMARK_RELAY_HEARTBEAT_INTERVAL || "10",
    },
    timeoutMs: 2 * 60 * 1000,
  });
  if (run.status === 0) {
    sandbox.relayStarted = true;
    relayClientContainers.push(containerName);
    sandbox.relayStartedCount += 1;
  }
  if (run.status !== 0) {
    blockers.push(`Relay/client sandbox did not start successfully for donor ${donor.id}.`);
    logger.issue({
      area: "client-install",
      severity: "medium",
      title: "Relay client sandbox failed to start",
      detail: run.stderr || run.error?.message || "docker run returned non-zero status",
    });
  }
}

function startInviteClientSandbox(connectionString, index = 0) {
  if (!startClientSandboxes || !connectionString || mode === "plan-only") {
    logger.action("sandbox.invite_client.skip", {
      index,
      hasConnectionString: Boolean(connectionString),
      startClientSandboxes,
      mode,
    });
    return;
  }
  const daemon = ensureClientDockerDaemon("invite-client");
  if (!daemon.ok) return;
  sandbox.clientAttempted = true;
  const script = `
const decodePayload = (connectionString) => {
  const body = connectionString.replace(/^rcl_/, "");
  const payload = body.split(".")[0] || "";
  const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
  return JSON.parse(Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));
};
const post = async (serverUrl, path, body, headers = {}) => {
  const result = await postResult(serverUrl, path, body, headers);
  if (!result.ok) throw new Error(path + " " + result.status + " " + String(result.text).slice(0, 300));
  return result.data;
};
const postResult = async (serverUrl, path, body, headers = {}) => {
  const response = await fetch(serverUrl + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let data = text;
  try { data = text ? JSON.parse(text) : {}; } catch {}
  return { ok: response.ok, status: response.status, data, text };
};
const main = async () => {
  const connectionString = process.env.ISTARA_CONNECTION_STRING || "";
  const payload = decodePayload(connectionString);
  const serverUrl = (process.env.ISTARA_CLIENT_SERVER_URL || payload.server_url || "").replace(/\\/$/, "");
  const networkAccessToken = process.env.ISTARA_CLIENT_NETWORK_ACCESS_TOKEN || "";
  const networkHeaders = networkAccessToken ? { "X-Access-Token": networkAccessToken } : {};
  const username = process.env.ISTARA_CLIENT_USERNAME || "maya-client";
  const password = process.env.ISTARA_CLIENT_PASSWORD || "IstaraBenchmarkClient123!";
  const email = process.env.ISTARA_CLIENT_EMAIL || username + "@benchmark.istara.local";
  const validation = await post(serverUrl, "/api/connections/validate", { connection_string: connectionString }, networkHeaders);
  if (!validation.valid) throw new Error("Connection string validation failed: " + JSON.stringify(validation));
  const redemptionAttempt = await postResult(serverUrl, "/api/connections/redeem", {
    connection_string: connectionString,
    username,
    password,
    email,
    display_name: "Maya Rodrigues Client Sandbox",
  }, networkHeaders);
  let redemption = redemptionAttempt.data;
  let reusedExistingUser = false;
  if (!redemptionAttempt.ok) {
    const conflict = redemptionAttempt.status === 409 && /already exists/i.test(String(redemptionAttempt.text || ""));
    if (!conflict) {
      throw new Error("/api/connections/redeem " + redemptionAttempt.status + " " + String(redemptionAttempt.text).slice(0, 300));
    }
    const login = await post(serverUrl, "/api/auth/login", { username, password }, networkHeaders);
    redemption = {
      token: login.token || login.access_token || "",
      user: login.user || {},
    };
    reusedExistingUser = true;
  }
  const meResponse = await fetch(serverUrl + "/api/auth/me", {
    headers: { Authorization: "Bearer " + redemption.token, ...networkHeaders },
  });
  const meText = await meResponse.text();
  let me = meText;
  try { me = meText ? JSON.parse(meText) : {}; } catch {}
  if (!meResponse.ok) throw new Error("/api/auth/me " + meResponse.status + " " + String(meText).slice(0, 300));
  console.log(JSON.stringify({
    ok: true,
    server_url: serverUrl,
    token_type: validation.token_type,
    username,
    user_id: redemption.user && redemption.user.id,
    role: redemption.user && redemption.user.role,
    me_id: me.id,
    me_role: me.role,
    reused_existing_user: reusedExistingUser,
  }));
};
main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: error.message }));
  process.exit(1);
});
`;
  const clientUsername = `researcher_${index + 1}`;
  const clientPassword = process.env[`ISTARA_BENCHMARK_CLIENT_${index + 1}_PASSWORD`]
    || process.env.ISTARA_BENCHMARK_CLIENT_PASSWORD
    || "istara123";
  const clientEmail = process.env[`ISTARA_BENCHMARK_CLIENT_${index + 1}_EMAIL`]
    || `${clientUsername}@istara.test`;
  const result = runCommand(`docker-run-user-invite-client-${index + 1}`, "docker", [
    "run",
    "--rm",
    ...dockerHostAccessArgs(),
    ...dockerBenchmarkNetworkArgs(),
    "-e",
    "ISTARA_CONNECTION_STRING",
    "-e",
    "ISTARA_CLIENT_SERVER_URL",
    "-e",
    "ISTARA_CLIENT_USERNAME",
    "-e",
    "ISTARA_CLIENT_PASSWORD",
    "-e",
    "ISTARA_CLIENT_EMAIL",
    "-e",
    "ISTARA_CLIENT_NETWORK_ACCESS_TOKEN",
    "node:24-slim",
    "node",
    "-e",
    script,
  ], {
    env: {
      ISTARA_CONNECTION_STRING: connectionString,
      ISTARA_CLIENT_SERVER_URL: process.env.ISTARA_BENCHMARK_CLIENT_SERVER_URL || containerReachableUrl(apiBase),
      ISTARA_CLIENT_USERNAME: process.env[`ISTARA_BENCHMARK_CLIENT_${index + 1}_USERNAME`] || clientUsername,
      ISTARA_CLIENT_PASSWORD: clientPassword,
      ISTARA_CLIENT_EMAIL: clientEmail,
      ISTARA_CLIENT_NETWORK_ACCESS_TOKEN: benchmarkNetworkToken,
    },
    timeoutMs: 3 * 60 * 1000,
  });
  sandbox.clientStarted = sandbox.clientStarted || result.status === 0;
  if (result.status === 0) sandbox.researcherStartedCount += 1;
  let parsed = null;
  const lines = String(result.stdout || "").trim().split(/\r?\n/).filter(Boolean);
  try {
    parsed = lines.length ? JSON.parse(lines.at(-1)) : null;
  } catch {}
  logger.writeJson("connection-client-results.json", {
    attempted: true,
    index,
    ok: result.status === 0,
    result: parsed,
    stderr_preview: String(result.stderr || "").slice(-1000),
  });
  if (result.status !== 0) {
    blockers.push("User invite client sandbox did not redeem the connection string successfully.");
    logger.issue({
      area: "client-install",
      severity: "high",
      title: "User invite client sandbox failed",
      detail: parsed?.error || result.stderr || result.error?.message || "docker run returned non-zero status",
    });
  }
  return {
    ok: result.status === 0,
    username: process.env[`ISTARA_BENCHMARK_CLIENT_${index + 1}_USERNAME`] || clientUsername,
    password: clientPassword,
    email: clientEmail,
    parsed,
  };
}

function cleanupRelayClientSandboxes() {
  if (keepClientContainers || relayClientContainers.length === 0) return;
  for (const containerName of relayClientContainers) {
    runCommand(`docker-logs-${containerName}`, "docker", ["logs", containerName], {
      timeoutMs: 30 * 1000,
    });
    runCommand(`docker-rm-${containerName}`, "docker", ["rm", "-f", containerName], {
      timeoutMs: 30 * 1000,
    });
  }
}

function cleanupDonorModelSandboxes() {
  if (keepDonorModelContainers || donorModelContainers.length === 0) return;
  for (const containerName of donorModelContainers) {
    runCommand(`docker-logs-${containerName}`, "docker", ["logs", containerName], {
      timeoutMs: 30 * 1000,
    });
    runCommand(`docker-rm-${containerName}`, "docker", ["rm", "-f", containerName], {
      timeoutMs: 30 * 1000,
    });
  }
}

function stopColimaIfRequested(label) {
  const usedBenchmarkColimaResources = (
    colimaAutostartAttempted ||
    relayClientContainers.length > 0 ||
    donorModelContainers.length > 0
  );
  const skipReason = !stopColimaAfterRun
    ? "disabled"
    : mode === "plan-only"
      ? "plan-only"
      : keepClientContainers || keepDonorModelContainers
        ? "keep-containers-requested"
        : !usedBenchmarkColimaResources
          ? "no-benchmark-colima-resources"
          : !hasExecutable("colima")
            ? "colima-not-installed"
            : "";
  if (skipReason) {
    logger.action("colima.stop.skip", {
      label,
      reason: skipReason,
      stop_colima_after_run: stopColimaAfterRun,
      colima_autostart_attempted: colimaAutostartAttempted,
      colima_started_by_benchmark: colimaStartedByBenchmark,
      relay_client_container_count: relayClientContainers.length,
      donor_model_container_count: donorModelContainers.length,
    });
    return;
  }

  captureColimaStorageSnapshot(`before-colima-stop-${label}`, { recordIssue: true });
  const result = runCommand(`colima-stop-${label}`, "colima", ["stop"], {
    timeoutMs: 5 * 60 * 1000,
  });
  logger.action("colima.stop.result", {
    label,
    ok: result.status === 0,
    status: result.status,
    signal: result.signal,
    colima_autostart_attempted: colimaAutostartAttempted,
    colima_started_by_benchmark: colimaStartedByBenchmark,
    relay_client_container_count: relayClientContainers.length,
    donor_model_container_count: donorModelContainers.length,
    stderr: sanitizeLogText(result.stderr || "").slice(-800),
  });
  captureColimaStorageSnapshot(`after-colima-stop-${label}`, { recordIssue: false });
}

async function preflightRelayLlmFromContainer(donorProfile = donorProfiles[0]) {
  const donor = donorProfile || donorProfiles[0];
  if (!requireComputeDonation || !startClientSandboxes || mode === "plan-only") {
    logger.action("compute.preflight.skip", {
      donor_id: donor?.id || "donor-1",
      requireComputeDonation,
      startClientSandboxes,
      mode,
    });
    return { skipped: true };
  }
  if (!donor?.enabled) {
    const preflight = {
      attempted: false,
      ok: false,
      donor: summarizeDonorProfile(donor),
      reason: donor?.blockedReason || "donor profile disabled",
    };
    logger.writeJson(`relay-llm-preflight-${donor?.id || "donor"}.json`, preflight);
    logger.action("compute.preflight.profile_skip", preflight);
    if (donor?.required) {
      blockers.push(`Required compute donor ${donor.id} has no runnable LLM endpoint.`);
      logger.issue({
        area: "compute-donation",
        severity: "critical",
        title: "Required compute donor has no LLM endpoint",
        detail: `Donor ${donor.id}: ${donor.blockedReason || "missing host"}. Provide a provisioned LM Studio/OpenAI-compatible endpoint instead of asking the benchmark to download or install a model.`,
      });
    }
    return preflight;
  }
  const daemon = ensureClientDockerDaemon(`relay-preflight-${donor.id}`);
  if (!daemon.ok) return { ok: false, skipped: true };
  const script = `
const provider = (process.env.ISTARA_RELAY_LLM_PROVIDER || "lmstudio").toLowerCase();
const host = (process.env.ISTARA_RELAY_LLM_HOST || "").replace(/\\/+$/, "");
const apiKey = process.env.ISTARA_RELAY_LLM_API_KEY || "";
const configuredModel = process.env.ISTARA_RELAY_LLM_MODEL || "";
const headers = { "Content-Type": "application/json" };
if (apiKey) headers.Authorization = "Bearer " + apiKey;
let loadAttempted = false;
let loadOk = false;
let loadError = "";
let modelCount = 0;
let configuredModelListed = null;
let selectedModelIdLength = 0;
let modelListSource = "";
let selectedQuantization = "";
let selectedQ4Evidence = false;
const redact = (value) => {
  let output = String(value || "");
  for (const secret of [host, apiKey, configuredModel].filter(Boolean)) {
    output = output.split(secret).join("[redacted]");
  }
  return output;
};
const q4EvidenceFrom = (...values) => {
  const joined = values.filter(Boolean).map((value) => String(value)).join(" ");
  return /(^|[^a-z0-9])(?:q4(?:[_\\-.][a-z0-9]+)?|4bit|4-bit|int4)([^a-z0-9]|$)/i.test(joined);
};
const openAIUrl = (suffix) => {
  const clean = suffix.replace(/^\\/+/, "");
  const parsed = new URL(host);
  const basePath = parsed.pathname.replace(/\\/+$/, "");
  if (basePath.endsWith("/v1") || basePath.endsWith("/openai")) return host + "/" + clean;
  return host + "/v1/" + clean;
};
const fetchJson = async (url, options = {}) => {
  const res = await fetch(url, { ...options, headers: { ...headers, ...(options.headers || {}) }, signal: AbortSignal.timeout(30000) });
  const text = await res.text();
  let data = text;
  try { data = text ? JSON.parse(text) : {}; } catch {}
  if (!res.ok) throw new Error(String(res.status) + " " + String(text).slice(0, 240));
  return data;
};
const modelId = (item) => typeof item === "string" ? item : (item && (item.id || item.name || item.model || item.path)) || "";
const modelAliases = (item) => {
  const ids = [modelId(item)];
  if (Array.isArray(item?.loaded_instances)) {
    for (const instance of item.loaded_instances) {
      if (instance?.id) ids.push(String(instance.id));
    }
  }
  return Array.from(new Set(ids.filter(Boolean)));
};
const loadConfiguredModel = async (model) => {
  if (provider !== "lmstudio" || !model || model === "default") return false;
  loadAttempted = true;
  try {
    await fetchJson(host + "/api/v1/models/load", {
      method: "POST",
      body: JSON.stringify({ model, echo_load_config: true })
    });
    loadOk = true;
    return true;
  } catch (error) {
    loadError = redact(error.message);
    return false;
  }
};
const candidateModelsFor = (configured, models, rawModels) => {
  const candidates = [];
  const add = (value) => {
    const model = String(value || "").trim();
    if (model && !candidates.includes(model)) candidates.push(model);
  };
  if (configured && configured !== "default") add(configured);
  for (const raw of rawModels) {
    const aliases = modelAliases(raw);
    if (!aliases.length) continue;
    const primary = aliases[0];
    const matchesConfigured = configured
      && configured !== "default"
      && (primary === configured || aliases.includes(configured) || aliases.some((alias) => alias.startsWith(configured + ":")));
    if (matchesConfigured) {
      for (const alias of aliases) add(alias);
    }
  }
  if (configured && configured !== "default") {
    for (const model of models) {
      if (model.startsWith(configured + ":")) add(model);
    }
  }
  if (!candidates.length && models[0]) add(models[0]);
  return candidates;
};
const tinyChat = async (model) => fetchJson(openAIUrl("chat/completions"), {
  method: "POST",
  body: JSON.stringify({
    model,
    messages: [{ role: "user", content: "Reply with the exact marker BENCHMARK_DONATION_READY." }],
    temperature: 0,
    max_tokens: 32,
    stream: false
  })
});
const main = async () => {
  if (!host) throw new Error("No relay LLM host configured");
  let modelData;
  try {
    modelData = provider === "lmstudio"
      ? await fetchJson(host + "/api/v1/models")
      : provider === "ollama"
        ? await fetchJson(host + "/api/tags")
      : await fetchJson(openAIUrl("models"));
    modelListSource = provider === "lmstudio" ? "lmstudio-native" : provider === "ollama" ? "ollama-native" : "openai-compatible";
  } catch (firstError) {
    modelData = await fetchJson(openAIUrl("models"));
    modelListSource = "openai-compatible";
  }
  let rawModels = Array.isArray(modelData?.data) ? modelData.data : Array.isArray(modelData?.models) ? modelData.models : [];
  let models = Array.from(new Set(rawModels.flatMap(modelAliases).filter(Boolean)));
  if (provider === "lmstudio" && models.length === 0) {
    try {
      modelData = await fetchJson(openAIUrl("models"));
      rawModels = Array.isArray(modelData?.data) ? modelData.data : Array.isArray(modelData?.models) ? modelData.models : [];
      models = Array.from(new Set(rawModels.flatMap(modelAliases).filter(Boolean)));
      modelListSource = "openai-compatible";
    } catch {}
  }
  modelCount = models.length;
  configuredModelListed = configuredModel && configuredModel !== "default" ? models.includes(configuredModel) : null;
  const candidates = candidateModelsFor(configuredModel, models, rawModels);
  if (!candidates.length) throw new Error("No chat model available from configured relay LLM target");
  let model = "";
  let completion;
  let lastChatError = null;
  for (const candidate of candidates) {
    try {
      completion = await tinyChat(candidate);
      model = candidate;
      break;
    } catch (chatError) {
      lastChatError = chatError;
      const retryableLmStudioLoadError = /no models loaded|not loaded|load|compute error/i.test(chatError.message);
      if (
        provider === "lmstudio"
        && configuredModel
        && configuredModel !== "default"
        && candidate === configuredModel
        && retryableLmStudioLoadError
      ) {
        await loadConfiguredModel(configuredModel);
        try {
          completion = await tinyChat(candidate);
          model = candidate;
          break;
        } catch (reloadChatError) {
          lastChatError = reloadChatError;
        }
      }
    }
  }
  if (!model || !completion) throw lastChatError || new Error("No chat model candidate served the configured relay LLM target");
  selectedModelIdLength = model.length;
  const selectedRawModel = rawModels.find((item) => modelAliases(item).includes(model)) || {};
  selectedQuantization = String(
    selectedRawModel?.quantization?.name
    || selectedRawModel?.quantization
    || selectedRawModel?.details?.quantization_level
    || selectedRawModel?.metadata?.quantization
    || ""
  );
  selectedQ4Evidence = q4EvidenceFrom(selectedQuantization, model, configuredModel);
  const content = completion?.choices?.[0]?.message?.content || "";
  console.log(JSON.stringify({
    ok: true,
    provider,
    model_count: modelCount,
    configured_model_listed: configuredModelListed,
    model_list_source: modelListSource,
    selected_model: model,
    selected_model_source: model === configuredModel ? "configured" : configuredModel && model.startsWith(configuredModel + ":") ? "loaded-instance-alias" : "candidate",
    selected_model_id_length: selectedModelIdLength,
    selected_quantization_present: Boolean(selectedQuantization),
    selected_quantization_redacted: Boolean(selectedQuantization),
    selected_q4_evidence_present: selectedQ4Evidence,
    load_attempted: loadAttempted,
    load_ok: loadOk,
    load_error_present: Boolean(loadError),
    load_error_preview: loadError.slice(0, 240),
    chat_chars: content.length,
    contains_marker: /BENCHMARK_DONATION_READY/i.test(content)
  }));
};
main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: redact(error.message), model_count: modelCount, configured_model_listed: configuredModelListed, model_list_source: modelListSource, selected_model_source: configuredModel && configuredModel !== "default" ? "configured" : "first-listed", selected_model_id_length: selectedModelIdLength, selected_quantization_present: Boolean(selectedQuantization), selected_quantization_redacted: Boolean(selectedQuantization), selected_q4_evidence_present: selectedQ4Evidence, load_attempted: loadAttempted, load_ok: loadOk, load_error_present: Boolean(loadError), load_error_preview: loadError.slice(0, 240) }));
  process.exit(1);
});
`;
  const preflightArgs = [
    "run",
    "--rm",
    ...dockerHostAccessArgs(),
    ...dockerBenchmarkNetworkArgs(),
    "-e",
    "ISTARA_RELAY_LLM_PROVIDER",
    "-e",
    "ISTARA_RELAY_LLM_HOST",
    "-e",
    "ISTARA_RELAY_LLM_API_KEY",
    "-e",
    "ISTARA_RELAY_LLM_MODEL",
    "node:24-slim",
    "node",
    "-e",
    script,
  ];
  const preflightEnv = {
    ISTARA_RELAY_LLM_PROVIDER: donor.provider,
    ISTARA_RELAY_LLM_HOST: donor.host,
    ISTARA_RELAY_LLM_API_KEY: donor.apiKey,
    ISTARA_RELAY_LLM_MODEL: donor.model,
  };
  // A Compose-owned llama.cpp donor can answer /v1/models before its first
  // generation is ready. Give a cold model a bounded readiness window, but
  // never convert a persistent route/model failure into a pass.
  const preflightDeadline = Date.now() + 180 * 1000;
  let result;
  do {
    result = runCommand(`docker-run-relay-llm-preflight-${donor.id}`, "docker", preflightArgs, {
      env: preflightEnv,
      redactStdout: true,
      redactStderr: true,
      timeoutMs: 60 * 1000,
    });
    if (result.status === 0) break;
    if (Date.now() >= preflightDeadline) break;
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 3000));
  } while (Date.now() < preflightDeadline);
  let parsed = null;
  const lines = `${result.stdout || ""}\n${result.stderr || ""}`.trim().split(/\r?\n/).filter(Boolean);
  for (const line of lines.slice().reverse()) {
    try {
      parsed = JSON.parse(line);
      break;
    } catch {}
  }
  const resolvedModel = String(parsed?.selected_model || "").trim();
  if (result.status === 0 && parsed?.ok === true && resolvedModel && resolvedModel !== donor.model) {
    donor.model = resolvedModel;
    donor.modelSource = `${donor.modelSource}+preflight-served-alias`;
  }
  const loggedParsed = parsed
    ? {
        ...parsed,
        selected_model: parsed.selected_model ? "[redacted]" : parsed.selected_model,
        selected_model_redacted: Boolean(parsed.selected_model),
      }
    : parsed;
  const preflight = {
    attempted: true,
    donor: summarizeDonorProfile(donor),
    ok: result.status === 0 && parsed?.ok === true,
    result: loggedParsed,
    stderr_preview: sanitizeLogText(
      resolvedModel ? String(result.stderr || "").split(resolvedModel).join("[redacted]") : result.stderr || "",
    ).slice(-1000),
    relay_host: hostSummary(donor.host),
    relay_host_source: donor.hostSource,
    relay_provider: donor.provider,
    relay_provider_source: donor.providerSource,
    relay_host_localhost_translated_for_container: donor.hostRaw !== donor.hostForContainer,
    relay_host_openai_path_stripped_for_native_lmstudio: donor.hostNormalized,
    api_key_configured: Boolean(donor.apiKey),
    api_key_source: donor.apiKeySource,
    model_configured: Boolean(donor.model && donor.model !== "default"),
    model_source: donor.modelSource,
  };
  const q4FromPreflight = q4EvidenceFrom(
    donor.model,
    donor.modelSandbox?.quantization,
    donor.modelSandbox?.modelFile,
  );
  preflight.q4 = {
    required: Boolean(donor.modelSandbox?.requireQ4),
    configured_evidence_present: Boolean(donor.modelSandbox?.q4?.ok),
    preflight_quantization_present: Boolean(parsed?.selected_quantization_present),
    preflight_q4_evidence_present: Boolean(parsed?.selected_q4_evidence_present),
    ok: Boolean(donor.modelSandbox?.q4?.ok || q4FromPreflight.ok || parsed?.selected_q4_evidence_present),
  };
  logger.writeJson(`relay-llm-preflight-${donor.id}.json`, preflight);
  if (donor.index === 1) logger.writeJson("relay-llm-preflight.json", preflight);
  logger.action("compute.preflight.result", preflight);
  if (!preflight.ok) {
    blockers.push(`Configured relay target failed the container preflight for donor ${donor.id}.`);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Relay LLM target failed container preflight",
      detail: parsed?.error || sanitizeLogText(result.stderr || "") || "The client container could not list models and complete a tiny chat request against the configured LM Studio target.",
    });
  }
  if (preflight.ok && donor.modelSandbox?.requireQ4 && !preflight.q4.ok) {
    blockers.push(`Donor ${donor.id} did not prove Q4/4-bit quantization.`);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Donor quantization evidence missing",
      detail: "The donor model sandbox was required to prove Q4/4-bit quantization through config or provider metadata.",
    });
  }
  return preflight;
}

async function waitForRelayRegistrations(api, projectId, expectedCount = 1, timeoutMs = 90000) {
  if (!projectId) {
    return {
      ok: false,
      expected_count: expectedCount,
      nodes: [],
      stats: null,
      error: "project_id is required for compute relay registration checks",
    };
  }
  const deadline = Date.now() + timeoutMs;
  let lastStats = null;
  const statsPath = `/api/compute/stats?project_id=${encodeURIComponent(projectId)}`;
  while (Date.now() < deadline) {
    try {
      lastStats = await api.get(statsPath, { timeoutMs: 15000 });
      const nodes = Array.isArray(lastStats.nodes) ? lastStats.nodes : [];
      const relayNodes = nodes.filter((node) => ["relay", "browser"].includes(node.source));
      if (relayNodes.length >= expectedCount) {
        const evidence = relayNodes.map(summarizeRelayNode);
        logger.action("compute.relay.registered", {
          expected_count: expectedCount,
          registered_count: evidence.length,
          nodes: evidence,
        });
        return { ok: true, nodes: evidence, node: evidence[0], stats: summarizeComputeStats(lastStats) };
      }
      logger.action("compute.relay.poll", {
        total_nodes: lastStats.total_nodes,
        alive_nodes: lastStats.alive_nodes,
        expected_count: expectedCount,
        relay_nodes: relayNodes.length,
      });
    } catch (error) {
      logger.action("compute.relay.poll_error", { error: error.message });
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 3000));
  }
  const nodes = Array.isArray(lastStats?.nodes)
    ? lastStats.nodes.filter((node) => ["relay", "browser"].includes(node.source)).map(summarizeRelayNode)
    : [];
  return { ok: false, expected_count: expectedCount, nodes, stats: summarizeComputeStats(lastStats) };
}

async function waitForRelayRegistration(api, projectId, timeoutMs = 90000) {
  return waitForRelayRegistrations(api, projectId, 1, timeoutMs);
}

async function waitForHealthyRelayRoutes(api, projectId, expectedCount = 1, timeoutMs = 180000, label = "relay-health") {
  if (!projectId || expectedCount <= 0) {
    return {
      ok: false,
      label,
      expected_count: expectedCount,
      alive_relay_count: 0,
      nodes: [],
      stats: null,
      error: projectId ? "expected_count must be positive" : "project_id is required",
    };
  }
  const deadline = Date.now() + timeoutMs;
  let lastStats = null;
  while (Date.now() < deadline) {
    try {
      lastStats = summarizeComputeStats(
        await api.get(`/api/compute/stats?project_id=${encodeURIComponent(projectId)}`, { timeoutMs: 15000 }),
      );
      const aliveRelayNodes = (lastStats.nodes || []).filter((node) => ["relay", "browser"].includes(node.source) && node.alive);
      logger.action("compute.relay.health_poll", {
        label,
        expected_count: expectedCount,
        alive_relay_count: aliveRelayNodes.length,
        relay_nodes: (lastStats.nodes || []).filter((node) => ["relay", "browser"].includes(node.source)),
      });
      if (aliveRelayNodes.length >= expectedCount) {
        return {
          ok: true,
          label,
          expected_count: expectedCount,
          alive_relay_count: aliveRelayNodes.length,
          nodes: aliveRelayNodes,
          stats: lastStats,
        };
      }
    } catch (error) {
      logger.action("compute.relay.health_poll_error", { label, error: error.message });
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 5000));
  }
  const relayNodes = (lastStats?.nodes || []).filter((node) => ["relay", "browser"].includes(node.source));
  const aliveRelayNodes = relayNodes.filter((node) => node.alive);
  return {
    ok: false,
    label,
    expected_count: expectedCount,
    alive_relay_count: aliveRelayNodes.length,
    nodes: relayNodes,
    stats: lastStats,
  };
}

function expectedObservableRelayCount(profiles) {
  const enabled = profiles.filter((profile) => profile.enabled);
  if (hostManagedThreeModelRun) {
    return enabled.filter((profile) => profile.required).length;
  }
  const dedicatedDonors = enabled.filter((profile) => (
    profile.provisionedOnly
    || profile.provisioned_only
    || profile.modelSandbox?.requested
  ));
  return Math.max(1, dedicatedDonors.length || enabled.length);
}

function relayProbeModelOverride(profiles) {
  const enabled = profiles.filter((profile) => profile.enabled);
  const dedicated = enabled.find((profile) => (
    profile.model
    && (
      profile.provisionedOnly
      || profile.provisioned_only
      || profile.modelSandbox?.requested
    )
  ));
  return (dedicated?.model || enabled.find((profile) => profile.model)?.model || "").trim();
}

function summarizeRelayNode(node) {
  const capabilities = node.model_capabilities || {};
  return {
    node_id: node.node_id || "",
    source: node.source || "",
    provider_type: node.provider_type || "",
    state: node.state || "",
    serving_state: node.serving_state || "",
    health_error_present: Boolean(node.health_error),
    alive: Boolean(node.alive ?? node.is_healthy),
    loaded_model_count: Array.isArray(node.loaded_models) ? node.loaded_models.length : 0,
    capability_model_count: Object.keys(capabilities).length,
    active_requests: node.active_requests || 0,
    selected_request_count: node.selected_request_count || 0,
    served_request_count: node.served_request_count || 0,
    failed_request_count: node.failed_request_count || 0,
    last_route_kind: node.last_route_kind || "",
    last_selected_project_id: node.last_selected_project_id || "",
    last_served_project_id: node.last_served_project_id || "",
    last_selected_model: node.last_selected_model || "",
    last_served_model: node.last_served_model || "",
    score: node.score || 0,
  };
}

function summarizeComputeStats(stats) {
  const nodes = Array.isArray(stats?.nodes) ? stats.nodes : [];
  return {
    total_nodes: stats?.total_nodes,
    alive_nodes: stats?.alive_nodes,
    available_model_count: Array.isArray(stats?.available_models) ? stats.available_models.length : 0,
    request_slots_total: stats?.request_slots_total,
    request_slots_used: stats?.request_slots_used,
    request_slots_available: stats?.request_slots_available,
    nodes: nodes.map(summarizeRelayNode),
  };
}

async function readComputeStatsSummary(api, projectId, label) {
  try {
    const stats = summarizeComputeStats(
      await api.get(`/api/compute/stats?project_id=${encodeURIComponent(projectId)}`, { timeoutMs: 15000 }),
    );
    logger.action("compute.stats.snapshot", { label, stats });
    return stats;
  } catch (error) {
    logger.action("compute.stats.snapshot_error", { label, error: error.message });
    return null;
  }
}

function relayRouteDelta(beforeStats, afterStats, projectId) {
  const beforeNodes = new Map((beforeStats?.nodes || []).map((node) => [node.node_id, node]));
  const relayNodes = (afterStats?.nodes || []).filter((node) => ["relay", "browser"].includes(node.source) && node.alive);
  const selected = relayNodes.filter((node) =>
    (node.selected_request_count || 0) > (beforeNodes.get(node.node_id)?.selected_request_count || 0)
  );
  const served = relayNodes.filter((node) =>
    (node.served_request_count || 0) > (beforeNodes.get(node.node_id)?.served_request_count || 0)
    && (!node.last_served_project_id || node.last_served_project_id === projectId)
    && (!node.last_route_kind || ["chat", "stream"].includes(node.last_route_kind))
  );
  return { selected, served };
}

function captureBackendLogs(label, since = "5m") {
  if (!startSandbox || skipSandbox) return { stdout: "", stderr: "", status: 0 };
  return runCommand(`docker-logs-backend-${label}`, "docker", [
    "logs",
    "--since",
    since,
    "istara-benchmark-backend",
  ], {
    timeoutMs: 30 * 1000,
  });
}

async function verifyComputeDonation(api, projectId, { activeDonorProfiles = donorProfiles } = {}) {
  if (!requireComputeDonation) {
    logger.action("compute.donation.verify.skip", { requireComputeDonation });
    return { skipped: true };
  }
  const enabledDonorCount = activeDonorProfiles.filter((profile) => profile.enabled).length;
  const expectedRelayCount = expectedObservableRelayCount(activeDonorProfiles);
  const expectedLocalDedupedDonorCount = Math.max(0, enabledDonorCount - expectedRelayCount);
  if (enabledDonorCount === 0 || expectedRelayCount <= 0) {
    blockers.push("No runnable compute donors remained after LLM endpoint preflight.");
    const result = {
      ok: false,
      expected_donor_count: enabledDonorCount,
      expected_relay_count: expectedRelayCount,
      expected_local_deduped_donor_count: expectedLocalDedupedDonorCount,
      donor_profiles: activeDonorProfiles.map(summarizeDonorProfile),
      reason: "no-runnable-preflighted-donors",
    };
    logger.writeJson("compute-donation-results.json", result);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "No runnable donated compute donors",
      detail: "Every required donor failed or skipped the container-side LLM preflight, so the benchmark did not count donor registration as donor usage.",
    });
    return result;
  }
  const registration = await waitForRelayRegistrations(api, projectId, expectedRelayCount);
  if (!registration.ok) {
    blockers.push(`Compute donation relay registration incomplete: ${registration.nodes?.length || 0}/${expectedRelayCount} relay nodes observed.`);
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Compute donation relay did not register",
      detail: "The benchmark generated or consumed compute donation strings and started relay clients, but project-scoped /api/compute/stats did not show the expected relay/browser node count.",
    });
    logger.writeJson("compute-donation-results.json", {
      expected_donor_count: enabledDonorCount,
      expected_relay_count: expectedRelayCount,
      expected_local_deduped_donor_count: expectedLocalDedupedDonorCount,
      donor_profiles: activeDonorProfiles.map(summarizeDonorProfile),
      registration,
    });
    return { ok: false, registration };
  }

  const startedAt = Date.now();
  let chat = null;
  let chatError = "";
  let relayProbeSessionId = "";
  let relayModelOverride = "";
  let strictRoutingRestoreValue = null;
  const technicalProbeResults = [];
  const uniqueByNodeId = (items) => Array.from(
    new Map(items.filter((item) => item?.node_id).map((item) => [item.node_id, item])).values(),
  );
  try {
    if (forceDonatedChat) {
      try {
        const status = await api.get("/api/settings/status");
        strictRoutingRestoreValue = Boolean(status.strict_auto_routing);
        if (!strictRoutingRestoreValue) {
          await api.post("/api/settings/strict-routing", { enabled: true });
        }
      } catch (error) {
        logger.issue({
          area: "compute-donation",
          severity: "medium",
          title: "Could not enable strict routing for donated-compute probe",
          detail: error.message,
        });
      }
      for (const donor of activeDonorProfiles.filter((profile) => profile.enabled)) {
        const modelOverride = (donor.model && donor.model !== "default" ? donor.model : relayProbeModelOverride([donor])).trim();
        const probe = {
          donor_id: donor.id,
          model_override_configured: Boolean(modelOverride),
          model_override_id_length: modelOverride.length,
          session_id_present: false,
          response_chars: 0,
          selected_relay_node_count: 0,
          served_relay_node_count: 0,
          selected_relay_nodes: [],
          served_relay_nodes: [],
          ok: false,
          error: "",
        };
        if (!modelOverride) {
          probe.error = "No model override was available for this required donor.";
          technicalProbeResults.push(probe);
          continue;
        }
        const beforeStats = await readComputeStatsSummary(api, projectId, `before-donor-probe-${donor.id}`);
        try {
          const session = await api.post("/api/sessions", {
            project_id: projectId,
            title: `[RU-BENCH] Donated compute probe ${donor.id} ${runId}`,
            model_override: modelOverride,
            inference_preset: "lightweight",
          });
          probe.session_id_present = Boolean(session.id);
          relayProbeSessionId = relayProbeSessionId || session.id || "";
          relayModelOverride = relayModelOverride || modelOverride;
          const probeChat = await api.sendChat({
            projectId,
            message: `Benchmark technical probe for donor ${donor.id}: reply with BENCHMARK_DONATION_OK and one sentence confirming this donor route served the request.`,
            sessionId: session.id || null,
            maxHistory: 0,
            timeoutMs: chatTimeoutMs,
          });
          if ((probeChat?.content || "").trim()) chat = probeChat;
          probe.response_chars = probeChat?.content?.trim().length || 0;
        } catch (error) {
          probe.error = error.message;
        }
        const afterStats = await readComputeStatsSummary(api, projectId, `after-donor-probe-${donor.id}`);
        const delta = relayRouteDelta(beforeStats, afterStats, projectId);
        probe.selected_relay_nodes = delta.selected;
        probe.served_relay_nodes = delta.served;
        probe.selected_relay_node_count = delta.selected.length;
        probe.served_relay_node_count = delta.served.length;
        probe.ok = !probe.error && probe.response_chars > 0 && probe.served_relay_node_count > 0;
        technicalProbeResults.push(probe);
        logger.action("compute.donation.technical_probe", probe);
      }
      chatError = technicalProbeResults
        .filter((probe) => !probe.ok)
        .map((probe) => `${probe.donor_id}: ${probe.error || "no relay served the probe"}`)
        .join(" | ");
    } else {
      try {
        chat = await api.sendChat({
          projectId,
          message: "Benchmark technical probe: answer with the phrase BENCHMARK_DONATION_OK and one short sentence about donated compute being connected.",
          sessionId: null,
          maxHistory: 0,
          timeoutMs: chatTimeoutMs,
        });
      } catch (error) {
        chatError = error.message;
      }
    }
  } finally {
    if (strictRoutingRestoreValue === false) {
      try {
        await api.post("/api/settings/strict-routing", { enabled: false });
      } catch (error) {
        logger.issue({
          area: "compute-donation",
          severity: "low",
          title: "Could not restore strict routing after donated-compute probe",
          detail: error.message,
        });
      }
    }
  }
  let postProbeStats = null;
  try {
    postProbeStats = summarizeComputeStats(
      await api.get(`/api/compute/stats?project_id=${encodeURIComponent(projectId)}`, { timeoutMs: 15000 })
    );
  } catch (error) {
    logger.action("compute.donation.post_probe_stats_error", { error: error.message });
  }
  const backendLogs = captureBackendLogs("compute-donation-probe", "5m");
  const routeUsedRelay = /routing (stream|chat) to Relay:/i.test(`${backendLogs.stdout}\n${backendLogs.stderr}`);
  const routeAttemptedRelayFromLogs = routeUsedRelay || /(stream|chat) failed on Relay:/i.test(`${backendLogs.stdout}\n${backendLogs.stderr}`);
  const responseChars = forceDonatedChat
    ? technicalProbeResults.reduce((sum, probe) => sum + (probe.response_chars || 0), 0)
    : chat?.content?.trim().length || 0;
  const statsNodes = Array.isArray(postProbeStats?.nodes) ? postProbeStats.nodes : (Array.isArray(registration.stats?.nodes) ? registration.stats.nodes : []);
  const beforeServedByNode = new Map((registration.nodes || []).map((node) => [node.node_id, node.served_request_count || 0]));
  const beforeSelectedByNode = new Map((registration.nodes || []).map((node) => [node.node_id, node.selected_request_count || 0]));
  const aliveRelayNodes = statsNodes.filter((node) => ["relay", "browser"].includes(node.source) && node.alive);
  const aliveDirectNodes = statsNodes.filter((node) => !["relay", "browser"].includes(node.source) && node.alive);
  const selectedRelayNodes = forceDonatedChat
    ? uniqueByNodeId(technicalProbeResults.flatMap((probe) => probe.selected_relay_nodes || []))
    : aliveRelayNodes.filter((node) =>
        (node.selected_request_count || 0) > (beforeSelectedByNode.get(node.node_id) || 0)
      );
  const servedRelayNodes = forceDonatedChat
    ? uniqueByNodeId(technicalProbeResults.flatMap((probe) => probe.served_relay_nodes || []))
    : aliveRelayNodes.filter((node) =>
        (node.served_request_count || 0) > (beforeServedByNode.get(node.node_id) || 0)
        && (!node.last_served_project_id || node.last_served_project_id === projectId)
        && (!node.last_route_kind || ["chat", "stream"].includes(node.last_route_kind))
      );
  const forcedRelayTopology = forceDonatedChat && aliveRelayNodes.length > 0 && aliveDirectNodes.length === 0;
  const modelOverrideRelayEvidence = Boolean(
    forceDonatedChat
    && relayProbeSessionId
    && relayModelOverride
    && aliveRelayNodes.length > 0
  );
  const routeAttemptedRelay = routeAttemptedRelayFromLogs || selectedRelayNodes.length > 0;
  const donorRegistered = registration.ok;
  const donorHealthy = aliveRelayNodes.length >= expectedRelayCount;
  const donorSelected = selectedRelayNodes.length > 0 || routeAttemptedRelay;
  const technicalProbesServed = forceDonatedChat
    && technicalProbeResults.length >= expectedRelayCount
    && technicalProbeResults.every((probe) => probe.ok)
    && servedRelayNodes.length >= expectedRelayCount;
  const donorServedRequest = forceDonatedChat
    ? technicalProbesServed
    : responseChars > 0 && (
        servedRelayNodes.length > 0
        || routeUsedRelay
        || forcedRelayTopology
      );
  const routeVerifiedBy = servedRelayNodes.length > 0
    ? "compute-stats-served-counter"
    : routeUsedRelay
    ? "backend-route-log"
    : forcedRelayTopology
      ? "forced-topology-only-alive-node"
      : modelOverrideRelayEvidence
        ? "relay-model-override"
        : "unverified";
  const ok = !chatError && donorServedRequest;
  const result = {
    ok,
    duration_ms: Date.now() - startedAt,
    expected_donor_count: enabledDonorCount,
    expected_relay_count: expectedRelayCount,
    expected_local_deduped_donor_count: expectedLocalDedupedDonorCount,
    donor_profiles: activeDonorProfiles.map(summarizeDonorProfile),
    registration,
    post_probe_stats: postProbeStats,
    donor_registered: donorRegistered,
    donor_healthy: donorHealthy,
    donor_selected: donorSelected,
    donor_served_request: donorServedRequest,
    selected_relay_node_count: selectedRelayNodes.length,
    served_relay_node_count: servedRelayNodes.length,
    selected_relay_nodes: selectedRelayNodes,
    served_relay_nodes: servedRelayNodes,
    donated_compute_chat_verified: ok,
    relay_model_override_configured: Boolean(relayModelOverride),
    relay_model_override_source: relayProbeSessionId ? "dedicated-donor-session" : "unavailable",
    relay_model_override_id_length: relayModelOverride.length,
    route_used_relay: routeUsedRelay,
    route_attempted_relay: routeAttemptedRelay,
    route_verified_by: routeVerifiedBy,
    route_evidence_detail: technicalProbesServed
      ? "Every required donor relay served a bounded strict project/model probe with project-scoped counter evidence."
      : routeUsedRelay
      ? "Backend logs explicitly reported Relay routing."
      : servedRelayNodes.length > 0
        ? "Project-scoped compute stats showed a relay/browser node served a chat or stream request during the probe."
      : forcedRelayTopology
        ? "The benchmark forced direct server providers unreachable and project-scoped /api/compute/stats showed the relay as the only alive compute node."
        : modelOverrideRelayEvidence
          ? "The probe used a chat session pinned to a dedicated donor model while project-scoped compute stats showed alive relay donors, but this is not accepted as proof that a donor served the request."
        : "Relay routing could not be proved from backend logs or forced topology.",
    forced_relay_topology: forcedRelayTopology,
    model_override_relay_evidence: modelOverrideRelayEvidence,
    alive_relay_node_count: aliveRelayNodes.length,
    alive_direct_node_count: aliveDirectNodes.length,
    multi_donor_registered: expectedRelayCount > 1 && (registration.nodes?.length || 0) >= expectedRelayCount,
    multi_donor_healthy: expectedRelayCount > 1 && aliveRelayNodes.length >= expectedRelayCount,
    chat_error: chatError,
    response_chars: responseChars,
    response_preview: (chat?.content || "").slice(0, 600),
    event_count: chat?.events?.length || 0,
    technical_probe_results: technicalProbeResults,
    technical_probes_all_served: technicalProbesServed,
  };
  logger.writeJson("compute-donation-results.json", result);
  logger.action("compute.donation.verify.result", result);
  if (!ok) {
    blockers.push("Compute donation did not produce a verified relay-routed chat response.");
    logger.issue({
      area: "compute-donation",
      severity: "critical",
      title: "Donated compute chat was not verified",
      detail: chatError || (routeAttemptedRelay ? "Relay route was attempted but did not return user-visible chat output." : "Neither backend route logs nor forced-topology evidence proved relay-routed chat."),
    });
  } else {
    featureResults.computeDonation = true;
    featureResults.multiDonorCompute = expectedRelayCount > 1 && (registration.nodes?.length || 0) >= expectedRelayCount && donorHealthy && donorServedRequest;
    featureResults.liveChat = true;
  }
  return result;
}

async function createProject(api) {
  const body = {
    name: `[RU-BENCH] ${PROJECT_CONTEXT.name} ${runId}`,
    description: `${PROJECT_CONTEXT.product}. Synthetic long-form benchmark project.`,
    phase: "discover",
    company_context: PROJECT_CONTEXT.companyContext || `${PROJECT_CONTEXT.company}: ${PROJECT_CONTEXT.audience}.`,
    project_context: PROJECT_CONTEXT.projectContext || PROJECT_CONTEXT.researchQuestions.join("\n"),
    guardrails: [
      ...(PROJECT_CONTEXT.guardrails || []),
      "",
      "Research questions:",
      ...(PROJECT_CONTEXT.researchQuestions || []),
      "",
      "Success metrics:",
      ...(PROJECT_CONTEXT.successMetrics || []),
    ].join("\n"),
  };
  const project = await api.post("/api/projects", body);
  logger.action("project.created", { project_id: project.id, name: project.name });
  return project;
}

async function grantResearcherProjectAccess(api, projectId, inviteResult) {
  const userId = inviteResult?.parsed?.user_id || inviteResult?.parsed?.me_id || "";
  if (!userId) {
    logger.action("researcher.access.skip", { reason: "no-user-id", invite_ok: Boolean(inviteResult?.ok) });
    return false;
  }
  try {
    await api.post(`/api/projects/${projectId}/members`, {
      user_id: userId,
      role: "researcher",
    });
    logger.action("researcher.access.granted", { project_id: projectId, user_id: userId, role: "researcher" });
    return true;
  } catch (error) {
    if (/409/.test(error.message)) {
      logger.action("researcher.access.already_member", { project_id: projectId, user_id: userId });
      return true;
    }
    logger.issue({
      area: "auth",
      severity: "high",
      title: "Could not grant researcher project access",
      detail: error.message,
    });
    return false;
  }
}

function personaForKey(key, fallbackIndex = 0) {
  return RESEARCHER_PERSONAS.find((persona) => persona.key === key)
    || RESEARCHER_PERSONAS[Math.min(fallbackIndex, RESEARCHER_PERSONAS.length - 1)]
    || RESEARCHER_PERSONAS[0];
}

function actorSummary(actor) {
  if (!actor) return {};
  return {
    key: actor.key,
    label: actor.label,
    username: actor.username,
    role: actor.role,
    persona: actor.persona?.displayName || actor.displayName || "",
  };
}

function actorByKey(actors, key) {
  return actors.find((actor) => actor.key === key || actor.persona?.key === key || actor.username === key);
}

function trackActorContribution(map, actor, kind) {
  const key = actor?.key || actor?.username || "unknown";
  const current = map.get(key) || {
    actor: actorSummary(actor),
    chat_turns: 0,
    tasks_created: 0,
    tasks_reviewed: 0,
    revisions_requested: 0,
    tasks_approved: 0,
  };
  if (kind === "chat") current.chat_turns += 1;
  if (kind === "created") current.tasks_created += 1;
  if (kind === "reviewed") current.tasks_reviewed += 1;
  if (kind === "revision_requested") current.revisions_requested += 1;
  if (kind === "approved") current.tasks_approved += 1;
  map.set(key, current);
}

function makeAdminActor(api) {
  const persona = personaForKey("admin");
  return {
    key: persona.key,
    label: persona.displayName,
    displayName: persona.displayName,
    role: persona.role,
    persona,
    username: benchmarkAdminUsername,
    api,
  };
}

async function authenticateResearcherActors(inviteResults) {
  const actors = [];
  for (let index = 0; index < inviteResults.length; index += 1) {
    const inviteResult = inviteResults[index];
    if (!inviteResult?.ok) continue;
    const persona = personaForKey(`researcher-${index + 1}`, index + 1);
    const researcherApi = new IstaraApiClient({
      apiBase,
      repoRoot,
      logger,
      networkAccessToken: benchmarkNetworkToken,
      adminUsername: inviteResult.username,
      adminPassword: inviteResult.password,
      agentEngine: benchmarkAgentEngine,
    });
    const researcherAuth = await researcherApi.authenticate();
    logger.action("researcher.auth.result", {
      actor: persona.displayName,
      actor_key: persona.key,
      ok: researcherAuth.ok,
      method: researcherAuth.method,
      user_id: researcherAuth.user_id,
    });
    if (researcherAuth.ok) {
      actors.push({
        key: persona.key,
        label: persona.displayName,
        displayName: persona.displayName,
        role: persona.role,
        persona,
        api: researcherApi,
        username: inviteResult.username,
        password: inviteResult.password,
        user_id: researcherAuth.user_id,
      });
    }
  }
  logger.writeJson("researcher-actors.json", actors.map(actorSummary));
  return actors;
}

async function linkProjectFolder(api, projectId, corpusDir) {
  const folderPath = String(process.env.ISTARA_BENCHMARK_SHARED_CORPUS_DIR || "").trim()
    || (startSandbox && !skipSandbox ? `/benchmark-results/runs/${runId}/corpus` : "");
  if (!folderPath) {
    logger.action("project.folder_link.skip", {
      project_id: projectId,
      reason: "No corpus path shared by both runner and backend; uploads remain the authoritative ingestion path.",
      runner_corpus_path: corpusDir,
    });
    return false;
  }
  try {
    const linked = await api.post(`/api/projects/${projectId}/link-folder`, { folder_path: folderPath });
    logger.action("project.folder_linked", { project_id: projectId, folder_path: folderPath, result: linked });
    return true;
  } catch (error) {
    logger.issue({
      area: "project-context",
      severity: "low",
      title: "Could not link canonical corpus folder",
      detail: error.message,
    });
    return false;
  }
}

async function uploadCorpus(api, projectId, manifest, limit) {
  const uploaded = [];
  for (const item of manifest.slice(0, limit)) {
    try {
      const result = await api.uploadFile(projectId, item.path, item.file_name);
      uploaded.push({ ...item, result });
      logger.action("corpus.uploaded", {
        file_name: item.file_name,
        document_id: result.id || result.file_id || result.document_id || "",
      });
    } catch (error) {
      logger.issue({
        area: "upload",
        severity: "medium",
        title: `Upload failed: ${item.file_name}`,
        detail: error.message,
      });
    }
  }
  const resolved = await resolveUploadedDocuments(api, projectId, uploaded);
  logger.writeJson("uploaded-document-manifest.json", resolved);
  return resolved;
}

async function resolveUploadedDocuments(api, projectId, uploaded) {
  try {
    const listing = await api.get(`/api/files/${projectId}`);
    const files = Array.isArray(listing.files) ? listing.files : [];
    const byDisplayName = new Map(files.map((file) => [file.display_name, file]));
    const byStoredName = new Map(files.map((file) => [file.name, file]));
    return uploaded.map((item) => {
      const match = byDisplayName.get(item.file_name) || byStoredName.get(item.result?.saved_as);
      return {
        ...item,
        document_id: match?.document_id || item.result?.doc_id || item.result?.document_id || "",
        document_status: match?.document_status || "",
      };
    });
  } catch (error) {
    logger.issue({
      area: "upload",
      severity: "medium",
      title: "Could not resolve uploaded files to document IDs",
      detail: error.message,
    });
    return uploaded;
  }
}

function uploadedDocumentIds(uploaded) {
  return uploaded
    .map((item) => item.document_id || item.result?.doc_id || item.result?.document_id)
    .filter(Boolean);
}

async function createConnectionStrings(api, { projectId, donorProfilesForRun = donorProfiles, researcherCount = runtimeResearcherCount } = {}) {
  const output = {
    userInvites: [],
    computeDonations: [],
  };
  const clientSandboxesNeedHostUrl = startClientSandboxes || (startSandbox && !skipSandbox);
  const defaultConnectionServerUrl = clientSandboxesNeedHostUrl ? containerReachableUrl(apiBase) : apiBase;
  const connectionServerUrl = (process.env.ISTARA_BENCHMARK_CONNECTION_SERVER_URL || defaultConnectionServerUrl).replace(/\/$/, "");
  const connectionWsUrl = (process.env.ISTARA_BENCHMARK_CONNECTION_WS_URL || `${connectionServerUrl.replace(/^http/, "ws")}/ws/relay`).replace(/\/$/, "");
  logger.action("connection.urls.selected", {
    server_url: hostSummary(connectionServerUrl),
    ws_url: hostSummary(connectionWsUrl),
    client_sandboxes_need_host_url: clientSandboxesNeedHostUrl,
  });
  for (let index = 0; index < researcherCount; index += 1) {
    try {
      const userInvite = await api.post("/api/connections/generate", {
        server_url: connectionServerUrl,
        ws_url: connectionWsUrl,
        label: `Real user benchmark invite ${index + 1} ${runId}`,
        role: "researcher",
        expires_hours: 24,
      });
      output.userInvites.push(userInvite);
      if (index === 0) output.userInvite = userInvite;
      logger.action("connection.user_invite.generated", {
        index,
        id: userInvite.id,
        preview: `${String(userInvite.connection_string).slice(0, 18)}...`,
      });
    } catch (error) {
      blockers.push(`User invite connection string generation failed for researcher ${index + 1}.`);
      logger.issue({
        area: "connection-string",
        severity: "high",
        title: "User invite connection string generation failed",
        detail: error.message,
      });
    }
  }
  for (const donor of donorProfilesForRun.filter((profile) => profile.required)) {
    try {
      const computeDonation = await api.post("/api/connections/compute-donation/generate", {
        server_url: connectionServerUrl,
        ws_url: connectionWsUrl,
        label: `Real user benchmark relay ${donor.id} ${runId}`,
        expires_hours: 24,
        allowed_project_ids: projectId ? [projectId] : [],
      });
      output.computeDonations.push({ ...computeDonation, donor_id: donor.id });
      if (!output.computeDonation) output.computeDonation = computeDonation;
      logger.action("connection.compute.generated", {
        donor_id: donor.id,
        id: computeDonation.id,
        preview: `${String(computeDonation.connection_string).slice(0, 18)}...`,
      });
    } catch (error) {
      blockers.push(`Compute donation connection string generation failed for donor ${donor.id}.`);
      logger.issue({
        area: "connection-string",
        severity: "high",
        title: "Compute donation connection string generation failed",
        detail: error.message,
      });
    }
  }
  logger.writeJson("connection-string-results.json", {
    user_invite_generated: Boolean(output.userInvite?.connection_string),
    compute_donation_generated: Boolean(output.computeDonation?.connection_string),
    user_invite_count: output.userInvites.length,
    compute_donation_count: output.computeDonations.length,
    user_invite_id: output.userInvite?.id || "",
    compute_donation_id: output.computeDonation?.id || "",
    donor_profiles: donorProfilesForRun.map(summarizeDonorProfile),
  });
  return output;
}

function connectionListFromPlan(config, keys) {
  if (!config || typeof config !== "object") return [];
  for (const key of keys) {
    if (config[key]) {
      return asArray(config[key]).map(String).map((item) => item.trim()).filter(Boolean);
    }
  }
  return [];
}

function loadConnectionStringOverrides({ donorProfilesForRun = donorProfiles } = {}) {
  const fileConfig = readJsonConfigFile(
    process.env.ISTARA_BENCHMARK_CONNECTION_STRINGS_FILE,
    "ISTARA_BENCHMARK_CONNECTION_STRINGS_FILE",
  );
  const computeFromFile = connectionListFromPlan(fileConfig, [
    "compute_donations",
    "computeDonations",
    "compute_connection_strings",
    "computeConnectionStrings",
    "donor_connection_strings",
    "donorConnectionStrings",
  ]);
  const userFromFile = connectionListFromPlan(fileConfig, [
    "user_invites",
    "userInvites",
    "user_invite_connection_strings",
    "userInviteConnectionStrings",
    "researcher_invites",
    "researcherInvites",
  ]);
  const computeFromEnv = [
    ...parseConnectionStringList(process.env.ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRINGS),
    ...parseConnectionStringList(process.env.ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRING),
  ];
  const userFromEnv = [
    ...parseConnectionStringList(process.env.ISTARA_BENCHMARK_USER_INVITE_CONNECTION_STRINGS),
    ...parseConnectionStringList(process.env.ISTARA_BENCHMARK_USER_INVITE_CONNECTION_STRING),
  ];
  const computeFromProfiles = donorProfilesForRun.map((profile) => profile.connectionString).filter(Boolean);
  return {
    computeDonations: [...computeFromFile, ...computeFromEnv, ...computeFromProfiles],
    userInvites: [...userFromFile, ...userFromEnv],
    sources: {
      file: Boolean(fileConfig),
      compute_env: computeFromEnv.length,
      user_env: userFromEnv.length,
      donor_profiles: computeFromProfiles.length,
    },
  };
}

async function maybePromptForConnectionOverrides(overrides, { donorProfilesForRun = donorProfiles, researcherCount = runtimeResearcherCount } = {}) {
  if (!boolEnv("ISTARA_BENCHMARK_INTERACTIVE_CONNECTION_STRINGS", false)) return overrides;
  if (!process.stdin.isTTY) {
    blockers.push("Interactive connection string mode was requested, but stdin is not a TTY.");
    logger.issue({
      area: "connection-string",
      severity: "high",
      title: "Interactive connection prompt unavailable",
      detail: "Set ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRINGS and ISTARA_BENCHMARK_USER_INVITE_CONNECTION_STRINGS, or run the benchmark from an interactive terminal.",
    });
    return overrides;
  }
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const currentDonorCount = donorProfilesForRun.filter((profile) => profile.required).length;
    const donorAnswer = await rl.question(`How many compute donor containers should this run start? [${currentDonorCount}] `);
    const donorCount = Number.parseInt(donorAnswer.trim(), 10);
    if (Number.isFinite(donorCount) && donorCount > 0 && donorCount !== currentDonorCount) {
      donorProfiles = buildDonorProfiles({ donorCountOverride: donorCount });
      donorProfilesForRun = donorProfiles;
      sandbox.relayExpectedCount = donorProfiles.filter((profile) => profile.required).length;
      logger.action("connection.interactive.donor_count", {
        requested_count: donorCount,
        donor_profiles: donorProfiles.map(summarizeDonorProfile),
      });
    }
    const researcherAnswer = await rl.question(`How many researcher invite/client containers should this run start? [${researcherCount}] `);
    const parsedResearcherCount = Number.parseInt(researcherAnswer.trim(), 10);
    if (Number.isFinite(parsedResearcherCount) && parsedResearcherCount > 0) {
      runtimeResearcherCount = parsedResearcherCount;
      researcherCount = parsedResearcherCount;
      sandbox.researcherExpectedCount = researcherCount;
    }
    const requiredDonors = donorProfiles.filter((profile) => profile.required);
    const computeDonations = [...overrides.computeDonations];
    for (let index = computeDonations.length; index < requiredDonors.length; index += 1) {
      const answer = await rl.question(`Paste compute donation connection string for ${requiredDonors[index].id}, or leave blank to generate through the API when possible: `);
      if (answer.trim()) computeDonations.push(answer.trim());
    }
    const userInvites = [...overrides.userInvites];
    for (let index = userInvites.length; index < researcherCount; index += 1) {
      const answer = await rl.question(`Paste researcher invite connection string ${index + 1}, or leave blank to generate through the API when possible: `);
      if (answer.trim()) userInvites.push(answer.trim());
    }
    return {
      ...overrides,
      computeDonations,
      userInvites,
      sources: {
        ...overrides.sources,
        interactive: true,
      },
    };
  } finally {
    rl.close();
  }
}

function materializeConnectionStrings(generated, overrides, { donorProfilesForRun = donorProfiles, researcherCount = runtimeResearcherCount } = {}) {
  const computeOverrideStrings = overrides.computeDonations || [];
  const userOverrideStrings = overrides.userInvites || [];
  const output = {
    ...generated,
    userInvites: [],
    computeDonations: [],
  };
  const generatedUserInvites = generated.userInvites || (generated.userInvite ? [generated.userInvite] : []);
  const generatedComputeDonations = generated.computeDonations || (generated.computeDonation ? [generated.computeDonation] : []);
  const userCount = Math.max(researcherCount, userOverrideStrings.length, generatedUserInvites.length);
  for (let index = 0; index < userCount; index += 1) {
    const override = userOverrideStrings[index];
    const generatedInvite = generatedUserInvites[index];
    const invite = override
      ? { connection_string: override, source: "external-override", id: `external-user-invite-${index + 1}` }
      : generatedInvite;
    if (invite?.connection_string) {
      rememberConnectionStringSensitiveValues(invite.connection_string);
      output.userInvites.push(invite);
    }
  }
  output.userInvite = output.userInvites[0] || generated.userInvite;

  const requiredDonors = donorProfilesForRun.filter((profile) => profile.required);
  for (let index = 0; index < requiredDonors.length; index += 1) {
    const donor = requiredDonors[index];
    const override = computeOverrideStrings[index] || donor.connectionString;
    const generatedDonation = generatedComputeDonations[index];
    const donation = override
      ? { connection_string: override, source: "external-override", id: `external-compute-${donor.id}`, donor_id: donor.id }
      : generatedDonation;
    if (donation?.connection_string) {
      rememberConnectionStringSensitiveValues(donation.connection_string);
      output.computeDonations.push({ ...donation, donor_id: donor.id });
    }
  }
  output.computeDonation = output.computeDonations[0] || generated.computeDonation;
  logger.writeJson("connection-string-plan.json", {
    external_mode: externalConnectionStringMode,
    overrides: {
      compute_count: computeOverrideStrings.length,
      user_invite_count: userOverrideStrings.length,
      sources: overrides.sources,
    },
    materialized: {
      compute_count: output.computeDonations.length,
      user_invite_count: output.userInvites.length,
    },
    donor_profiles: donorProfilesForRun.map(summarizeDonorProfile),
  });
  logger.action("connection.plan.materialized", {
    external_mode: externalConnectionStringMode,
    compute_count: output.computeDonations.length,
    user_invite_count: output.userInvites.length,
    donor_count: requiredDonors.length,
  });
  return output;
}

async function revokeGeneratedConnectionStrings(api, connectionStrings) {
  const entries = [
    ...(connectionStrings?.computeDonations || []).map((item) => ({ kind: "compute_donation", item })),
    ...(connectionStrings?.userInvites || []).map((item) => ({ kind: "user_invite", item })),
  ];
  const results = [];
  for (const { kind, item } of entries) {
    const id = String(item?.id || "");
    const external = item?.source === "external-override" || id.startsWith("external-");
    if (external || !id) {
      results.push({ kind, id, status: "skipped_external_or_unidentified", reason: external ? "external-override" : "missing-generated-id" });
      continue;
    }
    try {
      const response = await api.delete(`/api/connections/${encodeURIComponent(id)}`);
      const ok = response?.status === "revoked" || response?.is_active === false;
      results.push({ kind, id, status: ok ? "revoked" : "unexpected-response", response_status: response?.status || "" });
      logger.action("connection.revoked", { kind, id, ok, response_status: response?.status || "" });
      if (!ok) blockers.push(`Generated ${kind} ${id} did not confirm revocation.`);
    } catch (error) {
      results.push({ kind, id, status: "error", error: error.message });
      blockers.push(`Generated ${kind} ${id} could not be revoked.`);
      logger.issue({
        area: "connection-string",
        severity: "high",
        title: `Generated ${kind} revocation failed`,
        detail: error.message,
        evidence: { id, kind },
      });
    }
  }
  const summary = {
    attempted: results.filter((item) => ["revoked", "unexpected-response", "error"].includes(item.status)).length,
    revoked: results.filter((item) => item.status === "revoked").length,
    skipped_external_or_unidentified: results.filter((item) => item.status === "skipped_external_or_unidentified").length,
    results,
  };
  logger.writeJson("connection-revocation-results.json", summary);
  logger.action("connection.revocation.summary", summary);
  return summary;
}

/**
 * F-P2b: benchmark sessions pin a custom inference preset with an adequate
 * completion budget. Default presets cap max_tokens, and reasoning-style
 * models (deepseek-v4-flash et al at low effort) can spend that budget in the
 * reasoning channel before any visible content emits — which the benchmark
 * correctly rejects as "no assistant text". Env: ISTARA_BENCHMARK_SESSION_MAX_TOKENS.
 */
const benchSessionMaxTokens = Number.parseInt(
  process.env.ISTARA_BENCHMARK_SESSION_MAX_TOKENS || "16384", 10,
);

async function ensureBenchSession(api, projectId, label) {
  try {
    const session = await api.post("/api/sessions", {
      project_id: projectId,
      title: `[RU-BENCH] ${label} ${runId}`,
      inference_preset: "custom",
      custom_temperature: 0.7,
      custom_max_tokens: Number.isFinite(benchSessionMaxTokens) ? benchSessionMaxTokens : 16384,
    });
    return session?.id || null;
  } catch (error) {
    console.warn(`[bench] session preset setup failed (${error.message}); using server defaults`);
    return null;
  }
}

async function runChatBenchmark(api, projectId, turns, { actor = null, contributionMap = null } = {}) {
  let sessionId = await ensureBenchSession(api, projectId, actor?.key || "chat");
  const completed = [];
  for (const turn of turns) {
    const started = Date.now();
    try {
      const response = await api.sendChat({
        projectId,
        message: turn.content,
        sessionId,
        maxHistory: 40,
        timeoutMs: chatTimeoutMs,
      });
      sessionId = response.session_id || sessionId;
      const content = response.content || "";
      if (requireLiveChat && !content.trim()) {
        throw new Error("Chat returned no assistant text. Live model-backed output is required for this benchmark profile.");
      }
      const hasCitation = /interview|survey|usability|diary|ticket|source|file/i.test(content);
      if (hasCitation) featureResults.citedSources = true;
      if (content.trim()) featureResults.liveChat = true;
      if (contributionMap && actor) trackActorContribution(contributionMap, actor, "chat");
      completed.push({ turn: turn.turn, ok: true });
      logger.chatTurn({
        turn: turn.turn,
        actor: actor?.label || turn.speaker || "benchmark",
        actor_key: actor?.key || turn.actor_key || "",
        actor_role: actor?.role || turn.actor_role || "",
        intent: turn.intent,
        prompt: turn.content,
        ok: true,
        duration_ms: Date.now() - started,
        response_preview: content.slice(0, 1200),
        event_count: response.events.length,
        session_id: sessionId,
        quality_notes: {
          mentions_sources: hasCitation,
          response_chars: content.length,
        },
      });
    } catch (error) {
      logger.chatTurn({
        turn: turn.turn,
        actor: actor?.label || turn.speaker || "benchmark",
        actor_key: actor?.key || turn.actor_key || "",
        actor_role: actor?.role || turn.actor_role || "",
        intent: turn.intent,
        prompt: turn.content,
        ok: false,
        duration_ms: Date.now() - started,
        error: error.message,
      });
      logger.issue({
        area: "chat",
        severity: "high",
        title: `Chat turn ${turn.turn} failed`,
        detail: error.message,
      });
      blockers.push(`Chat benchmark stopped at turn ${turn.turn}: ${error.message}`);
      break;
    }
  }
  if (completed.length > 0) featureResults.uploadedAndQueried = true;
  return completed.length;
}

async function runCollaborativeChatBenchmark({ projectId, actors, turns }) {
  const activeActors = actors.length ? actors : [];
  if (activeActors.length <= 1) {
    return runChatBenchmark(activeActors[0]?.api || actors[0]?.api, projectId, turns, { actor: activeActors[0] || null });
  }
  const contributionMap = new Map();
  const sessions = new Map();
  for (const a of activeActors) {
    if (!sessions.get(a.key)) {
      // eslint-disable-next-line no-await-in-loop
      sessions.set(a.key, await ensureBenchSession(a.api, projectId, a.key || a.label || "actor"));
    }
  }
  let completed = 0;
  for (let index = 0; index < turns.length; index += 1) {
    const turn = turns[index];
    const actor = actorByKey(activeActors, turn.actor_key) || activeActors[index % activeActors.length];
    const started = Date.now();
    try {
      const response = await actor.api.sendChat({
        projectId,
        message: turn.content,
        sessionId: sessions.get(actor.key) || null,
        maxHistory: 40,
        timeoutMs: chatTimeoutMs,
      });
      sessions.set(actor.key, response.session_id || sessions.get(actor.key) || null);
      const content = response.content || "";
      if (requireLiveChat && !content.trim()) {
        throw new Error("Chat returned no assistant text. Live model-backed output is required for this benchmark profile.");
      }
      const hasCitation = /interview|survey|usability|diary|ticket|source|file/i.test(content);
      if (hasCitation) featureResults.citedSources = true;
      if (content.trim()) featureResults.liveChat = true;
      trackActorContribution(contributionMap, actor, "chat");
      completed += 1;
      logger.chatTurn({
        turn: turn.turn,
        actor: actor.label,
        actor_key: actor.key,
        actor_role: actor.role,
        actor_focus: actor.persona?.focus || "",
        intent: turn.intent,
        prompt: turn.content,
        ok: true,
        duration_ms: Date.now() - started,
        response_preview: content.slice(0, 1200),
        event_count: response.events.length,
        session_id: sessions.get(actor.key),
        quality_notes: {
          mentions_sources: hasCitation,
          response_chars: content.length,
        },
      });
    } catch (error) {
      logger.chatTurn({
        turn: turn.turn,
        actor: actor.label,
        actor_key: actor.key,
        actor_role: actor.role,
        intent: turn.intent,
        prompt: turn.content,
        ok: false,
        duration_ms: Date.now() - started,
        error: error.message,
      });
      logger.issue({
        area: "chat",
        severity: "high",
        title: `Collaborative chat turn ${turn.turn} failed for ${actor.label}`,
        detail: error.message,
        evidence: actorSummary(actor),
      });
      blockers.push(`Collaborative chat stopped at turn ${turn.turn} for ${actor.label}: ${error.message}`);
      break;
    }
  }
  if (completed > 0) featureResults.uploadedAndQueried = true;
  const contributions = Array.from(contributionMap.values());
  logger.writeJson("collaborative-chat-contributions.json", contributions);
  logger.action("chat.collaboration.summary", {
    actor_count: activeActors.length,
    completed_turns: completed,
    active_actor_count: contributions.filter((item) => item.chat_turns > 0).length,
    contributions,
  });
  return completed;
}

async function runTaskAgentPass(api, projectId, task, plan, uploaded, { revisionInstruction = "", weakFirstPass = false, actor = null } = {}) {
  const documentRefs = uploaded
    .slice(0, 8)
    .map((item) => item.file_name || item.result?.saved_as || item.document_id)
    .filter(Boolean)
    .join(", ");
  const prompt = [
    weakFirstPass
      ? "You are doing a first-pass Istara task attempt. Keep it brief, identify what is missing, and do not pretend certainty."
      : "You are Istara executing a researcher task against project evidence. Produce task notes that a human researcher can review.",
    `Task title: ${task.title}`,
    `Task description: ${plan.description}`,
    `Acceptance criteria:\n${plan.acceptance.map((item) => `- ${item}`).join("\n")}`,
    documentRefs ? `Available project documents/files: ${documentRefs}` : "Available project documents/files: none resolved by the benchmark.",
    revisionInstruction ? `Revision instruction from human reviewer: ${revisionInstruction}` : "",
    "Return a grounded evidence summary, sources used or attempted, findings, recommendation, confidence, and any limitation.",
  ].filter(Boolean).join("\n\n");
  const response = await api.sendChat({
    projectId,
    message: prompt,
    maxHistory: 0,
    timeoutMs: chatTimeoutMs,
  });
  const content = (response.content || "").trim();
  if (requireLiveChat && !content) {
    throw new Error(`Task agent pass for ${task.title} returned no live assistant output.`);
  }
  logger.action("task.agent_execution", {
    task_id: task.id,
    title: task.title,
    actor: actor?.label || "benchmark",
    actor_key: actor?.key || "",
    actor_role: actor?.role || "",
    weak_first_pass: weakFirstPass,
    response_chars: content.length,
    response_preview: content.slice(0, 1200),
    event_count: response.events?.length || 0,
    session_id: response.session_id || "",
  });
  return content;
}

async function createReviewAndApproveTasks(options, projectIdArg, taskPlanArg, uploadedArg) {
  const config = options?.adminApi
    ? options
    : {
        adminApi: options,
        adminActor: makeAdminActor(options),
        projectId: projectIdArg,
        taskPlan: taskPlanArg,
        uploaded: uploadedArg,
        researcherActors: [],
      };
  const {
    adminApi,
    adminActor = makeAdminActor(adminApi),
    projectId,
    taskPlan,
    uploaded,
    researcherActors = [],
  } = config;
  let approvals = 0;
  let revisions = 0;
  const approvedTasks = [];
  const createdTasks = [];
  const contributionMap = new Map();
  const activeResearchers = researcherActors.filter((actor) => actor?.api);
  const allActors = [...activeResearchers, adminActor].filter((actor) => actor?.api);
  const taskProjectQuery = `project_id=${encodeURIComponent(projectId)}`;
  for (let index = 0; index < taskPlan.length; index += 1) {
    const plan = taskPlan[index];
    const creator = actorByKey(activeResearchers, plan.creator_key) || activeResearchers[index % activeResearchers.length] || adminActor;
    const reviewer = actorByKey(activeResearchers, plan.reviewer_key)
      || activeResearchers[(index + 1) % activeResearchers.length]
      || adminActor;
    try {
      const task = await creator.api.post("/api/tasks", {
        project_id: projectId,
        title: plan.title,
        description: plan.description,
        skill_name: plan.skill_name,
        user_context: `Benchmark actor ${creator.label} will create this and ${reviewer.label} will review it. Acceptance criteria:\n${plan.acceptance.join("\n")}`,
        input_document_ids: uploadedDocumentIds(uploaded).slice(0, 8),
        urls: plan.title.includes("Integration") ? ["https://example.com/healthcare-coordination-benchmark"] : [],
        instructions: plan.acceptance.join("\n"),
        labels: plan.labels,
        priority: plan.priority,
      });
      createdTasks.push({ id: task.id, title: task.title, creator: actorSummary(creator), reviewer: actorSummary(reviewer) });
      trackActorContribution(contributionMap, creator, "created");
      logger.taskReview({
        task_id: task.id,
        title: task.title,
        actor: creator.label,
        actor_key: creator.key,
        actor_role: creator.role,
        reviewer: reviewer.label,
        reviewer_key: reviewer.key,
        action: "created",
        outcome: "created",
      });

      if (plan.shouldReviseFirst) {
        const weakNotes = await runTaskAgentPass(creator.api, projectId, task, plan, uploaded, { weakFirstPass: true, actor: creator });
        const inReview = await creator.api.patch(`/api/tasks/${task.id}?${taskProjectQuery}`, {
          status: "in_review",
          agent_notes: weakNotes,
          progress: 1,
          what_to_review: "Check whether this has enough evidence and source specificity.",
        });
        const assessment = reviewerAssessment(plan, inReview.agent_notes);
        await reviewer.api.post(`/api/tasks/${task.id}/review/request-revision?${taskProjectQuery}`, {
          what_to_review: assessment.revisionInstruction,
          next_status: "in_progress",
          reviewed_by: `${reviewer.label} benchmark`,
          severity: "medium",
          failure_category: "unsupported_summary",
        });
        revisions += 1;
        trackActorContribution(contributionMap, reviewer, "reviewed");
        trackActorContribution(contributionMap, reviewer, "revision_requested");
        logger.taskReview({
          task_id: task.id,
          title: task.title,
          actor: reviewer.label,
          actor_key: reviewer.key,
          actor_role: reviewer.role,
          creator: creator.label,
          creator_key: creator.key,
          action: "reviewed",
          outcome: "revision_requested",
          issues: assessment.issues,
          instruction: assessment.revisionInstruction,
        });
      }

      const finalAgentNotes = await runTaskAgentPass(creator.api, projectId, task, plan, uploaded, {
        revisionInstruction: "Address any review gaps with concrete source grounding and a clear recommendation.",
        actor: creator,
      });
      const revised = await creator.api.patch(`/api/tasks/${task.id}?${taskProjectQuery}`, {
        status: "in_review",
        agent_notes: finalAgentNotes,
        progress: 1,
        what_to_review: "Review for grounding, utility, and safety.",
      });
      const finalAssessment = reviewerAssessment(plan, revised.agent_notes);
      if (!finalAssessment.approved) {
        await reviewer.api.post(`/api/tasks/${task.id}/review/request-revision?${taskProjectQuery}`, {
          what_to_review: finalAssessment.revisionInstruction,
          next_status: "in_progress",
          reviewed_by: `${reviewer.label} benchmark`,
          severity: "high",
          failure_category: "reviewer_quality_gate",
        });
        revisions += 1;
        trackActorContribution(contributionMap, reviewer, "reviewed");
        trackActorContribution(contributionMap, reviewer, "revision_requested");
        logger.taskReview({
          task_id: task.id,
          title: task.title,
          actor: reviewer.label,
          actor_key: reviewer.key,
          actor_role: reviewer.role,
          creator: creator.label,
          creator_key: creator.key,
          action: "reviewed",
          outcome: "revision_requested",
          issues: finalAssessment.issues,
          instruction: finalAssessment.revisionInstruction,
        });
        continue;
      }

      const approved = await reviewer.api.post(`/api/tasks/${task.id}/review/approve?${taskProjectQuery}`, {
        reviewed_by: `${reviewer.label} benchmark`,
        note: finalAssessment.revisionInstruction,
      });
      approvals += 1;
      trackActorContribution(contributionMap, reviewer, "reviewed");
      trackActorContribution(contributionMap, reviewer, "approved");
      approvedTasks.push({
        id: task.id,
        title: task.title,
        creator: actorSummary(creator),
        reviewer: actorSummary(reviewer),
        agent_notes: finalAgentNotes,
        review_event_id: approved.event?.id || "",
        skill_name: plan.skill_name || "",
        labels: plan.labels || [],
      });
      logger.taskReview({
        task_id: task.id,
        title: task.title,
        actor: reviewer.label,
        actor_key: reviewer.key,
        actor_role: reviewer.role,
        creator: creator.label,
        creator_key: creator.key,
        action: "reviewed",
        outcome: "approved",
        review_event_id: approved.event?.id || "",
        note: finalAssessment.revisionInstruction,
      });
    } catch (error) {
      logger.issue({
        area: "task-review",
        severity: "high",
        title: `Task review flow failed for ${plan.title}`,
        detail: error.message,
        evidence: {
          creator: actorSummary(creator),
          reviewer: actorSummary(reviewer),
        },
      });
    }
  }
  const contributions = Array.from(contributionMap.values());
  const activeActorCount = contributions.filter((item) => (
    item.chat_turns > 0
    || item.tasks_created > 0
    || item.tasks_reviewed > 0
    || item.tasks_approved > 0
  )).length;
  const result = {
    approvals,
    revisions,
    created_count: createdTasks.length,
    approvedTasks,
    createdTasks,
    actorContributions: contributions,
    activeActorCount,
    researcherActorCount: activeResearchers.length,
    adminActor: actorSummary(adminActor),
    actor_count: allActors.length,
  };
  featureResults.taskReviewLoop = approvals > 0 && (revisions > 0 || taskPlan.some((plan) => plan.shouldReviseFirst));
  featureResults.multiUserCollaboration = featureResults.multiUserCollaboration || (activeActorCount >= 2 && activeResearchers.length >= 2);
  logger.writeJson("collaborative-task-workflow.json", result);
  logger.action("task.collaboration.summary", {
    approvals,
    revisions,
    created_count: createdTasks.length,
    active_actor_count: activeActorCount,
    researcher_actor_count: activeResearchers.length,
    contributions,
  });
  return result;
}

async function exerciseLoopsAutoresearch(api, projectId) {
  let ok = false;
  const projectQuery = `project_id=${encodeURIComponent(projectId)}`;
  for (const [label, fn] of [
    ["loops overview", () => api.get(`/api/loops/overview?${projectQuery}`)],
    ["loops agents", () => api.get(`/api/loops/agents?${projectQuery}`)],
    ["loop schedule create", () => api.post("/api/schedules", {
      name: `[RU-BENCH] Weekly support ticket review ${runId}`,
      cron_expression: "0 9 * * 1",
      project_id: projectId,
      skill_name: "analyze-interview",
      description: "Benchmark weekly loop for new support-ticket evidence.",
    })],
    ["autoresearch status", () => api.get(`/api/autoresearch/status?project_id=${projectId}`)],
    ["autoresearch config", () => api.get("/api/autoresearch/config")],
  ]) {
    try {
      const result = await fn();
      logger.action("feature.loops_autoresearch", { label, ok: true, result: preview(result) });
      ok = true;
    } catch (error) {
      logger.action("feature.loops_autoresearch", { label, ok: false, error: error.message });
    }
  }
  featureResults.loops = ok;
  return ok;
}

async function exerciseFindingsReports(api, projectId) {
  try {
    const nugget = await api.post("/api/findings/nuggets", {
      project_id: projectId,
      text: "Care coordinators need source freshness before trusting readiness automation.",
      source: "interviews/P06-care-coordinator.md",
      source_location: "05:42",
      tags: ["trust", "readiness", "source-trail"],
      phase: "discover",
    });
    const fact = await api.post("/api/findings/facts", {
      project_id: projectId,
      text: "Multiple sources converge on missing source trail as a trust blocker.",
      nugget_ids: [nugget.id],
      phase: "define",
    });
    const insight = await api.post("/api/findings/insights", {
      project_id: projectId,
      text: "Readiness automation is not trusted unless it exposes source and freshness.",
      fact_ids: [fact.id],
      phase: "define",
      impact: "high",
    });
    await api.post("/api/findings/recommendations", {
      project_id: projectId,
      text: "Add source freshness, required/optional labels, and caregiver-safe visibility to the readiness timeline.",
      insight_ids: [insight.id],
      phase: "deliver",
      priority: "high",
      effort: "medium",
    });
    featureResults.findingsCreated = true;
    logger.action("feature.findings.created", { nugget_id: nugget.id, fact_id: fact.id, insight_id: insight.id });
  } catch (error) {
    logger.issue({
      area: "findings",
      severity: "medium",
      title: "Could not create atomic findings",
      detail: error.message,
    });
  }
  try {
    const brief = await api.post("/api/interfaces/handoff/brief", { project_id: projectId }, { timeoutMs: 180000 });
    featureResults.reportGenerated = true;
    logger.action("feature.report.generated", { result: preview(brief) });
  } catch (error) {
    logger.action("feature.report.generated", { ok: false, error: error.message });
  }
}

async function captureComputeSnapshot(api, projectId, label) {
  if (!projectId) return null;
  try {
    const stats = summarizeComputeStats(
      await api.get(`/api/compute/stats?project_id=${encodeURIComponent(projectId)}`, { timeoutMs: 15000 })
    );
    logger.action("compute.natural.snapshot", { label, stats });
    return stats;
  } catch (error) {
    logger.action("compute.natural.snapshot_error", { label, error: error.message });
    return null;
  }
}

function computeRouteDeltas(beforeStats, afterStats, projectId) {
  const beforeNodes = new Map((beforeStats?.nodes || []).map((node) => [node.node_id, node]));
  const deltas = (afterStats?.nodes || []).map((node) => {
    const before = beforeNodes.get(node.node_id) || {};
    const selectedDelta = Math.max(0, (node.selected_request_count || 0) - (before.selected_request_count || 0));
    const servedDelta = Math.max(0, (node.served_request_count || 0) - (before.served_request_count || 0));
    const failedDelta = Math.max(0, (node.failed_request_count || 0) - (before.failed_request_count || 0));
    return {
      ...node,
      selected_delta: selectedDelta,
      served_delta: servedDelta,
      failed_delta: failedDelta,
      project_match: !node.last_served_project_id || node.last_served_project_id === projectId,
    };
  });
  const servedNodes = deltas.filter((node) => node.served_delta > 0 && node.project_match);
  const selectedNodes = deltas.filter((node) => node.selected_delta > 0);
  return {
    selected_delta_total: deltas.reduce((sum, node) => sum + node.selected_delta, 0),
    served_delta_total: deltas.reduce((sum, node) => sum + node.served_delta, 0),
    failed_delta_total: deltas.reduce((sum, node) => sum + node.failed_delta, 0),
    served_node_count: servedNodes.length,
    selected_node_count: selectedNodes.length,
    served_nodes: servedNodes,
    selected_nodes: selectedNodes,
    nodes: deltas,
  };
}

async function recordNaturalComputeOrchestration(api, projectId, beforeStats, label) {
  const afterStats = await captureComputeSnapshot(api, projectId, label);
  const routeDeltas = computeRouteDeltas(beforeStats, afterStats, projectId);
  const result = {
    label,
    before: beforeStats,
    after: afterStats,
    route_deltas: routeDeltas,
    verifies_natural_scheduler_use: routeDeltas.served_delta_total > 0 || routeDeltas.selected_delta_total > 0,
    note: "This evidence observes Istara's normal compute/model scheduler after real research work. It does not pin an individual model or donor.",
  };
  featureResults.naturalComputeOrchestration = Boolean(result.verifies_natural_scheduler_use);
  logger.writeJson("natural-compute-orchestration.json", result);
  logger.action("compute.natural.orchestration", {
    label,
    verifies_natural_scheduler_use: result.verifies_natural_scheduler_use,
    selected_delta_total: routeDeltas.selected_delta_total,
    served_delta_total: routeDeltas.served_delta_total,
    served_node_count: routeDeltas.served_node_count,
  });
  return result;
}

function compactTaskNote(note, fallback) {
  const text = String(note || fallback || "").replace(/\s+/g, " ").trim();
  return text.length > 280 ? `${text.slice(0, 277)}...` : text;
}

async function exerciseTaskBackedFindingsReports(api, projectId, taskWorkflow) {
  const approvedTasks = taskWorkflow?.approvedTasks || [];
  if (!approvedTasks.length) {
    logger.action("feature.findings.task_backed.skip", { reason: "no-approved-tasks" });
    return false;
  }
  const sourceTasks = approvedTasks.slice(0, 3);
  try {
    const nugget = await api.post("/api/findings/nuggets", {
      project_id: projectId,
      text: `Approved task evidence: ${compactTaskNote(sourceTasks[0]?.agent_notes, sourceTasks[0]?.title)}`,
      source: `task:${sourceTasks[0].id}`,
      source_location: "approved_agent_notes",
      tags: ["task-backed", "real-user-benchmark", "approved-work"],
      phase: "discover",
    });
    const fact = await api.post("/api/findings/facts", {
      project_id: projectId,
      text: `Approved task review found usable evidence across ${sourceTasks.length} research task(s).`,
      nugget_ids: [nugget.id],
      phase: "define",
    });
    const insight = await api.post("/api/findings/insights", {
      project_id: projectId,
      text: "Only reviewed and approved agent work should advance into the reporting chain.",
      fact_ids: [fact.id],
      phase: "define",
      impact: "high",
    });
    const recommendation = await api.post("/api/findings/recommendations", {
      project_id: projectId,
      text: "Generate leadership reporting from approved task outputs, preserving reviewer notes and source traceability.",
      insight_ids: [insight.id],
      phase: "deliver",
      priority: "high",
      effort: "medium",
    });
    featureResults.findingsCreated = true;
    featureResults.approvedTaskFindings = true;
    logger.action("feature.findings.task_backed.created", {
      approved_task_ids: sourceTasks.map((task) => task.id),
      nugget_id: nugget.id,
      fact_id: fact.id,
      insight_id: insight.id,
      recommendation_id: recommendation.id,
    });
  } catch (error) {
    logger.issue({
      area: "findings",
      severity: "medium",
      title: "Could not create approved-task-backed findings",
      detail: error.message,
    });
  }
  try {
    const brief = await api.post("/api/interfaces/handoff/brief", { project_id: projectId }, { timeoutMs: 180000 });
    featureResults.reportGenerated = true;
    logger.action("feature.report.task_backed.generated", { result: preview(brief) });
  } catch (error) {
    logger.action("feature.report.task_backed.generated", { ok: false, error: error.message });
  }
  return Boolean(featureResults.approvedTaskFindings);
}

function recordInterviewProcessEvidence({ uploaded, taskWorkflow }) {
  const transcriptFiles = uploaded.filter((item) => {
    const name = `${item.file_name || ""} ${item.path || ""} ${item.result?.saved_as || ""}`;
    return /interview|transcript|participant|p\d{2}/i.test(name);
  });
  const approvedInterviewTasks = (taskWorkflow?.approvedTasks || []).filter((task) => (
    task.skill_name === "analyze-interview"
    || /interview|transcript|participant|aura/i.test(task.title)
    || (task.labels || []).some((label) => /interview/i.test(label))
  ));
  const evidence = {
    transcript_file_count: transcriptFiles.length,
    transcript_files: transcriptFiles.slice(0, 12).map((item) => item.file_name || item.result?.saved_as || item.document_id || ""),
    approved_interview_task_count: approvedInterviewTasks.length,
    approved_interview_tasks: approvedInterviewTasks.map((task) => ({
      id: task.id,
      title: task.title,
      creator: task.creator,
      reviewer: task.reviewer,
    })),
    credential_free_required_path: "uploaded transcripts plus analyze-interview task workflow",
    external_channel_required_path: "Telegram/AURA live participant deployment requires explicit bounded test credentials and is documented as future improvement when unavailable.",
  };
  featureResults.interviewEvidence = evidence.transcript_file_count > 0 || evidence.approved_interview_task_count > 0;
  featureResults.interviewProcess = evidence.approved_interview_task_count > 0;
  logger.writeJson("interview-process-evidence.json", evidence);
  logger.action("feature.interview_process.evidence", evidence);
  if (!evidence.approved_interview_task_count) {
    logger.issue({
      area: "interviews",
      severity: "low",
      title: "Interview process did not reach an approved task",
      detail: "The benchmark found or generated transcript material, but no analyze-interview task was approved by the collaborative task workflow.",
      evidence,
    });
  }
  return evidence;
}

function preview(value) {
  return JSON.parse(JSON.stringify(value, (_key, val) => {
    if (typeof val === "string" && val.length > 400) return `${val.slice(0, 400)}...`;
    return val;
  }));
}

function writePlanSnapshot(corpusSummary) {
  logger.writeJson("benchmark-playbook-snapshot.json", {
    system_prompt: {
      source_path: systemPromptPath,
      copied_to_run: "system-prompt.md",
      version: systemPromptVersion,
      sha256: systemPromptHash,
      bytes: Buffer.byteLength(systemPromptContent, "utf8"),
    },
    persona: "Maya Rodrigues leads a small research team instead of acting as the only user",
    personas: RESEARCHER_PERSONAS,
    project: PROJECT_CONTEXT,
    requested_full_chat_turns: 100,
    requested_completed_tasks: 50,
    requested_researcher_client_count: runtimeResearcherCount,
    acceptance_profile: acceptanceProfile,
    provider_acceptance_selected: providerAcceptanceSelected,
    petals_acceptance_selected: petalsAcceptanceSelected,
    workload_scope: workload,
    requested_limits: {
      chat_turns: requestedMaxChatTurns,
      tasks: requestedMaxTasks,
      uploads: requestedMaxUploads,
      coding_units: requestedCodingValidationLimit,
    },
    effective_limits: {
      chat_turns: maxChatTurns,
      tasks: maxTasks,
      uploads: maxUploads,
      coding_units: codingValidationLimit,
    },
    requested_compute_donor_count: workload.petals ? donorProfiles.filter((profile) => profile.required).length : 0,
    compute_donor_profiles: donorProfiles.map(summarizeDonorProfile),
    generated_chat_turn_templates: buildCollaborativeChatTurns({ total: 108 }),
    generated_task_templates: [buildInterviewProcessPlan(), ...buildTaskPlan({ total: 59 })],
    corpus_summary: {
      document_count: corpusSummary.document_count,
      total_bytes: corpusSummary.total_bytes,
    },
    integration_policy: "Attempt developer-friendly harnesses first; classify credential-free blockers as product findings.",
  });
}

async function main() {
  if (failClosedForHostManagedThreeModelRun()) return;
  captureColimaStorageSnapshot("run-start", { recordIssue: true });
  logger.action("benchmark.start", {
    mode,
    acceptance_profile: acceptanceProfile,
    provider_acceptance_selected: providerAcceptanceSelected,
    petals_acceptance_selected: petalsAcceptanceSelected,
    workload_scope: workload,
    requested_limits: {
      chat_turns: requestedMaxChatTurns,
      tasks: requestedMaxTasks,
      uploads: requestedMaxUploads,
      coding_units: requestedCodingValidationLimit,
    },
    effective_limits: {
      chat_turns: maxChatTurns,
      tasks: maxTasks,
      uploads: maxUploads,
      coding_units: codingValidationLimit,
    },
    apiBase,
    frontendUrl,
    maxChatTurns,
    maxTasks,
    maxUploads,
    codingValidationEnabled,
    codingValidationLimit,
    selfImprovementProbeEnabled,
    startAutoresearchExperiment,
    startSandbox,
    skipSandbox,
    startClientSandboxes,
    hostManagedThreeModelRun,
    stopColimaAfterRun,
    externalConnectionStringMode,
    freshSandbox,
    benchmarkTeamMode,
    hasNetworkAccessToken: Boolean(benchmarkNetworkToken),
    requireComputeDonation,
    requireLiveChat,
    forceDonatedChat,
    researcher_count: runtimeResearcherCount,
    donor_count_requested: workload.petals ? donorProfiles.filter((profile) => profile.required).length : 0,
    donor_profiles: donorProfiles.map(summarizeDonorProfile),
    colima_storage_policy: colimaStoragePolicy,
    colima_storage_budget: colimaStorageBudget,
    colima_enforce_apparent_storage: enforceColimaApparentStorage,
    relayLlm: {
      provider: relayLlmProvider,
      provider_source: relayLlmProviderSource,
      host: hostSummary(relayLlmHost),
      host_source: relayLlmHostSource,
      host_localhost_translated_for_container: relayLlmHostRaw !== relayLlmHostForContainer,
      host_openai_path_stripped_for_native_lmstudio: relayLlmHostNormalized,
      live_base_url_configured: Boolean(liveLlmProfile.baseUrl),
      live_base_url_source: liveLlmProfile.baseUrlSource,
      api_key_configured: Boolean(relayLlmApiKey),
      api_key_source: relayLlmApiKeySource,
      model_configured: Boolean(relayLlmModel && relayLlmModel !== "default"),
      model_source: relayLlmModelSource,
      model_id_redacted: true,
    },
    backgroundAgentsDisabled,
  });

  const corpus = generateCorpus({ outputDir: logger.paths.corpus, logger });
  logger.writeJson("corpus-manifest.json", corpus);
  writePlanSnapshot(corpus);

  if (mode === "plan-only") {
    const enginePlan = benchmarkEngines.length ? benchmarkEngines : ["(default)"];
    console.log("[plan-only] real-user benchmark — no live services attempted.");
    for (const engine of enginePlan) {
      const header =
        engine === "(default)"
          ? "(engine header unset — dispatcher default)"
          : `${AGENT_ENGINE_HEADER}: ${engine}`;
      console.log(`[plan-only] engine=${engine} -> ${header}`);
    }
    blockers.push("Plan-only mode did not attempt live services.");
    const scorecard = buildScorecard({
      mode,
      metrics: { corpusDocuments: corpus.document_count },
      integrationMatrix: [],
      blockers,
      completedTasks: 0,
      chatTurns: 0,
      uploadedDocuments: 0,
      sandbox,
      featureResults,
    });
    logger.writeJson("scorecard.json", scorecard);
    logger.appendReport("Plan-only mode generated the benchmark corpus, playbook snapshot, and scoring scaffold without live app interaction.\n\n");
    logger.appendReport(writeScorecardMarkdown(scorecard));
    logger.finalize({ scorecard });
    return;
  }

  startServerSandboxIfRequested();
  const api = new IstaraApiClient({
    apiBase,
    repoRoot,
    logger,
    networkAccessToken: benchmarkNetworkToken,
    adminUsername: benchmarkAdminUsername,
    adminPassword: benchmarkAdminPassword,
    agentEngine: benchmarkAgentEngine,
  });
  const health = await waitForHealth(api, startSandbox && !skipSandbox && sandbox.serverStarted ? 240000 : 15000);
  if (!health.ok) {
    blockers.push(`Istara API is unreachable at ${apiBase}.`);
    logger.issue({
      area: "install",
      severity: "critical",
      title: "Istara API unreachable",
      detail: health.error || `status=${health.status}`,
    });
    const scorecard = buildScorecard({
      mode,
      metrics: { corpusDocuments: corpus.document_count },
      integrationMatrix: [],
      blockers,
      completedTasks: 0,
      chatTurns: 0,
      uploadedDocuments: 0,
      sandbox,
      featureResults,
    });
    logger.writeJson("scorecard.json", scorecard);
    logger.appendReport("The benchmark could not reach the Istara API, so the run is a documented environment/product blocker.\n\n");
    logger.appendReport(writeScorecardMarkdown(scorecard));
    stopColimaIfRequested("api-unreachable");
    logger.finalize({ scorecard });
    return;
  }

  const auth = await api.authenticate();
  logger.action("auth.result", auth);
  if (!auth.ok) {
    blockers.push(`Benchmark could not authenticate: ${auth.reason || auth.method}`);
    logger.issue({
      area: "auth",
      severity: "critical",
      title: "Benchmark authentication failed",
      detail: auth.reason || "No token available.",
    });
  }

  if (auth.ok) {
    try {
      securityIntegrityBaseline = await api.get("/api/settings/security-integrity");
      logger.writeJson("security-integrity-baseline.json", securityIntegrityBaseline);
      const fieldHealth = securityIntegrityBaseline?.field_encryption || {};
      if (fieldHealth.healthy !== true || Number(fieldHealth.decryption_failures || 0) > 0) {
        blockers.push("Field-encryption integrity was already degraded before benchmark work began.");
      }
      const telemetryHealth = securityIntegrityBaseline?.telemetry_writes || {};
      if (telemetryHealth.healthy !== true || Number(telemetryHealth.write_failures || 0) > 0) {
        blockers.push("Telemetry evidence persistence was already degraded before benchmark work began.");
      }
    } catch (error) {
      blockers.push("Security-integrity health could not be verified before the benchmark.");
      logger.issue({
        area: "security-integrity",
        severity: "critical",
        title: "Security integrity baseline unavailable",
        detail: error.message,
      });
    }
  }

  let project = null;
  let uploaded = [];
  let connectionStrings = {};
  let integrationMatrix = [];
  let chatTurnCount = 0;
  let completedTasks = 0;
  let taskWorkflow = null;
  let researchSpineEvidence = null;
  let connectionRevocation = null;
  let researcherInviteResults = [];
  let researcherActors = [];

  if (auth.ok) {
    project = await createProject(api);
    if (workload.corpus) {
      await linkProjectFolder(api, project.id, logger.paths.corpus);
      uploaded = await uploadCorpus(api, project.id, corpus.manifest, maxUploads);
    } else {
      logger.action("corpus.upload.skip", { reason: "acceptance-profile-does-not-select-corpus" });
    }
    if (uploaded.length > 0) featureResults.uploadedAndQueried = true;

    let selectedDonorProfiles = workload.petals ? donorProfiles : [];
    let selectedResearcherCount = workload.commonWorkflow ? runtimeResearcherCount : 0;
    const initialOverrides = loadConnectionStringOverrides({ donorProfilesForRun: selectedDonorProfiles });
    const connectionOverrides = (workload.petals || workload.commonWorkflow)
      ? await maybePromptForConnectionOverrides(initialOverrides, {
          donorProfilesForRun: selectedDonorProfiles,
          researcherCount: selectedResearcherCount,
        })
      : initialOverrides;
    if (workload.petals) selectedDonorProfiles = donorProfiles;
    if (workload.commonWorkflow) selectedResearcherCount = runtimeResearcherCount;
    const requiredDonorCount = selectedDonorProfiles.filter((profile) => profile.required).length;
    const hasAllExternalOverrides = connectionOverrides.computeDonations.length >= requiredDonorCount
      && connectionOverrides.userInvites.length >= selectedResearcherCount;
    const shouldGenerateConnectionStrings = !hasAllExternalOverrides || boolEnv("ISTARA_BENCHMARK_GENERATE_CONNECTION_STRINGS_WITH_OVERRIDES", false);
    const generatedConnectionStrings = shouldGenerateConnectionStrings
      ? await createConnectionStrings(api, {
          projectId: project.id,
          donorProfilesForRun: selectedDonorProfiles,
          researcherCount: selectedResearcherCount,
        })
      : { userInvites: [], computeDonations: [] };
    connectionStrings = materializeConnectionStrings(generatedConnectionStrings, connectionOverrides, {
      donorProfilesForRun: selectedDonorProfiles,
      researcherCount: selectedResearcherCount,
    });
    const requiredDonors = selectedDonorProfiles.filter((profile) => profile.required);
    const enabledRequiredDonors = requiredDonors.filter((profile) => profile.enabled);
    const endpointDiversity = {
      ...donorEndpointDiversity(enabledRequiredDonors),
      selected: workload.petals,
      required_donor_count: requiredDonors.length,
      enabled_required_donor_count: enabledRequiredDonors.length,
      all_required_donors_enabled: enabledRequiredDonors.length === requiredDonors.length,
    };
    endpointDiversity.ok = endpointDiversity.all_required_donors_enabled
      && (!requireDistinctDonorEndpoints || endpointDiversity.distinct);
    // An unselected Petals plane must not emit a vacuous "distinct" result
    // merely because its donor list is empty (`[].distinct === true`).
    featureResults.distinctDonorEndpoints = workload.petals && endpointDiversity.ok;
    logger.writeJson("donor-endpoint-diversity.json", endpointDiversity);
    logger.action("compute.donor.endpoint_diversity", endpointDiversity);
    if (!endpointDiversity.ok && requireDistinctDonorEndpoints) {
      blockers.push("Required compute donors do not resolve to distinct runnable LLM endpoints.");
      logger.issue({
        area: "compute-donation",
        severity: "critical",
        title: "Required donor endpoints are not distinct",
        detail: `Enabled donors: ${endpointDiversity.enabled_required_donor_count}/${endpointDiversity.required_donor_count}. Duplicate endpoint groups: ${JSON.stringify(endpointDiversity.duplicate_groups)}.`,
      });
    }

    if (workload.petals) {
      for (const donor of requiredDonors) {
        await startDonorModelSandbox(donor);
      }
    }

    researcherInviteResults = [];
    if (workload.commonWorkflow) {
      for (let index = 0; index < connectionStrings.userInvites.length; index += 1) {
        const result = startInviteClientSandbox(connectionStrings.userInvites[index]?.connection_string || "", index);
        if (result) researcherInviteResults.push(result);
        await grantResearcherProjectAccess(api, project.id, result);
      }
    }
    logger.writeJson("connection-client-results.json", {
      attempted: researcherInviteResults.length > 0,
      expected_count: selectedResearcherCount,
      ok_count: researcherInviteResults.filter((result) => result.ok).length,
      results: researcherInviteResults.map((result) => ({
        ok: result.ok,
        username: result.username,
        email: result.email,
        user_id: result.parsed?.user_id || result.parsed?.me_id || "",
        role: result.parsed?.role || result.parsed?.me_role || "",
      })),
    });
    researcherActors = await authenticateResearcherActors(researcherInviteResults);

    const activeDonorProfiles = [];
    for (let index = 0; workload.petals && index < requiredDonors.length; index += 1) {
      const donor = requiredDonors[index];
      const donation = connectionStrings.computeDonations.find((item) => item.donor_id === donor.id) || connectionStrings.computeDonations[index];
      const preflight = await preflightRelayLlmFromContainer(donor);
      const preflightOk = preflight?.ok === true || (preflight?.skipped === true && !requireComputeDonation);
      if (donation?.connection_string && donor.enabled && preflightOk) {
        activeDonorProfiles.push(donor);
        startRelayClientSandbox(donation.connection_string, donor, index);
      } else {
        logger.action("sandbox.relay.blocked_by_preflight", {
          donor_id: donor.id,
          has_connection_string: Boolean(donation?.connection_string),
          donor_enabled: Boolean(donor.enabled),
          preflight_ok: Boolean(preflightOk),
          preflight_skipped: Boolean(preflight?.skipped),
        });
        if (requireComputeDonation) {
          blockers.push(`Required compute donor ${donor.id} was not started because its LLM preflight did not prove a runnable endpoint.`);
        }
      }
    }
    if (workload.petals) {
      await verifyComputeDonation(api, project.id, { activeDonorProfiles });
    } else {
      logger.action("compute.donation.verify.skip", { reason: "acceptance-profile-does-not-select-petals" });
      logger.writeJson("compute-donation-results.json", { selected: false, reason: "acceptance-profile-does-not-select-petals" });
    }
    if (workload.commonWorkflow) {
    const adminActor = makeAdminActor(api);

    const uiResult = await runUiJourney({
      frontendUrl,
      api,
      projectId: project.id,
      logger,
      chatTurns: buildChatTurns({ total: 5 }),
      actor: "admin",
      credentials: {
        username: benchmarkAdminUsername,
        password: benchmarkAdminPassword,
      },
    });
    featureResults.uiVisited = uiResult.visited;
    featureResults.uiOnboarding = uiResult.onboarding;
    featureResults.adminUiRoleContract = uiResult.visited && (uiResult.unexpectedForbiddenCount || 0) === 0;

    let researcherUiSuccessCount = 0;
    for (let index = 0; index < researcherActors.length; index += 1) {
      const actor = researcherActors[index];
      try {
        const researcherUiResult = await runUiJourney({
          frontendUrl,
          api: actor.api,
          projectId: project.id,
          logger,
          chatTurns: buildCollaborativeChatTurns({ total: 3, actors: [actor.persona] }),
          actor: actor.key,
          credentials: {
            username: actor.username,
            password: actor.password,
          },
        });
        const ok = researcherUiResult.visited
          && ["chat", "shell", "no_project"].includes(researcherUiResult.finalState)
          && (researcherUiResult.unexpectedForbiddenCount || 0) === 0;
        if (ok) researcherUiSuccessCount += 1;
        logger.action("researcher.ui.result", { actor: actorSummary(actor), ok, result: researcherUiResult });
      } catch (error) {
        logger.issue({
          area: "ui",
          severity: "high",
          title: `Researcher UI journey failed for ${actor.label}`,
          detail: error.message,
          evidence: actorSummary(actor),
        });
      }
    }
    featureResults.researcherUi = researcherUiSuccessCount > 0;
    featureResults.multiUserCollaboration = researcherUiSuccessCount >= Math.min(2, runtimeResearcherCount);

    const computeBeforeResearch = await captureComputeSnapshot(api, project.id, "before-collaborative-research");
    await exerciseLoopsAutoresearch(api, project.id);
    integrationMatrix = await runIntegrationMatrix({ api, projectId: project.id, repoRoot, logger });
    featureResults.interfaces = integrationMatrix.some((item) => ["Google Stitch", "Figma"].includes(item.integration) && item.classification === "developer-harness-tested");

    const turns = buildChatTurns({ total: Math.max(maxChatTurns, 0) }).slice(0, maxChatTurns);
    if (turns.length > 0) {
      const chatActors = researcherActors.length ? researcherActors : [adminActor];
      const collaborativeTurns = researcherActors.length > 1
        ? buildCollaborativeChatTurns({ total: turns.length, actors: researcherActors.map((actor) => actor.persona) })
        : turns;
      chatTurnCount = researcherActors.length > 1
        ? await runCollaborativeChatBenchmark({ projectId: project.id, actors: chatActors, turns: collaborativeTurns })
        : await runChatBenchmark(chatActors[0].api, project.id, turns, { actor: chatActors[0] });
      featureResults.urlFetch = chatTurnCount >= 10 || turns.some((turn) => /URL|fetch|web/i.test(turn.content));
    }

    const taskPlan = maxTasks > 0
      ? [buildInterviewProcessPlan(), ...buildTaskPlan({ total: Math.max(maxTasks - 1, 0) })]
      : [];
    taskWorkflow = await createReviewAndApproveTasks({
      adminApi: api,
      adminActor,
      projectId: project.id,
      taskPlan,
      uploaded,
      researcherActors,
    });
    completedTasks = taskWorkflow.approvals;
    recordInterviewProcessEvidence({ uploaded, taskWorkflow });
    await recordNaturalComputeOrchestration(api, project.id, computeBeforeResearch, "after-collaborative-research");
    }

    if (workload.provider) {
      const expectedResearchSpineDonorRoutes = (hostManagedThreeModelRun || dockerOwnedThreeModelRun)
        ? Math.min(3, donorProfiles.filter((profile) => profile.required && profile.enabled).length)
        : 0;
      if (codingValidationEnabled && expectedResearchSpineDonorRoutes >= 2) {
        const preCodingRelayHealth = await waitForHealthyRelayRoutes(
          api,
          project.id,
          expectedResearchSpineDonorRoutes,
          180000,
          "before-research-spine-coding",
        );
        logger.writeJson("research-spine-pre-coding-relay-health.json", preCodingRelayHealth);
        if (!preCodingRelayHealth.ok) {
          blockers.push(`Research Spine coding did not have all required donor relays healthy: ${preCodingRelayHealth.alive_relay_count}/${expectedResearchSpineDonorRoutes}.`);
          logger.issue({
            area: "research-spine",
            severity: "high",
            title: "Required donor relays were not healthy before Research Spine coding",
            detail: "The benchmark must prove the host donor plus both Colima donors can serve the coding pass. Registration or earlier technical probes are not enough.",
            evidence: {
              expected_distinct_donor_routes: expectedResearchSpineDonorRoutes,
              alive_relay_count: preCodingRelayHealth.alive_relay_count,
            },
          });
        }
      }
      researchSpineEvidence = await exerciseResearchSpineValidation({
        api,
        projectId: project.id,
        taskWorkflow,
        logger,
        featureResults,
        blockers,
        codingValidationEnabled,
        codingValidationLimit,
        expectedDistinctCoders: codingValidationEnabled ? 3 : 0,
        expectedDistinctDonorRoutes: expectedResearchSpineDonorRoutes,
        // Research Spine reliability is defined over raw evidence units coded by
        // distinct model identities.  Source diversity remains a deterministic
        // selection preference, but the contract does not require three source
        // documents; a single interview/document may legitimately provide three
        // independent spans.  Keep source count observable in the selection
        // artifact without turning it into a false acceptance blocker.
        expectedDistinctSources: 0,
      });
    } else {
      logger.action("research-spine.validation.skip", { reason: "acceptance-profile-does-not-select-provider" });
      logger.writeJson("research-spine-results.json", { selected: false, reason: "acceptance-profile-does-not-select-provider" });
    }
    if (workload.commonWorkflow) {
      await exerciseSelfImprovementGovernance({
        api,
        projectId: project.id,
        taskWorkflow,
        researchSpineEvidence,
        logger,
        featureResults,
        runId,
        selfImprovementProbeEnabled,
        startAutoresearchExperiment,
      });
      await exerciseTaskBackedFindingsReports(api, project.id, taskWorkflow);
      if (!featureResults.approvedTaskFindings) {
        await exerciseFindingsReports(api, project.id);
      }
    }
  }

  blockers.push(...liveAcceptanceBlockers({
    maxChatTurns,
    chatTurnCount,
    maxTasks,
    completedTasks,
    acceptanceProfile,
    codingValidationEnabled,
    requireComputeDonation,
    featureResults,
  }));
  if (mode === "full" && workload.chat && chatTurnCount < 100) blockers.push(`Full run completed only ${chatTurnCount}/100 required chat turns.`);
  if (mode === "full" && workload.tasks && completedTasks < 50) blockers.push(`Full run completed only ${completedTasks}/50 required reviewed tasks.`);

  if (auth.ok) {
    try {
      const finalIntegrity = await api.get("/api/settings/security-integrity");
      logger.writeJson("security-integrity-final.json", finalIntegrity);
      const baselineFailures = Number(securityIntegrityBaseline?.field_encryption?.decryption_failures || 0);
      const finalFailures = Number(finalIntegrity?.field_encryption?.decryption_failures || 0);
      if (finalIntegrity?.field_encryption?.healthy !== true || finalFailures > baselineFailures) {
        blockers.push(`Field-encryption integrity failed during the benchmark (${baselineFailures} -> ${finalFailures}).`);
      }
      const baselineTelemetryFailures = Number(securityIntegrityBaseline?.telemetry_writes?.write_failures || 0);
      const finalTelemetryFailures = Number(finalIntegrity?.telemetry_writes?.write_failures || 0);
      if (finalIntegrity?.telemetry_writes?.healthy !== true || finalTelemetryFailures > baselineTelemetryFailures) {
        blockers.push(`Telemetry evidence persistence failed during the benchmark (${baselineTelemetryFailures} -> ${finalTelemetryFailures}).`);
      }
    } catch (error) {
      blockers.push("Security-integrity health could not be verified after the benchmark.");
      logger.issue({
        area: "security-integrity",
        severity: "critical",
        title: "Security integrity final check unavailable",
        detail: error.message,
      });
    }
  }

  if (auth.ok && (workload.petals || workload.commonWorkflow)) {
    connectionRevocation = await revokeGeneratedConnectionStrings(api, connectionStrings);
  } else {
    connectionRevocation = { attempted: 0, revoked: 0, skipped_external_or_unidentified: 0, results: [], selected: false };
    logger.writeJson("connection-revocation-results.json", connectionRevocation);
    logger.action("connection.revocation.skip", { reason: "no-generated-connections-for-selected-profile" });
  }

  captureColimaStorageSnapshot("before-scorecard", { recordIssue: true });
  const scorecard = buildScorecard({
    mode,
    metrics: { ...logger.metrics, corpusDocuments: corpus.document_count },
    integrationMatrix,
    blockers,
    completedTasks,
    chatTurns: chatTurnCount,
    uploadedDocuments: uploaded.length,
    sandbox,
    featureResults,
    connectionRevocation,
  });
  logger.writeJson("scorecard.json", scorecard);
  const historyRecord = {
    run_id: runId,
    mode,
    acceptance_profile: acceptanceProfile,
    workload_scope: workload,
    requested_limits: {
      chat_turns: requestedMaxChatTurns,
      tasks: requestedMaxTasks,
      uploads: requestedMaxUploads,
      coding_units: requestedCodingValidationLimit,
    },
    effective_limits: {
      chat_turns: maxChatTurns,
      tasks: maxTasks,
      uploads: maxUploads,
      coding_units: codingValidationLimit,
    },
    date: new Date().toISOString(),
    benchmark_id: benchmarkRegistry.benchmark_id,
    benchmark_registry_version: benchmarkRegistry.version,
    score: scorecard.total,
    chat_turns: chatTurnCount,
    completed_tasks: completedTasks,
    uploaded_documents: uploaded.length,
    blocker_count: blockers.length,
    unrelated_workflow_failures: [...unrelatedWorkflowFailures],
    connection_revocation: connectionRevocation,
    compute_donation_verified: Boolean(featureResults.computeDonation),
    multi_donor_compute_verified: Boolean(featureResults.multiDonorCompute),
    natural_compute_orchestration_verified: Boolean(featureResults.naturalComputeOrchestration),
    distinct_donor_endpoints_verified: Boolean(featureResults.distinctDonorEndpoints),
    multi_user_collaboration_verified: Boolean(featureResults.multiUserCollaboration),
    task_review_loop_verified: Boolean(featureResults.taskReviewLoop),
    approved_task_findings_verified: Boolean(featureResults.approvedTaskFindings),
    interview_process_verified: Boolean(featureResults.interviewProcess),
    coding_validation_verified: Boolean(featureResults.codingValidation),
    donor_endpoint_contract_verified: Boolean(featureResults.distinctDonorEndpoints),
    research_spine_structure_present: Boolean(featureResults.researchSpineTraceability),
    research_spine_validation_verified: scorecard.research_spine_validation_verified,
    research_spine_donor_routes_verified: Boolean(featureResults.multiModelResearchSpineValidation),
    research_spine_traceability_verified: Boolean(featureResults.researchSpineTraceability),
    telemetry_evidence_verified: Boolean(featureResults.telemetryEvidence),
    reasoning_bank_evidence_verified: Boolean(featureResults.reasoningBankEvidence),
    memento_skill_health_exercised: Boolean(featureResults.mementoSkillEvidence),
    meta_hyperagent_evidence_verified: Boolean(featureResults.metaHyperagentEvidence),
    self_improvement_governance_verified: Boolean(featureResults.selfImprovementGovernance),
    autoresearch_evidence_verified: Boolean(featureResults.autoresearchEvidence),
    rag_traceability_evidence_verified: Boolean(featureResults.ragTraceabilityEvidence),
    autoresearch_experiment_started: Boolean(startAutoresearchExperiment),
    host_managed_three_model_run: Boolean(hostManagedThreeModelRun),
    docker_runner_mode: Boolean(dockerRunnerMode),
    docker_owned_three_model_run: Boolean(dockerOwnedThreeModelRun),
    stop_colima_after_run: Boolean(stopColimaAfterRun),
    colima_autostart_attempted: Boolean(colimaAutostartAttempted),
    colima_started_by_benchmark: Boolean(colimaStartedByBenchmark),
    compute_donor_count_requested: workload.petals ? donorProfiles.filter((profile) => profile.required).length : 0,
    compute_donor_count_started: sandbox.relayStartedCount,
    donor_model_server_count_requested: sandbox.modelServerExpectedCount,
    donor_model_server_count_started: sandbox.modelServerStartedCount,
    researcher_client_count_requested: workload.commonWorkflow ? runtimeResearcherCount : 0,
    researcher_client_count_started: sandbox.researcherStartedCount,
    live_chat_verified: Boolean(featureResults.liveChat),
    researcher_actor_count: researcherActors.length,
    task_workflow_summary: taskWorkflow
      ? {
          approvals: taskWorkflow.approvals,
          revisions: taskWorkflow.revisions,
          active_actor_count: taskWorkflow.activeActorCount,
          researcher_actor_count: taskWorkflow.researcherActorCount,
        }
      : null,
    integration_classifications: scorecard.integration_summary,
    companion_suites: benchmarkRegistry.companion_suites.map((suite) => suite.path),
    industry_alignment: benchmarkRegistry.industry_alignment.map((item) => item.reference),
    live_model_profile: benchmarkRegistry.live_model_profile || { model: PRIMARY_TEST_MODEL },
    agentic_eval_focus: benchmarkRegistry.agentic_eval_focus?.map((item) => item.area) || [],
    colima_storage: summarizeColimaStorage(latestColimaStorageSnapshot),
  };
  logger.writeJson("history-record.json", historyRecord);
  logger.rootLine("history.jsonl", historyRecord);
  logger.writeRootJson("latest-run.json", {
    ...historyRecord,
    run_dir: logger.runDir,
    run_summary: join(logger.runDir, "run-summary.json"),
    scorecard: join(logger.runDir, "scorecard.json"),
    report: join(logger.runDir, "report.md"),
  });

  logger.appendReport("## Run Summary\n\n");
  logger.appendReport(`Corpus documents generated: ${corpus.document_count}\n\n`);
  logger.appendReport(`Documents uploaded: ${uploaded.length}\n\n`);
  logger.appendReport(`Chat turns completed: ${chatTurnCount}\n\n`);
  logger.appendReport(`Human-approved completed tasks: ${completedTasks}\n\n`);
  logger.appendReport(`Compute donation verified: ${featureResults.computeDonation ? "yes" : "no"}\n\n`);
  logger.appendReport(`Host-managed three-model topology: ${hostManagedThreeModelRun ? "yes" : "no"}\n\n`);
  logger.appendReport(`Docker runner mode: ${dockerRunnerMode ? "yes" : "no"}\n\n`);
  logger.appendReport(`Docker-owned three-model topology: ${dockerOwnedThreeModelRun ? "yes" : "no"}\n\n`);
  logger.appendReport(`Stop Colima after benchmark resources are cleaned up: ${stopColimaAfterRun ? "yes" : "no"}\n\n`);
  logger.appendReport(`Compute donor containers: ${sandbox.relayStartedCount}/${donorProfiles.filter((profile) => profile.required).length} started\n\n`);
  logger.appendReport(`Donor model server containers: ${sandbox.modelServerStartedCount}/${sandbox.modelServerExpectedCount} started\n\n`);
  logger.appendReport(`Donor endpoint contract verified: ${featureResults.distinctDonorEndpoints ? "yes" : "no"}\n\n`);
  logger.appendReport(`Research Spine donor routes verified: ${scorecard.research_spine_donor_routes_verified ? "yes" : "no"}\n\n`);
  logger.appendReport(`Researcher client containers: ${sandbox.researcherStartedCount}/${runtimeResearcherCount} redeemed\n\n`);
  logger.appendReport(`Multi-donor compute verified: ${featureResults.multiDonorCompute ? "yes" : "no"}\n\n`);
  logger.appendReport(`Natural compute orchestration observed: ${featureResults.naturalComputeOrchestration ? "yes" : "no"}\n\n`);
  logger.appendReport(`Multi-user collaboration verified: ${featureResults.multiUserCollaboration ? "yes" : "no"}\n\n`);
  logger.appendReport(`Task review/revision loop verified: ${featureResults.taskReviewLoop ? "yes" : "no"}\n\n`);
  logger.appendReport(`Approved-task-backed Findings/reporting verified: ${featureResults.approvedTaskFindings ? "yes" : "no"}\n\n`);
  logger.appendReport(`Research Spine coding validation observed: ${featureResults.codingValidation ? "yes" : "no"}\n\n`);
  logger.appendReport(`Research Spine structural traceability present: ${scorecard.research_spine_structure_present ? "yes" : "no"}\n\n`);
  logger.appendReport(`Research Spine accepted multi-model validation verified: ${scorecard.research_spine_validation_verified ? "yes" : "no"}\n\n`);
  logger.appendReport(`Telemetry evidence observed: ${featureResults.telemetryEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`ReasoningBank process-memory probe verified: ${featureResults.reasoningBankEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`Memento/skill health probe verified: ${featureResults.mementoSkillEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`Meta-Hyperagent project-scoped probe verified: ${featureResults.metaHyperagentEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`Governed self-improvement proposal path verified: ${featureResults.selfImprovementGovernance ? "yes" : "no"}\n\n`);
  logger.appendReport(`Autoresearch evidence observed: ${featureResults.autoresearchEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`Graph/RAG traceability observed: ${featureResults.ragTraceabilityEvidence ? "yes" : "no"}\n\n`);
  logger.appendReport(`Interview process verified: ${featureResults.interviewProcess ? "yes" : "no"}\n\n`);
  logger.appendReport(`Live model chat verified: ${featureResults.liveChat ? "yes" : "no"}\n\n`);
  logger.appendReport("Credentialed integrations (Figma, Stitch, Telegram/AURA live participant paths): optional in this run unless bounded test tokens are explicitly provided.\n\n");
  const colimaStorage = summarizeColimaStorage(latestColimaStorageSnapshot);
  if (colimaStorage) {
    logger.appendReport(`Colima storage: ${colimaStorage.actual_gb} GB actual, ${colimaStorage.apparent_gb} GB apparent\n\n`);
  }
  logger.appendReport(writeScorecardMarkdown(scorecard));
  logger.appendReport("\n## Actionable Product Improvements\n\n");
  for (const issue of logger.issues.slice(0, 20)) {
    logger.appendReport(`- [${issue.severity}] ${issue.area}: ${issue.title}. ${issue.detail}\n`);
  }
  cleanupRelayClientSandboxes();
  cleanupDonorModelSandboxes();
  stopColimaIfRequested("run-complete");
  logger.finalize({ scorecard, project_id: project?.id || "", uploaded_documents: uploaded.length });
  process.exitCode = benchmarkExitCode({ mode, blockers });
}

main().catch((error) => {
  logger.issue({
    area: "benchmark",
    severity: "critical",
    title: "Benchmark crashed",
    detail: error.stack || error.message,
  });
  const scorecard = buildScorecard({
    mode,
    metrics: logger.metrics,
    integrationMatrix: [],
    blockers: [...blockers, error.message],
    completedTasks: 0,
    chatTurns: 0,
    uploadedDocuments: 0,
    sandbox,
    featureResults,
  });
  logger.writeJson("scorecard.json", scorecard);
  logger.appendReport("\nBenchmark crashed before completing. See `issues.jsonl` and `action-log.jsonl`.\n\n");
  logger.appendReport(writeScorecardMarkdown(scorecard));
  cleanupRelayClientSandboxes();
  cleanupDonorModelSandboxes();
  stopColimaIfRequested("crash");
  logger.finalize({ scorecard });
  process.exitCode = 1;
});
