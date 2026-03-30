#!/usr/bin/env node
/**
 * Generate all mock research data fixtures for Istara testing.
 *
 * Creates ~64 files across all research types so every skill has data to work with.
 *
 * Usage:
 *   node tests/simulation/data/generate-fixtures.mjs
 */

import { mkdirSync, writeFileSync, readdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

import { generateTranscript } from "./generators/interviews.mjs";
import { generateSurveyCSV } from "./generators/surveys.mjs";
import { generateFieldNotes } from "./generators/research-notes.mjs";
import { generateUsabilityReport } from "./generators/usability-tests.mjs";
import { generateDiaryStudy } from "./generators/diary-entries.mjs";
import { generateCompetitorProfile } from "./generators/competitive-analysis.mjs";
import {
  generateDailyMetrics,
  generateFunnelData,
  generateABTestResults,
} from "./generators/analytics-export.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturesDir = join(__dirname, "fixtures");

// Ensure fixtures directory exists
mkdirSync(fixturesDir, { recursive: true });

let totalFiles = 0;

function save(filename, content) {
  writeFileSync(join(fixturesDir, filename), content, "utf-8");
  totalFiles++;
  process.stdout.write(`  [${totalFiles}] ${filename}\n`);
}

console.log("=== Istara Fixture Generator ===\n");

// ── Interview Transcripts (32 files: 4 per topic × 8 topics) ──────────
console.log("Generating interview transcripts...");
for (let i = 0; i < 32; i++) {
  const { filename, content } = generateTranscript(1);
  // Ensure unique filenames by appending index
  const uniqueName = filename.replace(".txt", `-${String(i + 1).padStart(2, "0")}.txt`);
  save(uniqueName, content);
}

// ── Survey CSVs (5 files, 50 respondents each) ────────────────────────
console.log("\nGenerating survey data...");
for (let i = 0; i < 5; i++) {
  const { filename, content } = generateSurveyCSV(50);
  const uniqueName = filename.replace(".csv", `-${String(i + 1).padStart(2, "0")}.csv`);
  save(uniqueName, content);
}

// ── Field Research Notes (8 files, 1 per topic) ───────────────────────
console.log("\nGenerating field research notes...");
for (let i = 0; i < 8; i++) {
  const { filename, content } = generateFieldNotes();
  const uniqueName = filename.replace(".md", `-${String(i + 1).padStart(2, "0")}.md`);
  save(uniqueName, content);
}

// ── Usability Test Reports (8 files, 1 per topic) ─────────────────────
console.log("\nGenerating usability test reports...");
for (let i = 0; i < 8; i++) {
  const { filename, content } = generateUsabilityReport(6);
  const uniqueName = filename.replace(".md", `-${String(i + 1).padStart(2, "0")}.md`);
  save(uniqueName, content);
}

// ── Diary Studies (5 files, 14-day studies) ────────────────────────────
console.log("\nGenerating diary studies...");
for (let i = 0; i < 5; i++) {
  const { filename, content } = generateDiaryStudy(14);
  const uniqueName = filename.replace(".md", `-${String(i + 1).padStart(2, "0")}.md`);
  save(uniqueName, content);
}

// ── Competitive Analysis (5 files) ────────────────────────────────────
console.log("\nGenerating competitive analysis profiles...");
for (let i = 0; i < 5; i++) {
  const { filename, content } = generateCompetitorProfile();
  const uniqueName = filename.replace(".md", `-${String(i + 1).padStart(2, "0")}.md`);
  save(uniqueName, content);
}

// ── Analytics CSVs (3 types) ──────────────────────────────────────────
console.log("\nGenerating analytics data...");
{
  const { filename, content } = generateDailyMetrics(90);
  save(filename, content);
}
{
  const { filename, content } = generateFunnelData();
  save(filename, content);
}
{
  const { filename, content } = generateABTestResults();
  save(filename, content);
}

// ── Summary ───────────────────────────────────────────────────────────
const fixtureFiles = readdirSync(fixturesDir).filter((f) => !f.startsWith("."));
console.log(`\n=== Done! Generated ${totalFiles} files (${fixtureFiles.length} total in fixtures/) ===`);
console.log(`Location: ${fixturesDir}`);
