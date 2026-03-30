#!/usr/bin/env node
/**
 * Seed a Istara project with all generated fixture data.
 *
 * 1. Creates a "UX Research Demo" project via the API
 * 2. Uploads all fixture files
 * 3. Triggers a file scan so the watcher creates research tasks
 *
 * Usage:
 *   node tests/simulation/data/seed-project.mjs [--base-url http://localhost:8000]
 */

import { readdirSync, readFileSync, statSync } from "fs";
import { basename, join, dirname, extname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturesDir = join(__dirname, "fixtures");

// Parse CLI args
const args = process.argv.slice(2);
let baseUrl = "http://localhost:8000";
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--base-url" && args[i + 1]) {
    baseUrl = args[i + 1];
    i++;
  }
}

const api = (path) => `${baseUrl}/api${path}`;

async function main() {
  console.log("=== Istara Project Seeder ===\n");
  console.log(`API: ${baseUrl}\n`);

  // 1. Check API health
  try {
    const res = await fetch(api("/settings/status"));
    if (!res.ok) throw new Error(`Status ${res.status}`);
    console.log("API is reachable.\n");
  } catch (e) {
    console.error(`Cannot reach API at ${baseUrl}: ${e.message}`);
    console.error("Make sure the backend is running: cd backend && uvicorn app.main:app");
    process.exit(1);
  }

  // 2. Create project
  console.log("Creating project...");
  const projectRes = await fetch(api("/projects"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "UX Research Demo",
      description:
        "Demo project seeded with mock research data for testing all Istara skills and agent workflows.",
      phase: "discover",
      company_context:
        "Mid-size B2B SaaS company (200 employees). Product is a project management platform targeting teams of 5-50. Key competitors: Asana, Monday.com, ClickUp.",
      project_context:
        "Evaluating a major redesign of the onboarding flow, dashboard, and collaboration features. Research covers interviews, surveys, usability tests, diary studies, competitive analysis, and analytics review.",
      guardrails:
        "All findings must cite source documents. Recommendations must reference at least one insight. Quantitative claims require sample sizes. Do not generalize from single data points.",
    }),
  });

  if (!projectRes.ok) {
    const err = await projectRes.text();
    console.error(`Failed to create project: ${err}`);
    process.exit(1);
  }

  const project = await projectRes.json();
  console.log(`Project created: ${project.name} (${project.id})\n`);

  // 3. Upload all fixture files
  const files = readdirSync(fixturesDir).filter((f) => !f.startsWith("."));
  console.log(`Uploading ${files.length} files...\n`);

  let uploaded = 0;
  let errors = 0;

  for (const file of files) {
    const filePath = join(fixturesDir, file);
    const stat = statSync(filePath);
    if (!stat.isFile()) continue;

    const ext = extname(file).toLowerCase();
    const mimeTypes = {
      ".txt": "text/plain",
      ".md": "text/markdown",
      ".csv": "text/csv",
      ".pdf": "application/pdf",
      ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    };
    const contentType = mimeTypes[ext] || "application/octet-stream";

    try {
      const fileContent = readFileSync(filePath);
      const formData = new FormData();
      formData.append("file", new Blob([fileContent], { type: contentType }), file);

      const uploadRes = await fetch(api(`/files/upload/${project.id}`), {
        method: "POST",
        body: formData,
      });

      if (uploadRes.ok) {
        uploaded++;
        const result = await uploadRes.json();
        const chunks = result.chunks_indexed || 0;
        process.stdout.write(`  [${uploaded}/${files.length}] ${file} — ${chunks} chunks\n`);
      } else {
        errors++;
        const err = await uploadRes.text();
        process.stdout.write(`  [ERROR] ${file}: ${err}\n`);
      }
    } catch (e) {
      errors++;
      process.stdout.write(`  [ERROR] ${file}: ${e.message}\n`);
    }
  }

  console.log(`\nUploaded: ${uploaded}, Errors: ${errors}\n`);

  // 4. Trigger file scan (creates research tasks via file watcher classification)
  console.log("Triggering file scan (auto-creates research tasks)...");
  try {
    const scanRes = await fetch(api(`/files/${project.id}/scan`), {
      method: "POST",
    });
    if (scanRes.ok) {
      const scanResult = await scanRes.json();
      console.log(`Scan complete: ${scanResult.scanned} files processed.\n`);
    } else {
      console.log(`Scan returned ${scanRes.status} — tasks may already have been created during upload.\n`);
    }
  } catch (e) {
    console.log(`Scan request failed: ${e.message} — this is OK if the watcher isn't running.\n`);
  }

  // 5. Report
  console.log("=== Seeding Complete ===");
  console.log(`Project ID: ${project.id}`);
  console.log(`Files uploaded: ${uploaded}`);
  console.log(`\nNext steps:`);
  console.log(`  1. Open Istara in your browser`);
  console.log(`  2. Select the "${project.name}" project`);
  console.log(`  3. Check the Tasks view — research tasks should appear`);
  console.log(`  4. The agent will start processing tasks automatically`);
}

main().catch((e) => {
  console.error("Fatal error:", e);
  process.exit(1);
});
