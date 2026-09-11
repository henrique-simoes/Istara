import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  buildBenchmarkProvenance,
  resolveGitCommitWithoutGit,
  validateBenchmarkProvenance,
} from "./provenance.mjs";

test("resolves a commit from git metadata without invoking host git", () => {
  const root = mkdtempSync(join(tmpdir(), "istara-provenance-"));
  mkdirSync(join(root, ".git", "refs", "heads"), { recursive: true });
  writeFileSync(join(root, ".git", "HEAD"), "ref: refs/heads/testing\n");
  writeFileSync(join(root, ".git", "refs", "heads", "testing"), `${"a".repeat(40)}\n`);

  assert.equal(resolveGitCommitWithoutGit(root), "a".repeat(40));
});

test("authoritative Docker provenance requires explicit engine images and isolation", () => {
  const provenance = buildBenchmarkProvenance({
    sourceSha: "b".repeat(40),
    sourceState: "working-tree-snapshot",
    runnerImage: "node@sha256:" + "c".repeat(64),
    runnerImageId: "sha256:" + "d".repeat(64),
    backendImageId: "sha256:" + "e".repeat(64),
    frontendImageId: "sha256:" + "f".repeat(64),
    engine: "pi",
    isolation: "fresh-postgres-container-per-engine",
    stackProject: "istara-testing",
    runGroup: "comparison-1",
    runOrder: "legacy,pi",
    armIndex: 2,
    sourceSnapshotSha256: "1".repeat(64),
  });

  assert.deepEqual(validateBenchmarkProvenance(provenance), []);
  assert.equal(provenance.execution.host_dependencies_installed, false);
  assert.equal(provenance.execution.container_only, true);
  assert.equal(provenance.source.snapshot_sha256, "1".repeat(64));
  assert.equal(provenance.comparison.arm_index, 2);
  assert.deepEqual(provenance.comparison.run_order, ["legacy", "pi"]);
});

test("missing or mutable provenance is a blocker", () => {
  const failures = validateBenchmarkProvenance(buildBenchmarkProvenance({
    sourceSha: "",
    sourceState: "",
    runnerImage: "node:20-bookworm",
    runnerImageId: "",
    backendImageId: "",
    frontendImageId: "",
    engine: "",
    isolation: "",
    stackProject: "",
    runGroup: "",
    runOrder: "",
    armIndex: 0,
    sourceSnapshotSha256: "",
  }));

  assert.ok(failures.some((item) => item.includes("source commit")));
  assert.ok(failures.some((item) => item.includes("digest-qualified runner image")));
  assert.ok(failures.some((item) => item.includes("engine")));
  assert.ok(failures.some((item) => item.includes("isolation")));
  assert.ok(failures.some((item) => item.includes("snapshot")));
  assert.ok(failures.some((item) => item.includes("run order")));
});
