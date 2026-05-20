import { basename, dirname, resolve } from "path";
import { existsSync, realpathSync, statSync } from "fs";

const DEFAULT_LLAMA_CPP_IMAGE = "ghcr.io/ggml-org/llama.cpp:server";
const DEFAULT_OLLAMA_IMAGE = "ollama/ollama:latest";
const DEFAULT_MODEL_ROOT = "/Users/studio/Istara-Projects/models";
const Q4_PATTERN = /(^|[^a-z0-9])(?:q4(?:[_\-.][a-z0-9]+)?|4bit|4-bit|int4)([^a-z0-9]|$)/i;

function firstNonEmpty(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
  }
  return "";
}

function envValue(env, index, suffixes) {
  for (const suffix of suffixes) {
    const key = `ISTARA_BENCHMARK_DONOR_${index}_${suffix}`;
    const value = env[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      return { value: String(value).trim(), source: key };
    }
  }
  return { value: "", source: "" };
}

function parseBoolean(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "boolean") return value;
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return fallback;
}

function parsePort(value, fallback) {
  const parsed = Number.parseInt(String(value || ""), 10);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 65535) return fallback;
  return parsed;
}

function sanitizeId(value) {
  return String(value || "donor")
    .replace(/[^a-z0-9_.-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80)
    .toLowerCase() || "donor";
}

function isSubpath(child, parent) {
  const childReal = realpathSync(child);
  const parentReal = realpathSync(parent);
  return childReal === parentReal || childReal.startsWith(`${parentReal}/`);
}

export function q4EvidenceFrom(...values) {
  const joined = values.filter(Boolean).map((value) => String(value)).join(" ");
  const match = joined.match(Q4_PATTERN);
  return {
    ok: Boolean(match),
    evidence: match ? match[0].trim() : "",
  };
}

export function buildDonorModelSandboxConfig(rawProfile = {}, index = 1, options = {}) {
  const env = options.env || process.env;
  const donorId = sanitizeId(options.donorId || rawProfile.id || rawProfile.name || `donor-${index}`);
  const serverEnv = envValue(env, index, ["MODEL_SERVER", "MODEL_SANDBOX", "SANDBOX_MODEL_SERVER"]);
  const kind = firstNonEmpty(
    serverEnv.value,
    rawProfile.model_server,
    rawProfile.modelServer,
    rawProfile.model_sandbox,
    rawProfile.modelSandbox,
  ).toLowerCase();

  if (!kind || ["0", "false", "no", "none", "external"].includes(kind)) {
    return { requested: false, enabled: false, kind: "external" };
  }

  const normalizedKind = kind === "llama.cpp" || kind === "llama-cpp" ? "llamacpp" : kind;
  const provider = normalizedKind === "ollama" ? "ollama" : "llamacpp";
  const hostPort = parsePort(
    firstNonEmpty(
      envValue(env, index, ["MODEL_SERVER_PORT", "MODEL_PORT", "SANDBOX_MODEL_PORT"]).value,
      rawProfile.model_server_port,
      rawProfile.modelServerPort,
    ),
    18110 + index,
  );
  const containerPort = provider === "ollama" ? 11434 : 8080;
  const modelRoot = resolve(firstNonEmpty(
    envValue(env, index, ["MODEL_ROOT", "MODEL_DIR_ROOT"]).value,
    rawProfile.model_root,
    rawProfile.modelRoot,
    env.ISTARA_BENCHMARK_MODEL_ROOT,
    DEFAULT_MODEL_ROOT,
  ));
  const modelFile = firstNonEmpty(
    envValue(env, index, ["MODEL_FILE", "GGUF", "GGUF_FILE"]).value,
    rawProfile.model_file,
    rawProfile.modelFile,
    rawProfile.gguf,
    rawProfile.gguf_file,
  );
  const modelDir = resolve(firstNonEmpty(
    envValue(env, index, ["MODEL_DIR", "OLLAMA_MODELS_DIR"]).value,
    rawProfile.model_dir,
    rawProfile.modelDir,
    modelFile ? dirname(modelFile) : modelRoot,
  ));
  const modelName = firstNonEmpty(
    envValue(env, index, ["LLM_MODEL", "MODEL", "MODEL_ID"]).value,
    rawProfile.model,
    rawProfile.llm_model,
    options.model,
    modelFile ? basename(modelFile) : "",
    "default",
  );
  const quantization = firstNonEmpty(
    envValue(env, index, ["QUANTIZATION", "MODEL_QUANTIZATION"]).value,
    rawProfile.quantization,
    rawProfile.model_quantization,
  );
  const q4 = q4EvidenceFrom(quantization, modelName, modelFile);
  const requireQ4 = parseBoolean(
    firstNonEmpty(
      envValue(env, index, ["REQUIRE_Q4", "REQUIRE_Q4_QUANTIZATION"]).value,
      rawProfile.require_q4,
      rawProfile.requireQ4,
      env.ISTARA_BENCHMARK_REQUIRE_Q4_DONORS,
    ),
    true,
  );
  const containerName = sanitizeId(firstNonEmpty(
    envValue(env, index, ["MODEL_SERVER_CONTAINER", "MODEL_CONTAINER"]).value,
    rawProfile.model_server_container,
    rawProfile.modelServerContainer,
    `istara-donor-model-${options.runId || "run"}-${donorId}`,
  ));

  return {
    requested: true,
    enabled: true,
    kind: provider,
    source: serverEnv.source || "donor-profile",
    donorId,
    containerName,
    image: firstNonEmpty(
      envValue(env, index, ["MODEL_SERVER_IMAGE", "MODEL_IMAGE"]).value,
      rawProfile.model_server_image,
      rawProfile.modelServerImage,
      provider === "ollama" ? DEFAULT_OLLAMA_IMAGE : DEFAULT_LLAMA_CPP_IMAGE,
    ),
    hostPort,
    containerPort,
    hostUrl: `http://host.docker.internal:${hostPort}`,
    hostProbeUrl: `http://127.0.0.1:${hostPort}`,
    modelRoot,
    modelDir,
    modelFile: modelFile ? resolve(modelFile) : "",
    modelName,
    quantization,
    q4,
    requireQ4,
    contextLength: Number.parseInt(firstNonEmpty(
      envValue(env, index, ["CONTEXT_LENGTH", "N_CTX"]).value,
      rawProfile.context_length,
      rawProfile.contextLength,
      "4096",
    ), 10) || 4096,
    reasoning: firstNonEmpty(
      envValue(env, index, ["REASONING", "THINKING"]).value,
      rawProfile.reasoning,
      rawProfile.thinking,
      "off",
    ),
    cpus: firstNonEmpty(
      envValue(env, index, ["CPUS", "CPU_LIMIT"]).value,
      rawProfile.cpus,
      rawProfile.cpu_limit,
      "",
    ),
    memory: firstNonEmpty(
      envValue(env, index, ["MEMORY", "MEMORY_LIMIT"]).value,
      rawProfile.memory,
      rawProfile.memory_limit,
      "",
    ),
    allowPull: parseBoolean(
      firstNonEmpty(
        envValue(env, index, ["ALLOW_PULL", "ALLOW_MODEL_PULL"]).value,
        rawProfile.allow_pull,
        rawProfile.allowPull,
      ),
      false,
    ),
  };
}

export function validateDonorModelSandbox(config) {
  const issues = [];
  if (!config?.requested) return issues;
  if (!["llamacpp", "ollama"].includes(config.kind)) {
    issues.push({ severity: "critical", code: "unsupported-model-server", detail: `Unsupported donor model server: ${config.kind}` });
  }
  if (config.requireQ4 && !config.q4?.ok) {
    issues.push({ severity: "critical", code: "q4-not-proved", detail: "Donor model sandbox requires Q4/4-bit quantization evidence in the model id, model file, or quantization field." });
  }
  if (!existsSync(config.modelRoot) || !statSync(config.modelRoot).isDirectory()) {
    issues.push({ severity: "critical", code: "model-root-missing", detail: `Model root does not exist: ${config.modelRoot}` });
  }
  if (config.kind === "llamacpp") {
    if (!config.modelFile) {
      issues.push({ severity: "critical", code: "llamacpp-model-file-required", detail: "llama.cpp donor sandboxes require DONOR_N_MODEL_FILE or donor model_file." });
    } else if (!existsSync(config.modelFile) || !statSync(config.modelFile).isFile()) {
      issues.push({ severity: "critical", code: "model-file-missing", detail: `Model file does not exist: ${config.modelFile}` });
    } else {
      try {
        if (!isSubpath(config.modelFile, config.modelRoot)) {
          issues.push({ severity: "critical", code: "model-file-outside-root", detail: "Model file must live under the configured benchmark model root." });
        }
      } catch (error) {
        issues.push({ severity: "critical", code: "model-file-realpath-failed", detail: error.message });
      }
    }
  }
  if (config.kind === "ollama") {
    if (!existsSync(config.modelDir) || !statSync(config.modelDir).isDirectory()) {
      issues.push({ severity: "critical", code: "ollama-model-dir-missing", detail: `Ollama model directory does not exist: ${config.modelDir}` });
    }
    if (!config.allowPull && config.modelName === "default") {
      issues.push({ severity: "critical", code: "ollama-model-name-required", detail: "Ollama donor sandboxes require a configured model name when pulls are disabled." });
    }
  }
  return issues;
}

export function dockerArgsForDonorModelSandbox(config, extraHostArgs = []) {
  const common = [
    "run",
    "-d",
    "--name",
    config.containerName,
    ...extraHostArgs,
    "-p",
    `127.0.0.1:${config.hostPort}:${config.containerPort}`,
    "--label",
    "istara.benchmark.role=donor-model",
    "--label",
    `istara.benchmark.donor=${config.donorId}`,
  ];
  if (config.cpus) common.push("--cpus", config.cpus);
  if (config.memory) common.push("--memory", config.memory);

  if (config.kind === "ollama") {
    return [
      ...common,
      "-v",
      `${config.modelDir}:/root/.ollama`,
      config.image,
    ];
  }

  return [
    ...common,
    "-v",
    `${dirname(config.modelFile)}:/models:ro`,
    config.image,
    "-m",
    `/models/${basename(config.modelFile)}`,
    "--host",
    "0.0.0.0",
    "--port",
    String(config.containerPort),
    "--alias",
    config.modelName,
    "-c",
    String(config.contextLength),
    "--reasoning",
    config.reasoning || "off",
  ];
}

export function endpointKey(profile) {
  return [
    profile.provider || "",
    profile.host || "",
  ].map((value) => String(value).trim().toLowerCase()).join("|");
}

export function donorEndpointDiversity(profiles = []) {
  const groups = new Map();
  const modelKeys = new Set();
  for (const profile of profiles) {
    const key = endpointKey(profile);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(profile.id);
    modelKeys.add(String(profile.model || "").trim().toLowerCase());
  }
  const duplicateGroups = [...groups.entries()]
    .filter(([, ids]) => ids.length > 1)
    .map(([key, ids]) => ({ key, donor_ids: ids }));
  return {
    donor_count: profiles.length,
    distinct_endpoint_count: groups.size,
    distinct_model_count: modelKeys.size,
    duplicate_groups: duplicateGroups,
    distinct: duplicateGroups.length === 0,
  };
}

export function summarizeDonorModelSandbox(config) {
  if (!config?.requested) return { requested: false };
  return {
    requested: true,
    kind: config.kind,
    donor_id: config.donorId,
    container_name: config.containerName,
    image: config.image,
    host_port: config.hostPort,
    container_port: config.containerPort,
    model_root: config.modelRoot,
    model_dir_configured: Boolean(config.modelDir),
    model_file_configured: Boolean(config.modelFile),
    model_file_name: config.modelFile ? basename(config.modelFile) : "",
    model_configured: Boolean(config.modelName && config.modelName !== "default"),
    quantization_configured: Boolean(config.quantization),
    q4_required: Boolean(config.requireQ4),
    q4_evidence_present: Boolean(config.q4?.ok),
    q4_evidence: config.q4?.evidence || "",
    reasoning: config.reasoning || "",
    allow_pull: Boolean(config.allowPull),
    cpus_configured: Boolean(config.cpus),
    memory_configured: Boolean(config.memory),
  };
}
