import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";

const SHA1 = /^[0-9a-f]{40}$/i;
const SHA256 = /^[0-9a-f]{64}$/i;
const IMAGE_ID = /^sha256:[0-9a-f]{64}$/i;

function readTrimmed(path) {
  try {
    return readFileSync(path, "utf8").trim();
  } catch {
    return "";
  }
}

function resolveGitDir(repoRoot) {
  const marker = join(repoRoot, ".git");
  if (!existsSync(marker)) return "";
  try {
    if (statSync(marker).isDirectory()) return marker;
  } catch {
    return "";
  }
  const pointer = readTrimmed(marker).match(/^gitdir:\s*(.+)$/i)?.[1]?.trim();
  if (!pointer) return "";
  return isAbsolute(pointer) ? pointer : resolve(dirname(marker), pointer);
}

export function resolveGitCommitWithoutGit(repoRoot) {
  const gitDir = resolveGitDir(repoRoot);
  if (!gitDir) return "";
  const head = readTrimmed(join(gitDir, "HEAD"));
  if (SHA1.test(head)) return head.toLowerCase();
  const ref = head.match(/^ref:\s*(.+)$/)?.[1]?.trim();
  if (!ref) return "";
  const loose = readTrimmed(join(gitDir, ref));
  if (SHA1.test(loose)) return loose.toLowerCase();
  const packed = readTrimmed(join(gitDir, "packed-refs"));
  for (const line of packed.split(/\r?\n/)) {
    if (!line || line.startsWith("#") || line.startsWith("^")) continue;
    const [sha, name] = line.trim().split(/\s+/, 2);
    if (name === ref && SHA1.test(sha)) return sha.toLowerCase();
  }
  return "";
}

export function buildBenchmarkProvenance({
  sourceSha = "",
  sourceState = "",
  runnerImage = "",
  runnerImageId = "",
  backendImageId = "",
  frontendImageId = "",
  engine = "",
  isolation = "",
  stackProject = "",
  runGroup = "",
  runOrder = "",
  armIndex = 0,
  sourceSnapshotSha256 = "",
} = {}) {
  const normalizedRunOrder = Array.isArray(runOrder)
    ? runOrder
    : String(runOrder || "").split(",");
  return {
    source: {
      commit: String(sourceSha || "").trim().toLowerCase(),
      state: String(sourceState || "").trim(),
      snapshot_sha256: String(sourceSnapshotSha256 || "").trim().toLowerCase(),
    },
    images: {
      runner_reference: String(runnerImage || "").trim(),
      runner_id: String(runnerImageId || "").trim(),
      backend_id: String(backendImageId || "").trim(),
      frontend_id: String(frontendImageId || "").trim(),
    },
    comparison: {
      engine: String(engine || "").trim(),
      isolation: String(isolation || "").trim(),
      stack_project: String(stackProject || "").trim(),
      run_group: String(runGroup || "").trim(),
      run_order: normalizedRunOrder.map((item) => String(item).trim()).filter(Boolean),
      arm_index: Number(armIndex),
    },
    execution: {
      container_only: true,
      host_dependencies_installed: false,
      dependency_install_location: "disposable-runner-container",
    },
  };
}

export function validateBenchmarkProvenance(provenance) {
  const failures = [];
  if (!SHA1.test(provenance?.source?.commit || "")) {
    failures.push("Benchmark provenance is missing a valid source commit.");
  }
  if (!provenance?.source?.state) {
    failures.push("Benchmark provenance is missing the source-state declaration.");
  }
  if (!SHA256.test(provenance?.source?.snapshot_sha256 || "")) {
    failures.push("Benchmark provenance is missing a valid source snapshot sha256.");
  }
  if (!/@sha256:[0-9a-f]{64}$/i.test(provenance?.images?.runner_reference || "")) {
    failures.push("Benchmark provenance is missing a digest-qualified runner image.");
  }
  for (const [label, value] of [
    ["runner", provenance?.images?.runner_id],
    ["backend", provenance?.images?.backend_id],
    ["frontend", provenance?.images?.frontend_id],
  ]) {
    if (!IMAGE_ID.test(value || "")) failures.push(`Benchmark provenance is missing the ${label} image ID.`);
  }
  if (!['legacy', 'pi'].includes(provenance?.comparison?.engine || "")) {
    failures.push("Benchmark provenance is missing an explicit legacy or pi engine.");
  }
  if (!provenance?.comparison?.isolation) {
    failures.push("Benchmark provenance is missing the state-isolation declaration.");
  }
  if (!provenance?.comparison?.stack_project || !provenance?.comparison?.run_group) {
    failures.push("Benchmark provenance is missing the comparison group or stack project.");
  }
  const runOrder = provenance?.comparison?.run_order;
  if (!Array.isArray(runOrder) || runOrder.length < 1 || runOrder.some((engine) => !['legacy', 'pi'].includes(engine))) {
    failures.push("Benchmark provenance is missing a valid engine run order.");
  }
  const armIndex = provenance?.comparison?.arm_index;
  if (!Number.isInteger(armIndex) || armIndex < 1 || armIndex > (runOrder?.length || 0)) {
    failures.push("Benchmark provenance is missing a valid comparison arm index.");
  }
  return failures;
}
