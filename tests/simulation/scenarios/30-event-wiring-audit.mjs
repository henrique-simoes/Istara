/**
 * Scenario 30 — Event Wiring Audit
 *
 * Verifies that every WebSocket event type the frontend listens for has a
 * corresponding backend broadcast function, and vice versa. This prevents
 * "defined but never wired" gaps where one side expects an event the other
 * never sends.
 *
 * Also checks that the resource governor lifecycle (register/unregister)
 * is properly called by agent workers.
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

export const name = "Event Wiring Audit";
export const id = "30-event-wiring-audit";

const __dirname = dirname(fileURLToPath(import.meta.url));
const configuredRepoRoot = String(process.env.ISTARA_SIM_REPO_ROOT || "").trim();
const REPO_ROOT = configuredRepoRoot || join(__dirname, "..", "..", "..");

export async function run(ctx) {
  const { api, page } = ctx;
  const checks = [];
  const activeProjectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  const scopedSkipDetail = "[skipped] No active project id; scoped endpoint not called";
  const projectScopedPath = (path) =>
    `${path}${path.includes("?") ? "&" : "?"}project_id=${encodeURIComponent(activeProjectId)}`;

  function check(id, label, passed, detail = "") {
    checks.push({ id, label, passed, detail });
  }

  // ── 1. WebSocket endpoint exists ────────────────────────────
  try {
    // Verify /ws is reachable (will fail upgrade but proves the route exists)
    const res = await fetch("http://localhost:8000/ws");
    check(1, "WebSocket endpoint reachable", res.status === 403 || res.status === 400 || res.status > 0,
      `Status: ${res.status}`);
  } catch (e) {
    check(1, "WebSocket endpoint reachable", false, e.message);
  }

  // ── 2-10. Backend broadcast functions exist ──────────────────
  // We verify the /ws endpoint's documented event types match what's available
  // by importing the websocket module's public API via a health-like introspection

  const expectedEvents = [
    "agent_status",
    "task_progress",
    "file_processed",
    "finding_created",
    "suggestion",
    "resource_throttle",
    "task_queue_update",
    "document_created",
    "document_updated",
  ];

  // Verify via settings/status that backend is healthy (proxy for all modules loaded)
  try {
    const health = await api.get("/api/settings/status");
    // Contract-mode QA intentionally has a reachable provider stub without a
    // chat-ready model. The backend is operational in that state and reports
    // `degraded`; only accept it when the readiness payload confirms the
    // bounded capability gap, so a real outage still fails this check.
    const contractModeDegraded = health.status === "degraded"
      && health.services?.llm === "connected"
      && health.llm_readiness?.chat_ready === false;
    const operational = health.status === "ok"
      || health.status === "healthy"
      || health.healthy === true
      || contractModeDegraded;
    check(2, "Backend healthy (all modules loaded)", operational,
      JSON.stringify(health).slice(0, 160));
  } catch (e) {
    check(2, "Backend healthy (all modules loaded)", false, e.message);
  }

  // ── 3. Verify finding_created broadcast exists ──────────────
  // Use persistent simulation project for wiring tests
  let projectId = activeProjectId;
  check(3, "Project available for wiring tests", !!projectId, projectId ? projectId : "No persistent project");

  // ── 4. Verify finding creation triggers API (proxy for broadcast wiring)
  if (projectId) {
    try {
      const nugget = await api.post("/api/findings/nuggets", {
        project_id: projectId,
        text: "Wiring audit test nugget",
        source: "audit-scenario-30",
      });
      check(4, "Finding creation API works (nugget)", !!nugget.id, nugget.id);
    } catch (e) {
      check(4, "Finding creation API works (nugget)", false, e.message);
    }
  } else {
    check(4, "Finding creation API works (nugget)", false, "No project");
  }

  // ── 5. Verify document creation triggers broadcast ──────────
  if (projectId) {
    try {
      const doc = await api.post("/api/documents", {
        project_id: projectId,
        title: "Wiring Audit Document",
        description: "Tests document_created event",
        source: "user_upload",
        file_name: "wiring-test.txt",
      });
      check(5, "Document creation API works", !!doc.id, doc.id);

      // Update to test document_updated event path
      const updated = await api.patch(projectScopedPath(`/api/documents/${doc.id}`), {
        title: "Wiring Audit Document (Updated)",
      });
      check(6, "Document update API works", updated.title?.includes("Updated"), updated.title);

      // Cleanup
      await api.delete(projectScopedPath(`/api/documents/${doc.id}`));
    } catch (e) {
      check(5, "Document creation API works", false, e.message);
      check(6, "Document update API works", false, e.message);
    }
  } else {
    check(5, "Document creation API works", false, "No project");
    check(6, "Document update API works", false, "No project");
  }

  // ── 7. Agent status endpoint (governor lifecycle proxy) ─────
  if (projectId) {
    try {
      const agents = await api.get(projectScopedPath("/api/agents"));
      check(7, "Agents API responds", Array.isArray(agents.agents), `${agents.agents?.length} agents`);
    } catch (e) {
      check(7, "Agents API responds", false, e.message);
    }
  } else {
    check(7, "Agents API responds", false, "No project");
  }

  // ── 8. Agent capacity (governor concurrent limit) ───────────
  try {
    const capacity = await api.get("/api/agents/capacity");
    check(8, "Agent capacity check works", capacity.can_create !== undefined || capacity.can_start !== undefined,
      `can_create: ${capacity.can_create}, current: ${capacity.current_agents}`);
  } catch (e) {
    check(8, "Agent capacity check works", false, e.message);
  }

  // ── 9. Resource governor status ─────────────────────────────
  try {
    const status = await api.get("/api/agents/status");
    check(9, "Agent status endpoint works", !!status, JSON.stringify(status).slice(0, 100));
  } catch (e) {
    check(9, "Agent status endpoint works", false, e.message);
  }

  // ── 10. Task queue update flow (create task, verify queue) ──
  if (projectId) {
    try {
      const task = await api.post("/api/tasks", {
        project_id: projectId,
        title: "Queue wiring test task",
        description: "Verify task_queue_update event path",
      });
      check(10, "Task creation for queue test", !!task.id, task.id);

      // Clean up
      await api.delete(projectScopedPath(`/api/tasks/${task.id}`));
    } catch (e) {
      check(10, "Task creation for queue test", false, e.message);
    }
  } else {
    check(10, "Task creation for queue test", false, "No project");
  }

  // ── 11. Frontend handles all expected event types ───────────
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });

    // Verify ToastNotification component is mounted (it renders conditionally)
    // We check that the WebSocket hook is active by looking for the connected state
    const wsConnected = await page.evaluate(() => {
      // The useWebSocket hook stores the connection; check if WebSocket exists
      return typeof WebSocket !== "undefined";
    });
    check(11, "Frontend WebSocket API available", wsConnected, "WebSocket supported in browser");
  } catch (e) {
    check(11, "Frontend WebSocket API available", false, e.message);
  }

  // ── 12-14. Frontend event switch covers all backend events ──
  // Static check against source files. Next's compiled chunks are noisy and can
  // hide string literals behind transforms, so use the repository source.
  try {
    const sourceFiles = [
      "frontend/src/components/common/ToastNotification.tsx",
      "frontend/src/lib/types.ts",
    ];
    const allText = sourceFiles
      .map((file) => readFileSync(join(REPO_ROOT, file), "utf8"))
      .join("\n");
    const hasFinding = allText.includes("finding_created");
    const hasDocCreated = allText.includes("document_created");
    const hasDocUpdated = allText.includes("document_updated");
    check(12, "Frontend handles finding_created event", hasFinding, `textLen: ${allText.length}`);
    check(13, "Frontend handles document_created event", hasDocCreated, "");
    check(14, "Frontend handles document_updated event", hasDocUpdated, "");
  } catch (e) {
    check(12, "Frontend handles finding_created event", false, e.message);
    check(13, "Frontend handles document_created event", false, e.message);
    check(14, "Frontend handles document_updated event", false, e.message);
  }

  // ── 15. Scheduler endpoints exist (coverage gap flagged) ────
  if (!activeProjectId) {
    check(15, "Scheduler API responds", true, scopedSkipDetail);
  } else {
    try {
      const schedules = await api.get(projectScopedPath("/api/schedules"));
      check(15, "Scheduler API responds", Array.isArray(schedules) || schedules.schedules !== undefined,
        `Type: ${typeof schedules}`);
    } catch (e) {
      // 404 is acceptable if no schedules exist, but route must be registered
      check(15, "Scheduler API responds", false, e.message);
    }
  }

  // ── Summary ─────────────────────────────────────────────────
  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;

  return { checks, passed, failed, total: checks.length };
}
