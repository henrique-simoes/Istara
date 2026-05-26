#!/usr/bin/env node

import { readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const CHECK_ROOTS = [
  "run.mjs",
  "data",
  "evaluators",
  "lib",
  "scenarios",
];
const SKIP_DIRS = new Set([".results", "node_modules", "test-results"]);

function collectJavaScriptFiles(path) {
  const entries = readdirSync(path, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) {
        files.push(...collectJavaScriptFiles(child));
      }
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".mjs")) {
      files.push(child);
    }
  }
  return files;
}

function expandCheckRoot(entry) {
  const path = join(ROOT, entry);
  if (entry.endsWith(".mjs")) {
    return [path];
  }
  return collectJavaScriptFiles(path);
}

const files = CHECK_ROOTS.flatMap(expandCheckRoot).sort();
const failures = [];

for (const file of files) {
  const result = spawnSync(process.execPath, ["--check", file], {
    cwd: ROOT,
    encoding: "utf-8",
  });
  if (result.status !== 0) {
    failures.push({
      file: relative(ROOT, file),
      stderr: result.stderr.trim(),
      stdout: result.stdout.trim(),
    });
  }
}

if (failures.length > 0) {
  console.error("Simulation static syntax check failed:");
  for (const failure of failures) {
    console.error(`- ${failure.file}`);
    if (failure.stderr) console.error(failure.stderr);
    if (failure.stdout) console.error(failure.stdout);
  }
  process.exit(1);
}

console.log(`Simulation static syntax check passed for ${files.length} files.`);
