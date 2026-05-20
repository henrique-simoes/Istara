import { appendFileSync, existsSync, mkdirSync, writeFileSync } from "fs";
import { join } from "path";

export function makeRunId(now = new Date()) {
  return now.toISOString().replace(/[:.]/g, "-");
}

export class BenchmarkLogger {
  constructor({ rootDir, runId, mode }) {
    this.rootDir = rootDir;
    this.runId = runId;
    this.mode = mode;
    this.runDir = join(rootDir, "runs", runId);
    this.paths = {
      logs: join(this.runDir, "logs"),
      screenshots: join(this.runDir, "screenshots"),
      traces: join(this.runDir, "traces"),
      corpus: join(this.runDir, "corpus"),
      uploads: join(this.runDir, "uploads"),
      artifacts: join(this.runDir, "artifacts"),
      network: join(this.runDir, "network"),
      storage: join(this.runDir, "storage"),
    };
    this.issues = [];
    this.metrics = {
      actions: 0,
      chatTurns: 0,
      taskApprovals: 0,
      taskRevisions: 0,
      integrationAttempts: 0,
      screenshots: 0,
    };
    this.sanitizer = null;
  }

  setSanitizer(sanitizer) {
    this.sanitizer = typeof sanitizer === "function" ? sanitizer : null;
  }

  sanitize(value) {
    if (!this.sanitizer) return value;
    return this.sanitizer(value);
  }

  init() {
    mkdirSync(this.runDir, { recursive: true });
    for (const dir of Object.values(this.paths)) {
      mkdirSync(dir, { recursive: true });
    }
    this.writeJson("run-metadata.json", {
      run_id: this.runId,
      mode: this.mode,
      started_at: new Date().toISOString(),
      cwd: process.cwd(),
      node: process.version,
    });
  }

  line(file, payload) {
    const record = {
      ts: new Date().toISOString(),
      run_id: this.runId,
      ...payload,
    };
    const sanitized = this.sanitize(record);
    appendFileSync(join(this.runDir, file), `${JSON.stringify(sanitized)}\n`);
    return sanitized;
  }

  action(step, payload = {}) {
    this.metrics.actions += 1;
    return this.line("action-log.jsonl", { step, ...payload });
  }

  chatTurn(payload) {
    this.metrics.chatTurns += 1;
    return this.line("conversation-turns.jsonl", payload);
  }

  taskReview(payload) {
    if (payload.outcome === "approved") this.metrics.taskApprovals += 1;
    if (payload.outcome === "revision_requested") this.metrics.taskRevisions += 1;
    return this.line("task-review-log.jsonl", payload);
  }

  integrationAttempt(payload) {
    this.metrics.integrationAttempts += 1;
    return this.line("integration-attempts.jsonl", payload);
  }

  issue(issue) {
    const item = {
      ts: new Date().toISOString(),
      severity: issue.severity || "medium",
      area: issue.area || "benchmark",
      title: issue.title,
      detail: issue.detail || "",
      evidence: issue.evidence || {},
    };
    const sanitized = this.sanitize(item);
    this.issues.push(sanitized);
    this.line("issues.jsonl", sanitized);
    return sanitized;
  }

  writeJson(relPath, payload) {
    writeFileSync(join(this.runDir, relPath), JSON.stringify(this.sanitize(payload), null, 2));
  }

  writeRootJson(relPath, payload) {
    mkdirSync(this.rootDir, { recursive: true });
    writeFileSync(join(this.rootDir, relPath), JSON.stringify(this.sanitize(payload), null, 2));
  }

  rootLine(file, payload) {
    mkdirSync(this.rootDir, { recursive: true });
    const record = {
      ts: new Date().toISOString(),
      run_id: this.runId,
      ...payload,
    };
    const sanitized = this.sanitize(record);
    appendFileSync(join(this.rootDir, file), `${JSON.stringify(sanitized)}\n`);
    return sanitized;
  }

  writeText(relPath, content) {
    writeFileSync(join(this.runDir, relPath), content);
  }

  appendReport(content) {
    appendFileSync(join(this.runDir, "report.md"), content);
  }

  noteScreenshot() {
    this.metrics.screenshots += 1;
  }

  finalize(extra = {}) {
    const final = {
      run_id: this.runId,
      mode: this.mode,
      finished_at: new Date().toISOString(),
      metrics: this.metrics,
      issue_count: this.issues.length,
      issues: this.issues,
      ...extra,
    };
    this.writeJson("run-summary.json", final);
    if (!existsSync(join(this.runDir, "report.md"))) {
      this.writeText("report.md", "# Istara Real User Benchmark Report\n\nNo narrative was written before finalize.\n");
    }
    return final;
  }
}
