/**
 * Scenario 29 — Documents System
 *
 * Verifies the Documents menu, API, search, filtering, file-to-document
 * registration, backup integration, and UI navigation.
 */

export const name = "Documents System";
export const id = "29-documents-system";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];
  let projectId;

  // ── Helper ─────────────────────────────────────────────────────────
  function check(id, label, passed, detail = "") {
    checks.push({ id, label, passed, detail });
  }

  // ── Setup: use persistent simulation project ─────────────────────────────────
  projectId = ctx.projectId;
  if (!projectId) {
    check(1, "Project setup", false, "No persistent project available from runner");
    return { checks, passed: 0, failed: checks.length };
  }
  check(1, "Project setup", true, `Using persistent project: ${projectId}`);

  // ──────────────────────────────────────────────────────────────────
  // 1. Documents API endpoint exists
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents?project_id=${projectId}`);
    check(1, "GET /api/documents returns valid response", !!res && "documents" in res && "total" in res, `keys: ${Object.keys(res)}`);
  } catch (e) {
    check(1, "GET /api/documents returns valid response", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 2. Create a document via API
  // ──────────────────────────────────────────────────────────────────
  let docId;
  try {
    const doc = await api.post("/api/documents", {
      project_id: projectId,
      title: "User Interview Analysis Report",
      description: "You asked to analyze 5 user interviews about onboarding friction.",
      file_name: "interview-analysis.md",
      file_type: ".md",
      file_size: 2048,
      source: "task_output",
      task_id: null,
      agent_ids: ["istara-main"],
      skill_names: ["user-interviews", "thematic-analysis"],
      tags: ["interviews", "onboarding", "friction"],
      phase: "discover",
      atomic_path: {
        step_1: "User uploaded 5 interview transcripts",
        step_2: "Agent selected user-interviews skill",
        step_3: "Thematic analysis performed",
        step_4: "Report generated with findings",
      },
      content_preview: "This report analyzes 5 user interviews about onboarding friction...",
      content_text: "# Interview Analysis Report\n\n## Summary\nAcross 5 interviews, users consistently reported friction in the onboarding flow...",
    });
    docId = doc.id;
    check(2, "POST /api/documents creates document", !!doc.id && doc.title === "User Interview Analysis Report",
      `id=${doc.id}, title=${doc.title}`);
  } catch (e) {
    check(2, "POST /api/documents creates document", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 3. Get document by ID
  // ──────────────────────────────────────────────────────────────────
  try {
    const doc = await api.get(`/api/documents/${docId}`);
    const hasContent = doc.content_text && doc.content_text.includes("Interview Analysis");
    const hasAtomicPath = doc.atomic_path && Object.keys(doc.atomic_path).length >= 4;
    const hasTags = Array.isArray(doc.tags) && doc.tags.length === 3;
    check(3, "GET /api/documents/:id returns full document",
      hasContent && hasAtomicPath && hasTags,
      `content=${!!hasContent}, atomic_keys=${Object.keys(doc.atomic_path || {}).length}, tags=${doc.tags?.length}`);
  } catch (e) {
    check(3, "GET /api/documents/:id returns full document", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 4. Create additional documents for search/filter testing
  // ──────────────────────────────────────────────────────────────────
  try {
    await api.post("/api/documents", {
      project_id: projectId,
      title: "Survey Design Questionnaire",
      description: "Agent created a survey based on research findings.",
      source: "agent_output",
      tags: ["survey", "questionnaire"],
      phase: "define",
      content_text: "# Survey Questionnaire\n\n1. How often do you use the product?",
    });
    await api.post("/api/documents", {
      project_id: projectId,
      title: "Usability Test Report",
      description: "You asked to evaluate the checkout flow usability.",
      source: "task_output",
      agent_ids: ["istara-main"],
      skill_names: ["usability-testing"],
      tags: ["usability", "checkout"],
      phase: "develop",
      content_text: "# Usability Report\n\nCompletion rate: 78%. SUS Score: 72.",
    });
    const listRes = await api.get(`/api/documents?project_id=${projectId}`);
    check(4, "Multiple documents created for test suite",
      listRes.total >= 3,
      `total=${listRes.total}`);
  } catch (e) {
    check(4, "Multiple documents created for test suite", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 5. Search documents by title content
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents?project_id=${projectId}&search=Survey`);
    const found = res.documents.some(d => d.title.toLowerCase().includes("survey"));
    check(5, "Search by title finds matching documents",
      found && res.documents.length >= 1,
      `results=${res.documents.length}`);
  } catch (e) {
    check(5, "Search by title finds matching documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 6. Search documents by content
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents?project_id=${projectId}&search=SUS+Score`);
    const found = res.documents.some(d => d.title === "Usability Test Report");
    check(6, "Search by content finds matching documents",
      found,
      `results=${res.documents.length}`);
  } catch (e) {
    check(6, "Search by content finds matching documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 7. Filter by Double Diamond phase
  // ──────────────────────────────────────────────────────────────────
  try {
    const discover = await api.get(`/api/documents?project_id=${projectId}&phase=discover`);
    const define = await api.get(`/api/documents?project_id=${projectId}&phase=define`);
    const develop = await api.get(`/api/documents?project_id=${projectId}&phase=develop`);
    check(7, "Phase filter returns correct documents",
      discover.documents.length >= 1 && define.documents.length >= 1 && develop.documents.length >= 1,
      `discover=${discover.documents.length}, define=${define.documents.length}, develop=${develop.documents.length}`);
  } catch (e) {
    check(7, "Phase filter returns correct documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 8. Filter by tag
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents?project_id=${projectId}&tag=interviews`);
    check(8, "Tag filter returns tagged documents",
      res.documents.length >= 1 && res.documents[0].tags.includes("interviews"),
      `results=${res.documents.length}`);
  } catch (e) {
    check(8, "Tag filter returns tagged documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 9. Get all tags for a project
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents/tags/${projectId}`);
    const tagNames = res.tags.map(t => t.name);
    check(9, "Tags endpoint returns all unique tags",
      tagNames.includes("interviews") && tagNames.includes("survey") && tagNames.includes("usability"),
      `tags: ${tagNames.join(", ")}`);
  } catch (e) {
    check(9, "Tags endpoint returns all unique tags", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 10. Document stats endpoint
  // ──────────────────────────────────────────────────────────────────
  try {
    const stats = await api.get(`/api/documents/stats/${projectId}`);
    check(10, "Document stats returns correct structure",
      stats.total >= 3 && !!stats.by_source && !!stats.by_phase && !!stats.by_status,
      `total=${stats.total}, sources=${Object.keys(stats.by_source).length}`);
  } catch (e) {
    check(10, "Document stats returns correct structure", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 11. Update document (add tags, change phase)
  // ──────────────────────────────────────────────────────────────────
  try {
    const updated = await api.patch(`/api/documents/${docId}`, {
      tags: ["interviews", "onboarding", "friction", "priority-high"],
      phase: "define",
    });
    check(11, "PATCH /api/documents/:id updates document",
      updated.tags.includes("priority-high") && updated.phase === "define",
      `tags=${updated.tags.length}, phase=${updated.phase}`);
  } catch (e) {
    check(11, "PATCH /api/documents/:id updates document", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 12. Document content endpoint
  // ──────────────────────────────────────────────────────────────────
  try {
    const content = await api.get(`/api/documents/${docId}/content`);
    check(12, "Document content endpoint returns content",
      content.content && content.content.includes("Interview Analysis"),
      `content_length=${content.content?.length || 0}`);
  } catch (e) {
    check(12, "Document content endpoint returns content", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 13. Full-text search API endpoint
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.get(`/api/documents/search/full?project_id=${projectId}&q=onboarding`);
    check(13, "Full-text search endpoint works",
      res.results.length >= 1 && res.query === "onboarding",
      `results=${res.results.length}`);
  } catch (e) {
    check(13, "Full-text search endpoint works", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 14. Sync documents from project folder
  // ──────────────────────────────────────────────────────────────────
  try {
    const res = await api.post(`/api/documents/sync/${projectId}`, {});
    check(14, "Document sync endpoint returns valid response",
      "synced" in res && "total" in res,
      `synced=${res.synced}, total=${res.total}`);
  } catch (e) {
    check(14, "Document sync endpoint returns valid response", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 15. Filter by source type
  // ──────────────────────────────────────────────────────────────────
  try {
    const agent = await api.get(`/api/documents?project_id=${projectId}&source=agent_output`);
    const task = await api.get(`/api/documents?project_id=${projectId}&source=task_output`);
    check(15, "Source filter returns correct documents",
      agent.documents.length >= 1 && task.documents.length >= 1,
      `agent_output=${agent.documents.length}, task_output=${task.documents.length}`);
  } catch (e) {
    check(15, "Source filter returns correct documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 16. Document atomic path is preserved and accessible
  // ──────────────────────────────────────────────────────────────────
  try {
    const doc = await api.get(`/api/documents/${docId}`);
    const ap = doc.atomic_path || {};
    check(16, "Atomic path preserved with step details",
      ap.step_1 && ap.step_2 && ap.step_3 && ap.step_4,
      `steps=${Object.keys(ap).length}`);
  } catch (e) {
    check(16, "Atomic path preserved with step details", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 17. Pagination works
  // ──────────────────────────────────────────────────────────────────
  try {
    const page1 = await api.get(`/api/documents?project_id=${projectId}&page=1&page_size=2`);
    check(17, "Pagination returns correct page structure",
      page1.page === 1 && page1.page_size === 2 && page1.total >= 3 && page1.total_pages >= 2,
      `page=${page1.page}, page_size=${page1.page_size}, total=${page1.total}, total_pages=${page1.total_pages}`);
  } catch (e) {
    check(17, "Pagination returns correct page structure", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 18. Documents included in project export/backup
  // ──────────────────────────────────────────────────────────────────
  try {
    const exported = await api.post(`/api/projects/${projectId}/export`, {});
    check(18, "Project export includes documents",
      exported.exported === true && exported.files_count > 0,
      `exported=${exported.exported}, files=${exported.files_count}, path=${exported.path}`);
  } catch (e) {
    check(18, "Project export includes documents", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 19. UI — Navigate to app and verify Documents menu
  // ──────────────────────────────────────────────────────────────────
  try {
    // Navigate fresh to the app
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 10000 });
    await page.waitForTimeout(2000);
    // The sidebar is only visible on lg+ (1280px viewport in test runner)
    const docsBtn = await page.$('button[aria-label="Documents"]');
    check(19, "Documents menu appears in sidebar",
      !!docsBtn,
      docsBtn ? "Found" : "Not found in sidebar (may be below viewport threshold)");
  } catch (e) {
    check(19, "Documents menu appears in sidebar", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 20. UI — Navigate to Documents view
  // ──────────────────────────────────────────────────────────────────
  try {
    const docsBtn = await page.$('button[aria-label="Documents"]');
    if (docsBtn) {
      await docsBtn.click();
      await page.waitForTimeout(2000);
      const heading = await page.$eval("h2", el => el.textContent).catch(() => "");
      check(20, "Documents view loads on navigation",
        heading.includes("Documents"),
        `heading="${heading}"`);
    } else {
      // Fallback: use keyboard shortcut
      await page.keyboard.down("Meta");
      await page.keyboard.press("5");
      await page.keyboard.up("Meta");
      await page.waitForTimeout(2000);
      const heading = await page.$eval("h2", el => el.textContent).catch(() => "");
      check(20, "Documents view loads on navigation",
        heading.includes("Documents"),
        `heading="${heading}" (via shortcut fallback)`);
    }
  } catch (e) {
    check(20, "Documents view loads on navigation", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 21. UI — Search input exists in documents view
  // ──────────────────────────────────────────────────────────────────
  try {
    const searchInput = await page.$('input[aria-label="Search documents"]');
    check(21, "Search input present in Documents view",
      !!searchInput,
      searchInput ? "Found" : "Not found");
  } catch (e) {
    check(21, "Search input present in Documents view", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 22. UI — Filter button exists
  // ──────────────────────────────────────────────────────────────────
  try {
    const filterBtn = await page.$('button[aria-label="Toggle filters"]');
    check(22, "Filter toggle button present",
      !!filterBtn,
      filterBtn ? "Found" : "Not found");
  } catch (e) {
    check(22, "Filter toggle button present", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 23. UI — Sync button exists
  // ──────────────────────────────────────────────────────────────────
  try {
    const syncBtn = await page.$('button[aria-label="Sync project files"]');
    check(23, "Sync button present",
      !!syncBtn,
      syncBtn ? "Found" : "Not found");
  } catch (e) {
    check(23, "Sync button present", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 23b. Phase 3: Documents View Modes — compact (default), grid, list
  // ──────────────────────────────────────────────────────────────────
  try {
    // Verify compact view renders by default
    const compactElements = await page.evaluate(() => {
      // Compact rows are typically table-like or narrow row elements
      const rows = document.querySelectorAll('[class*="compact"], [class*="table-row"], tr[class*="document"], [class*="doc-row"]');
      const anyRowLayout = document.querySelectorAll('[class*="flex"][class*="items-center"][class*="py-"]');
      return { compactCount: rows.length, rowLayoutCount: anyRowLayout.length };
    });
    check("23b-1", "Phase 3: Compact view renders by default",
      compactElements.compactCount > 0 || compactElements.rowLayoutCount > 0,
      `compact=${compactElements.compactCount}, rowLayout=${compactElements.rowLayoutCount}`);

    // Look for view mode toggle buttons (grid/list/compact)
    const viewModeToggles = await page.evaluate(() => {
      const btns = document.querySelectorAll('button[aria-label*="view"], button[aria-label*="View"], button[title*="view"], button[title*="View"]');
      const gridBtn = document.querySelector('button[aria-label*="Grid"], button[aria-label*="grid"], button[title*="Grid"]');
      const listBtn = document.querySelector('button[aria-label*="List"], button[aria-label*="list"], button[title*="List"]');
      const compactBtn = document.querySelector('button[aria-label*="Compact"], button[aria-label*="compact"], button[title*="Compact"]');
      return {
        totalToggleBtns: btns.length,
        hasGrid: !!gridBtn,
        hasList: !!listBtn,
        hasCompact: !!compactBtn,
        gridLabel: gridBtn?.getAttribute("aria-label") || gridBtn?.getAttribute("title") || "",
        listLabel: listBtn?.getAttribute("aria-label") || listBtn?.getAttribute("title") || "",
      };
    });
    check("23b-2", "Phase 3: View mode toggle buttons exist",
      viewModeToggles.hasGrid || viewModeToggles.hasList || viewModeToggles.totalToggleBtns >= 2,
      `grid=${viewModeToggles.hasGrid}, list=${viewModeToggles.hasList}, total=${viewModeToggles.totalToggleBtns}`);

    // Toggle to grid view if button exists
    if (viewModeToggles.hasGrid) {
      const gridBtn = await page.$('button[aria-label*="Grid"], button[aria-label*="grid"], button[title*="Grid"]');
      if (gridBtn) {
        await gridBtn.click();
        await page.waitForTimeout(800);
        const hasGrid = await page.evaluate(() => {
          const gridEl = document.querySelector('[class*="grid-cols"], [class*="grid "]');
          return !!gridEl;
        });
        check("23b-3", "Phase 3: Grid view renders grid layout CSS",
          hasGrid,
          `grid_layout_found=${hasGrid}`);
      }
    } else {
      check("23b-3", "Phase 3: Grid view renders grid layout CSS", false, "Grid button not found");
    }

    // Toggle to list view if button exists
    if (viewModeToggles.hasList) {
      const listBtn = await page.$('button[aria-label*="List"], button[aria-label*="list"], button[title*="List"]');
      if (listBtn) {
        await listBtn.click();
        await page.waitForTimeout(800);
        const hasList = await page.evaluate(() => {
          const listEl = document.querySelector('[class*="space-y"], [class*="divide-y"], [class*="flex-col"][class*="gap"]');
          return !!listEl;
        });
        check("23b-4", "Phase 3: List view renders list layout",
          hasList,
          `list_layout_found=${hasList}`);
      }
    } else {
      check("23b-4", "Phase 3: List view renders list layout", false, "List button not found");
    }

    // Verify view mode persists to localStorage
    const viewModePersisted = await page.evaluate(() => {
      const stored = localStorage.getItem("istara_documents_view_mode") || localStorage.getItem("documents_view_mode");
      return stored;
    });
    check("23b-5", "Phase 3: View mode persists to localStorage",
      !!viewModePersisted,
      `stored_mode="${viewModePersisted}"`);

    // Switch back to compact if possible
    if (viewModeToggles.hasCompact) {
      const compactBtn = await page.$('button[aria-label*="Compact"], button[aria-label*="compact"], button[title*="Compact"]');
      if (compactBtn) await compactBtn.click();
      await page.waitForTimeout(500);
    }
  } catch (e) {
    check("23b", "Phase 3: Documents view modes", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 24. Delete a document
  // ──────────────────────────────────────────────────────────────────
  try {
    // Create a temp document to delete
    const tempDoc = await api.post("/api/documents", {
      project_id: projectId,
      title: "Temporary Delete Test",
      source: "external",
    });
    // Delete it
    const delRes = await fetch(`http://localhost:8000/api/documents/${tempDoc.id}`, { method: "DELETE", headers: api._headers() });
    // Verify it's gone
    let gone = false;
    try {
      await api.get(`/api/documents/${tempDoc.id}`);
    } catch {
      gone = true;
    }
    check(24, "DELETE /api/documents/:id removes document",
      delRes.status === 204 && gone,
      `status=${delRes.status}, gone=${gone}`);
  } catch (e) {
    check(24, "DELETE /api/documents/:id removes document", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // 25. Keyboard shortcut — Cmd+5 navigates to Documents
  // ──────────────────────────────────────────────────────────────────
  try {
    // First navigate away to Chat
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 10000 });
    await page.waitForTimeout(1500);
    const chatBtn = await page.$('button[aria-label="Chat"]');
    if (chatBtn) {
      await chatBtn.click();
      await page.waitForTimeout(500);
    }
    // Press Cmd+5 to go to Documents
    await page.keyboard.down("Meta");
    await page.keyboard.press("5");
    await page.keyboard.up("Meta");
    await page.waitForTimeout(1500);
    const heading = await page.$eval("h2", el => el.textContent).catch(() => "");
    check(25, "Cmd+5 keyboard shortcut opens Documents view",
      heading.includes("Documents"),
      `heading="${heading}"`);
  } catch (e) {
    check(25, "Cmd+5 keyboard shortcut opens Documents view", false, e.message);
  }

  // ──────────────────────────────────────────────────────────────────
  // Summary
  // ──────────────────────────────────────────────────────────────────
  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;

  await screenshot("29-documents-system");

  return { checks, passed, failed };
}
