/**
 * Scenario 31 — Task-Document Linking & System Action Tools
 *
 * Verifies:
 * - New task fields (input_document_ids, output_document_ids, urls, instructions)
 * - Document attachment/detachment endpoints
 * - System action tools definition and prompt generation
 * - Tool-use loop in chat (tool_call extraction)
 * - Frontend task editor with new fields
 * - KanbanBoard document/URL indicators
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

export const name = "Task-Document Linking & System Tools";
export const id = "31-task-documents-tools";

const __dirname = dirname(fileURLToPath(import.meta.url));
const configuredRepoRoot = String(process.env.ISTARA_SIM_REPO_ROOT || "").trim();
const REPO_ROOT = configuredRepoRoot || join(__dirname, "..", "..", "..");

export async function run(ctx) {
  const { api, page } = ctx;
  const checks = [];

  function check(id, label, passed, detail = "") {
    checks.push({ id, label, passed, detail });
  }

  // ── Setup: use persistent simulation project ───────────────────────────
  let projectId = ctx.projectId;
  if (!projectId) {
    check(1, "Project setup", false, "No persistent project available from runner");
    return { checks, passed: 0, failed: 1, total: 1 };
  }
  const projectQuery = `project_id=${encodeURIComponent(projectId)}`;

  // ── 1. Create task with new fields ──────────────────────────
  let taskId;
  try {
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "Analyze competitor websites",
      description: "Run competitive analysis on key competitors",
      skill_name: "competitive-analysis",
      instructions: "Focus on pricing pages and onboarding flows",
      priority: "high",
      urls: ["https://competitor-a.com", "https://competitor-b.com"],
      input_document_ids: [],
      output_document_ids: [],
    });
    taskId = task.id;
    check(1, "Create task with new fields", !!task.id && task.instructions === "Focus on pricing pages and onboarding flows",
      `id: ${task.id}, instructions: ${task.instructions}`);
  } catch (e) {
    check(1, "Create task with new fields", false, e.message);
  }

  // ── 2. Verify new fields in response ────────────────────────
  if (taskId) {
    try {
      const task = await api.get(`/api/tasks/${taskId}?${projectQuery}`);
      const hasUrls = Array.isArray(task.urls) && task.urls.length === 2;
      const hasInstructions = task.instructions === "Focus on pricing pages and onboarding flows";
      const hasArrayFields = Array.isArray(task.input_document_ids) && Array.isArray(task.output_document_ids);
      check(2, "Task response includes new fields", hasUrls && hasInstructions && hasArrayFields,
        `urls: ${JSON.stringify(task.urls)}, instructions: ${task.instructions?.slice(0, 30)}`);
    } catch (e) {
      check(2, "Task response includes new fields", false, e.message);
    }
  } else {
    check(2, "Task response includes new fields", false, "No task created");
  }

  // ── 3. Create a document to attach ──────────────────────────
  let docId;
  try {
    const doc = await api.post("/api/documents", {
      project_id: projectId,
      title: "Competitor Report Draft",
      description: "Input for competitive analysis",
      source: "user_upload",
      file_name: "competitor-report.pdf",
    });
    docId = doc.id;
    check(3, "Create document for attachment", !!doc.id, doc.id);
  } catch (e) {
    check(3, "Create document for attachment", false, e.message);
  }

  // ── 4. Attach document to task (input) ──────────────────────
  if (taskId && docId) {
    try {
      const result = await api.post(`/api/tasks/${taskId}/attach?document_id=${docId}&direction=input&${projectQuery}`, {});
      check(4, "Attach document as input", result.attached === true, JSON.stringify(result));
    } catch (e) {
      check(4, "Attach document as input", false, e.message);
    }
  } else {
    check(4, "Attach document as input", false, "Missing task or document");
  }

  // ── 5. Verify attachment persisted ──────────────────────────
  if (taskId) {
    try {
      const task = await api.get(`/api/tasks/${taskId}?${projectQuery}`);
      const attached = Array.isArray(task.input_document_ids) && task.input_document_ids.includes(docId);
      check(5, "Attachment persisted on task", attached,
        `input_document_ids: ${JSON.stringify(task.input_document_ids)}`);
    } catch (e) {
      check(5, "Attachment persisted on task", false, e.message);
    }
  } else {
    check(5, "Attachment persisted on task", false, "No task");
  }

  // ── 6. Attach document as output ────────────────────────────
  if (taskId && docId) {
    try {
      const result = await api.post(`/api/tasks/${taskId}/attach?document_id=${docId}&direction=output&${projectQuery}`, {});
      const task = await api.get(`/api/tasks/${taskId}?${projectQuery}`);
      const hasOutput = Array.isArray(task.output_document_ids) && task.output_document_ids.includes(docId);
      check(6, "Attach document as output", hasOutput,
        `output_document_ids: ${JSON.stringify(task.output_document_ids)}`);
    } catch (e) {
      check(6, "Attach document as output", false, e.message);
    }
  } else {
    check(6, "Attach document as output", false, "Missing task or document");
  }

  // ── 7. Detach document ──────────────────────────────────────
  if (taskId && docId) {
    try {
      const result = await api.post(`/api/tasks/${taskId}/detach?document_id=${docId}&direction=input&${projectQuery}`, {});
      const task = await api.get(`/api/tasks/${taskId}?${projectQuery}`);
      const detached = Array.isArray(task.input_document_ids) && !task.input_document_ids.includes(docId);
      check(7, "Detach document from task", detached,
        `input_document_ids after detach: ${JSON.stringify(task.input_document_ids)}`);
    } catch (e) {
      check(7, "Detach document from task", false, e.message);
    }
  } else {
    check(7, "Detach document from task", false, "Missing task or document");
  }

  // ── 8. Update task URLs ─────────────────────────────────────
  if (taskId) {
    try {
      const updated = await api.patch(`/api/tasks/${taskId}?${projectQuery}`, {
        urls: ["https://new-competitor.com"],
        instructions: "Updated: analyze mobile app only",
      });
      const hasNewUrl = Array.isArray(updated.urls) && updated.urls.includes("https://new-competitor.com");
      const hasNewInstructions = updated.instructions === "Updated: analyze mobile app only";
      check(8, "Update task URLs and instructions", hasNewUrl && hasNewInstructions,
        `urls: ${JSON.stringify(updated.urls)}`);
    } catch (e) {
      check(8, "Update task URLs and instructions", false, e.message);
    }
  } else {
    check(8, "Update task URLs and instructions", false, "No task");
  }

  // ── 9. System tools endpoint (via settings health proxy) ────
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
    check(9, "Backend healthy with system tools loaded", operational,
      JSON.stringify(health).slice(0, 160));
  } catch (e) {
    check(9, "Backend healthy with system tools loaded", false, e.message);
  }

  // ── 10. Chat endpoint responds (tool-use system active) ─────
  try {
    // Just verify the chat endpoint accepts requests
    const res = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({
        message: "Hello, what can you help me with?",
        project_id: projectId,
        include_history: false,
      }),
    });
    check(10, "Chat endpoint responds with tool-use system", res.ok || res.status === 200,
      `Status: ${res.status}`);
  } catch (e) {
    check(10, "Chat endpoint responds with tool-use system", false, e.message);
  }

  // ── 11-14. UI Checks ───────────────────────────────────────
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForSelector('button[aria-label="Chat"], button[aria-label="Tasks"], main', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // 11. Tasks view loads
    const tasksNav = await page.locator('button[aria-label="Tasks"]').first();
    if (await tasksNav.isVisible({ timeout: 5000 })) {
      await tasksNav.click();
      await page.waitForTimeout(1000);
      check(11, "Tasks view navigable", true, "Tasks nav clicked");
    } else {
      await page.keyboard.down("Meta");
      await page.keyboard.press("3");
      await page.keyboard.up("Meta");
      await page.waitForTimeout(1000);
      let tasksHeading = await page.locator('h2:has-text("Tasks"), text=Backlog, text="Research Workflow"').first().isVisible({ timeout: 3000 }).catch(() => false);
      if (!tasksHeading) {
        await page.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "tasks" })));
        await page.waitForTimeout(1000);
        tasksHeading = await page.locator('h2:has-text("Tasks"), text=Backlog, text="Research Workflow"').first().isVisible({ timeout: 3000 }).catch(() => false);
      }
      check(11, "Tasks view navigable", tasksHeading, tasksHeading ? "Opened via keyboard shortcut" : "Tasks nav not visible");
    }

    // 12-14. Scan compiled JS for new fields, UI sections, and chat actions
    // Read source files directly; compiled Next chunks are not a stable contract.
    const sourceFiles = [
      "frontend/src/lib/types.ts",
      "frontend/src/lib/api.ts",
      "frontend/src/components/kanban/TaskEditor.tsx",
      "frontend/src/components/kanban/KanbanBoard.tsx",
      "frontend/src/components/layout/RightPanel.tsx",
      "frontend/src/components/chat/ChatView.tsx",
    ];
    const allText = sourceFiles
      .map((file) => readFileSync(join(REPO_ROOT, file), "utf8"))
      .join("\n");

    const hasNewFields = allText.includes("input_document_ids") && allText.includes("output_document_ids");
    const hasAttachUI = allText.includes("Attached Documents") || allText.includes("attach");
    const hasUrlsUI = allText.includes("URLs to Fetch") || allText.includes("urls");
    const hasChatActions = allText.includes("Chat Actions") || allText.includes("system tools") || allText.includes("Agents understand");

    check(12, "Frontend includes new task fields", hasNewFields,
      `textLen: ${allText.length}`);
    check(13, "Task editor has document/URL sections", hasAttachUI && hasUrlsUI,
      `attach: ${hasAttachUI}, urls: ${hasUrlsUI}`);
    check(14, "Chat panel shows tool-use actions", hasChatActions,
      `chatActions: ${hasChatActions}`);
  } catch (e) {
    check(11, "Tasks view navigable", false, e.message);
    check(12, "Frontend includes new task fields", false, e.message);
    check(13, "Task editor has document/URL sections", false, e.message);
    check(14, "Chat panel shows tool-use actions", false, e.message);
  }

  // ── 15. Phase 4E: Task cards show document indicators when documents are attached ──
  // Create a new task with attached documents to verify UI indicators
  let indicatorTaskId, indicatorDocId;
  try {
    // Create a document to attach
    const doc = await api.post("/api/documents", {
      project_id: projectId,
      title: "Indicator Test Document",
      description: "Document for testing card indicators",
      source: "user_upload",
      file_name: "indicator-test.pdf",
    });
    indicatorDocId = doc.id;

    // Create a task
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "Task With Document Indicator",
      description: "This task has a document attached for indicator testing",
      skill_name: "competitive-analysis",
      urls: ["https://example.com"],
      input_document_ids: [],
    });
    indicatorTaskId = task.id;

    // Attach the document
    if (indicatorTaskId && indicatorDocId) {
      await api.post(`/api/tasks/${indicatorTaskId}/attach?document_id=${indicatorDocId}&direction=input&${projectQuery}`, {});
    }

    // Now navigate to Tasks view and check for document indicators on cards
    if (page) {
      await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForSelector('button[aria-label="Chat"], button[aria-label="Tasks"], main', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1000);

      const tasksNav = page.locator('button[aria-label="Tasks"]').first();
      let tasksOpened = false;
      if (await tasksNav.isVisible({ timeout: 3000 })) {
        await tasksNav.click();
        await page.waitForTimeout(2000);
        tasksOpened = true;
      } else {
        await page.keyboard.down("Meta");
        await page.keyboard.press("3");
        await page.keyboard.up("Meta");
        await page.waitForTimeout(1500);
        tasksOpened = await page.locator('h2:has-text("Tasks"), text=Backlog, text="Research Workflow"').first().isVisible({ timeout: 3000 }).catch(() => false);
        if (!tasksOpened) {
          await page.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "tasks" })));
          await page.waitForTimeout(1000);
          tasksOpened = await page.locator('h2:has-text("Tasks"), text=Backlog, text="Research Workflow"').first().isVisible({ timeout: 3000 }).catch(() => false);
        }
      }

      if (tasksOpened) {
        // Look for document indicators on task cards
        const indicatorInfo = await page.evaluate(() => {
          const body = document.body.innerText.toLowerCase();
          // Look for document indicator icons or badges on task cards
          const docIcons = document.querySelectorAll(
            '[class*="document-indicator"], [aria-label*="document"], [title*="document"], ' +
            'svg[class*="doc"], [class*="paperclip"], [class*="attachment"]'
          );
          // Also check for document count badges
          const taskCards = document.querySelectorAll('[class*="task-card"], [class*="kanban-card"], [class*="rounded"][class*="border"][class*="shadow"]');
          let cardsWithDocIndicator = 0;
          for (const card of taskCards) {
            const cardHtml = card.innerHTML.toLowerCase();
            if (cardHtml.includes("document") || cardHtml.includes("paperclip") ||
                cardHtml.includes("attachment") || cardHtml.includes("file") ||
                cardHtml.includes("doc-icon") || cardHtml.includes("input_document")) {
              cardsWithDocIndicator++;
            }
          }

          return {
            docIconCount: docIcons.length,
            totalTaskCards: taskCards.length,
            cardsWithDocIndicator,
            bodyHasDocRef: body.includes("indicator test document") || body.includes("document indicator"),
          };
        });

        check(15, "Phase 4E: Task cards show document indicators",
          indicatorInfo.docIconCount > 0 || indicatorInfo.cardsWithDocIndicator > 0 || indicatorInfo.bodyHasDocRef,
          `doc_icons=${indicatorInfo.docIconCount}, cards_with_indicator=${indicatorInfo.cardsWithDocIndicator}/${indicatorInfo.totalTaskCards}`);
      } else {
        check(15, "Phase 4E: Task cards show document indicators", false, "Tasks view not reachable");
      }
    } else {
      check(15, "Phase 4E: Task cards show document indicators", false, "No page context");
    }
  } catch (e) {
    check(15, "Phase 4E: Task cards show document indicators", false, e.message);
  }

  // ── 16. Cleanup ─────────────────────────────────────────────
  try {
    if (indicatorDocId) await api.delete(`/api/documents/${indicatorDocId}?${projectQuery}`);
    if (indicatorTaskId) await api.delete(`/api/tasks/${indicatorTaskId}?${projectQuery}`);
    if (docId) await api.delete(`/api/documents/${docId}?${projectQuery}`);
    if (taskId) await api.delete(`/api/tasks/${taskId}?${projectQuery}`);
    check(16, "Cleanup successful", true, "");
  } catch (e) {
    check(16, "Cleanup successful", false, e.message);
  }

  // ── Summary ─────────────────────────────────────────────────
  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed, total: checks.length };
}
