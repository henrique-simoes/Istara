/** Scenario 04 — File Upload: generate and upload research data. */

export const name = "File Upload & Ingestion";
export const id = "04-file-upload";

import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { materializeSharedDocumentCorpus } from "../../document_corpus/shared-corpus.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  const tmpDir = join(__dirname, "..", ".results", "generated-data");
  mkdirSync(tmpDir, { recursive: true });

  const corpus = materializeSharedDocumentCorpus({
    outputDir: tmpDir,
    slice: "upload-smoke",
    minimumSources: 8,
    canonicalOnly: true,
  });
  const files = corpus.manifest.map((item) => ({
    path: item.path,
    name: item.file_name,
    type: item.method || item.corpus_source,
  }));

  // Upload each file via API
  for (const file of files) {
    try {
      const result = await api.uploadFile(ctx.projectId, file.path, file.name);
      checks.push({
        name: `Upload ${file.type}: ${file.name}`,
        passed: true,
        detail: `Chunks: ${result.chunks_indexed || result.chunks || "unknown"}`,
      });
    } catch (e) {
      checks.push({ name: `Upload ${file.type}: ${file.name}`, passed: false, detail: e.message });
    }
  }

  // Verify files via API
  try {
    const fileList = await api.get(`/api/files/${ctx.projectId}`);
    const fileCount = fileList.files?.length || (Array.isArray(fileList) ? fileList.length : 0);
    checks.push({ name: "Files listed in API", passed: fileCount >= files.length, detail: `${fileCount} files` });
  } catch (e) {
    checks.push({ name: "Files listed in API", passed: false, detail: e.message });
  }

  // Verify indexing stats
  try {
    const stats = await api.get(`/api/files/${ctx.projectId}/stats`);
    const chunks = stats.total_chunks || stats.indexed_chunks || 0;
    const searchable = stats.searchable_chunks || stats.keyword_chunks || chunks;
    checks.push({
      name: "Chunks searchable",
      passed: searchable > 0,
      detail: `${chunks} vector chunks, ${stats.keyword_chunks || 0} keyword chunks (${stats.indexing_status || "unknown"})`,
    });
  } catch (e) {
    checks.push({ name: "Chunks searchable", passed: false, detail: e.message });
  }

  // Verify in UI — navigate to chat and check
  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);
  await screenshot("04-after-upload");

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
