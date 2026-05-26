import assert from "node:assert/strict";
import test from "node:test";
import { resolve } from "node:path";

import {
  buildDonorModelSandboxConfig,
  dockerArgsForDonorModelSandbox,
  donorEndpointDiversity,
  q4EvidenceFrom,
  validateDonorModelSandbox,
} from "./donor-sandboxes.mjs";

test("q4EvidenceFrom recognizes Q4, 4-bit, and int4 quantization hints", () => {
  assert.equal(q4EvidenceFrom("gemma-4b-Q4_K_M.gguf").ok, true);
  assert.equal(q4EvidenceFrom("quantization=int4").ok, true);
  assert.equal(q4EvidenceFrom("4-bit").ok, true);
  assert.equal(q4EvidenceFrom("gemma-4b-f16.gguf").ok, false);
});

test("buildDonorModelSandboxConfig creates an opt-in llama.cpp donor endpoint", () => {
  const modelFile = resolve("/tmp/istara-models/qwen3.5-4b-q4_k_m.gguf");
  const config = buildDonorModelSandboxConfig({}, 2, {
    donorId: "Donor Two",
    model: "fallback-model",
    runId: "test-run",
    env: {
      ISTARA_BENCHMARK_DONOR_2_MODEL_SERVER: "llama.cpp",
      ISTARA_BENCHMARK_DONOR_2_MODEL_SERVER_PORT: "18122",
      ISTARA_BENCHMARK_DONOR_2_MODEL_FILE: modelFile,
      ISTARA_BENCHMARK_DONOR_2_CPUS: "2",
      ISTARA_BENCHMARK_DONOR_2_MEMORY: "6g",
    },
  });

  assert.equal(config.requested, true);
  assert.equal(config.kind, "llamacpp");
  assert.equal(config.donorId, "donor-two");
  assert.equal(config.hostUrl, "http://host.docker.internal:18122");
  assert.equal(config.hostProbeUrl, "http://127.0.0.1:18122");
  assert.equal(config.image, "ghcr.io/ggml-org/llama.cpp:server");
  assert.equal(config.modelName, "fallback-model");
  assert.equal(config.q4.ok, true);
  assert.equal(config.requireQ4, true);
  assert.equal(config.reasoning, "off");
  assert.equal(config.cpus, "2");
  assert.equal(config.memory, "6g");
});

test("dockerArgsForDonorModelSandbox binds llama.cpp models read-only and exposes only localhost", () => {
  const modelRoot = resolve("/tmp/istara-models");
  const modelFile = resolve(modelRoot, "qwen3.5-4b-q4_k_m.gguf");
  const config = buildDonorModelSandboxConfig({}, 2, {
    donorId: "donor-2",
    runId: "test-run",
    env: {
      ISTARA_BENCHMARK_DONOR_2_MODEL_SERVER: "llamacpp",
      ISTARA_BENCHMARK_DONOR_2_MODEL_SERVER_PORT: "18122",
      ISTARA_BENCHMARK_DONOR_2_MODEL_FILE: modelFile,
    },
  });

  const args = dockerArgsForDonorModelSandbox(config, ["--add-host", "host.docker.internal:host-gateway"]);

  assert.deepEqual(args.slice(0, 4), ["run", "-d", "--name", "istara-donor-model-test-run-donor-2"]);
  assert.ok(args.includes("127.0.0.1:18122:8080"));
  assert.ok(args.includes(`${modelRoot}:/models:ro`));
  assert.ok(args.includes("/models/qwen3.5-4b-q4_k_m.gguf"));
  assert.ok(args.includes("--alias"));
  assert.ok(args.includes("--reasoning"));
  assert.ok(args.includes("off"));
  assert.ok(args.includes("--add-host"));
});

test("donorEndpointDiversity flags donors sharing one physical endpoint", () => {
  const diversity = donorEndpointDiversity([
    { id: "donor-a", provider: "lmstudio", host: "http://host.docker.internal:1234", model: "gemma" },
    { id: "donor-b", provider: "lmstudio", host: "http://host.docker.internal:1234", model: "qwen" },
    { id: "donor-c", provider: "llamacpp", host: "http://host.docker.internal:18123", model: "qwen" },
  ]);

  assert.equal(diversity.donor_count, 3);
  assert.equal(diversity.distinct_endpoint_count, 2);
  assert.equal(diversity.distinct_model_count, 2);
  assert.equal(diversity.distinct, false);
  assert.deepEqual(diversity.duplicate_groups[0].donor_ids, ["donor-a", "donor-b"]);
});

test("validateDonorModelSandbox blocks missing Q4 evidence and missing local model files", () => {
  const issues = validateDonorModelSandbox({
    requested: true,
    kind: "llamacpp",
    requireQ4: true,
    q4: { ok: false },
    modelRoot: "/definitely/missing/istara/models",
    modelFile: "",
  });

  assert.ok(issues.some((issue) => issue.code === "q4-not-proved"));
  assert.ok(issues.some((issue) => issue.code === "model-root-missing"));
  assert.ok(issues.some((issue) => issue.code === "llamacpp-model-file-required"));
});
