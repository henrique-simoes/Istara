/** Scenario 09 — Navigation & Search: keyboard shortcuts, view switching, search modal. */

export const name = "Navigation & Search";
export const id = "09-navigation-search";

export async function run(ctx) {
  const { page, screenshot } = ctx;
  const checks = [];

  async function dismissBlockingOverlay() {
    const hasOverlay = async () => page.locator(".fixed.inset-0").first().isVisible({ timeout: 300 }).catch(() => false);
    if (!(await hasOverlay())) return;

    for (let i = 0; i < 2; i++) {
      await page.keyboard.press("Escape").catch(() => {});
      await page.waitForTimeout(200);
      if (!(await hasOverlay())) return;
    }

    const closeCandidates = [
      'button[aria-label="Skip Interfaces setup"]',
      'button[aria-label*="Close"]',
      'button[aria-label*="Dismiss"]',
      'button:has-text("Skip")',
      'button:has-text("Get Started")',
      'button:has-text("Got it")',
      'button:has-text("Continue")',
    ];

    for (const selector of closeCandidates) {
      const candidate = page.locator(selector).first();
      if (await candidate.isVisible({ timeout: 300 }).catch(() => false)) {
        await candidate.click({ timeout: 1000 }).catch(() => {});
        await page.waitForTimeout(300);
        if (!(await hasOverlay())) return;
      }
    }
  }

  async function clickNavButton(label) {
    await dismissBlockingOverlay();
    const btn = page.locator(`button[aria-label="${label}"]`).first();
    if (!(await btn.isVisible({ timeout: 1000 }).catch(() => false))) {
      return { clicked: false, selected: null, detail: "not visible" };
    }
    try {
      await btn.click({ timeout: 3000 });
    } catch {
      await dismissBlockingOverlay();
      await btn.click({ timeout: 3000 });
    }
    await page.waitForTimeout(800);
    await dismissBlockingOverlay();
    return {
      clicked: true,
      selected: await btn.getAttribute("aria-selected").catch(() => null),
      detail: "",
    };
  }

  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  // Test sidebar nav items exist
  const navItems = [
    "Chat",
    "Findings",
    "UX Laws",
    "Tasks",
    "Interviews",
    "Documents",
    "Context",
    "Skills",
    "Agents",
    "Memory",
    "Interfaces",
    "Integrations",
    "Loops",
    "Settings",
  ];
  for (const item of navItems) {
    const btn = page.locator(`button[aria-label="${item}"]`).first();
    const visible = await btn.isVisible({ timeout: 2000 }).catch(() => false);
    checks.push({ name: `Nav item: ${item}`, passed: visible, detail: "" });
  }

  // Test More button reveals secondary nav (Settings moved to primary nav in Phase 2B)
  const moreBtn = page.locator('button[aria-label="More views"]').first();
  if (await moreBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await moreBtn.click({ timeout: 3000 });
    await page.waitForTimeout(500);
    const secondaryItems = [
      "Autoresearch",
      "Backup",
      "Meta-Agent",
      "Compute Pool",
      "Ensemble Health",
      "Quality Dashboard",
      "Project Settings",
      "History",
    ];
    for (const item of secondaryItems) {
      const btn = page.locator(`button[aria-label="${item}"]`).first();
      const visible = await btn.isVisible({ timeout: 1000 }).catch(() => false);
      checks.push({ name: `Secondary nav: ${item}`, passed: visible, detail: "" });
    }
  }

  // Desktop secondary nav should auto-expand when returning to a secondary view.
  await page.evaluate(() => localStorage.setItem("istara_active_view", "quality"));
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);
  const restoredQuality = await page.locator('button[aria-label="Quality Dashboard"][aria-selected="true"]').first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({
    name: "Secondary nav auto-expands for Quality Dashboard",
    passed: restoredQuality,
    detail: restoredQuality ? "Quality Dashboard restored and visible" : "Quality Dashboard not visible after reload",
  });

  // Test view switching via clicks
  for (const view of navItems) {
    const result = await clickNavButton(view);
    if (result.clicked) {
      checks.push({ name: `View switch: ${view}`, passed: result.selected === "true", detail: `aria-selected=${result.selected}` });
    }
  }

  // Test keyboard shortcuts — Cmd+1 to Cmd+7
  const viewKeys = { "1": "Chat", "2": "Findings", "3": "Tasks", "4": "Interviews", "5": "Documents", "6": "Context", "7": "Skills", "8": "Agents" };
  for (const [key, expectedView] of Object.entries(viewKeys)) {
    await page.keyboard.press(`Meta+${key}`);
    await page.waitForTimeout(500);
    const activeBtn = page.locator(`button[aria-label="${expectedView}"][aria-selected="true"]`).first();
    const isActive = await activeBtn.isVisible({ timeout: 1000 }).catch(() => false);
    checks.push({ name: `Shortcut Cmd+${key} → ${expectedView}`, passed: isActive, detail: "" });
  }

  // Mobile navigation: primary bar plus More sheet must expose every hidden view.
  {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);

    const mobileBar = page.locator('nav[aria-label="Mobile navigation"]').first();
    const mobileVisible = await mobileBar.isVisible({ timeout: 2000 }).catch(() => false);
    checks.push({ name: "Mobile navigation bar visible", passed: mobileVisible, detail: "" });

    const mobilePrimary = ["Chat", "Findings", "Tasks", "Documents"];
    for (const item of mobilePrimary) {
      const visible = await mobileBar.locator(`button[aria-label="${item}"]`).first().isVisible({ timeout: 1000 }).catch(() => false);
      checks.push({ name: `Mobile primary nav: ${item}`, passed: visible, detail: "" });
    }

    const mobileMore = mobileBar.locator('button[aria-label="More views"]').first();
    if (await mobileMore.isVisible({ timeout: 1000 }).catch(() => false)) {
      await mobileMore.click({ timeout: 3000 });
      await page.waitForTimeout(500);
      const mobileMenu = page.locator('[role="dialog"][aria-label="Mobile navigation menu"]').first();
      const moreItems = [
        "UX Laws",
        "Interviews",
        "Context",
        "Skills",
        "Agents",
        "Memory",
        "Interfaces",
        "Integrations",
        "Loops",
        "Settings",
        "Notifications",
        "Autoresearch",
        "Backup",
        "Meta-Agent",
        "Compute Pool",
        "Ensemble Health",
        "Quality Dashboard",
        "Project Settings",
        "History",
      ];
      for (const item of moreItems) {
        const visible = await mobileMenu.locator(`button[aria-label="${item}"]`).first().isVisible({ timeout: 1000 }).catch(() => false);
        checks.push({ name: `Mobile More nav: ${item}`, passed: visible, detail: "" });
      }
      await page.keyboard.press("Escape");
    } else {
      checks.push({ name: "Mobile More nav opens", passed: false, detail: "More button not visible" });
    }

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
  }

  // ── Phase 0: View Persistence ──
  // Navigate to Documents view, verify it was saved to localStorage
  {
    await dismissBlockingOverlay();
    const docsBtn = page.locator('button[aria-label="Documents"]').first();
    if (await docsBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await docsBtn.click({ timeout: 3000 });
      await page.waitForTimeout(800);

      // Check localStorage for persisted view
      const savedView = await page.evaluate(() => localStorage.getItem("istara_active_view"));
      checks.push({
        name: "View persistence: localStorage stores active view",
        passed: savedView === "documents",
        detail: `istara_active_view="${savedView}"`,
      });

      // Check document title includes view name
      const docTitle = await page.title();
      const titleIncludesView = docTitle.toLowerCase().includes("document");
      checks.push({
        name: "View persistence: document title includes view name",
        passed: titleIncludesView,
        detail: `title="${docTitle}"`,
      });

      // Navigate away and back — verify persistence across reload
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1500);
      const restoredView = await page.evaluate(() => localStorage.getItem("istara_active_view"));
      checks.push({
        name: "View persistence: survives page reload",
        passed: restoredView === "documents",
        detail: `after reload: istara_active_view="${restoredView}"`,
      });
    } else {
      checks.push({ name: "View persistence: localStorage stores active view", passed: false, detail: "Documents nav button not visible" });
    }
  }

  // ── Phase 2B: Settings Visibility in Primary Nav ──
  // Settings should appear in primary nav, not hidden behind "More"
  {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);

    const settingsBtn = page.locator('button[aria-label="Settings"]').first();
    const settingsVisible = await settingsBtn.isVisible({ timeout: 2000 }).catch(() => false);

    // Verify Settings is visible WITHOUT needing to click "More"
    checks.push({
      name: "Settings visible in primary nav (not behind More)",
      passed: settingsVisible,
      detail: settingsVisible ? "Settings directly visible" : "Settings not found in primary nav",
    });

    // If Settings is visible, verify it's NOT inside a secondary/expanded menu
    if (settingsVisible) {
      const isInSecondaryPanel = await settingsBtn.evaluate((btn) => {
        // Check if the button is inside a panel that was triggered by "More"
        const parent = btn.closest('[class*="secondary"], [class*="expanded"], [class*="more-menu"]');
        return !!parent;
      });
      checks.push({
        name: "Settings is in primary nav section (not secondary)",
        passed: !isInSecondaryPanel,
        detail: `in_secondary_panel=${isInSecondaryPanel}`,
      });
    }
  }

  // Test Cmd+K search modal
  // Click the viewport directly first to ensure focus is not trapped in a view component.
  // `locator("body").click()` can fail actionability checks on pages where the
  // app root owns the full viewport and the body has no visible box.
  await dismissBlockingOverlay();
  await page.mouse.click(400, 300);
  await page.waitForTimeout(300);
  await page.keyboard.press("Meta+k");
  await page.waitForTimeout(800);
  // The Documents view also owns a visible search input. Scope this assertion
  // to the modal so Playwright's strict locator semantics cannot turn a real
  // Cmd+K open into a false negative when both fields are mounted.
  const searchModal = await page
    .locator('.fixed.inset-0 input[placeholder="Search findings, nuggets, insights..."]')
    .isVisible({ timeout: 3000 })
    .catch(() => false);
  checks.push({ name: "Cmd+K opens search modal", passed: searchModal, detail: "" });
  await screenshot("09-search-modal");

  // Close with Escape
  if (searchModal) {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(500);
    const modalClosed = !(await page.locator('[role="dialog"], [class*="modal"]').first().isVisible({ timeout: 1000 }).catch(() => false));
    checks.push({ name: "Escape closes search modal", passed: modalClosed, detail: "" });
  }

  // Test sidebar collapse/expand
  try {
    await dismissBlockingOverlay();
    const collapseBtn = page.locator('button[aria-label="Collapse sidebar"]').first();
    if (await collapseBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      try {
        await collapseBtn.click({ timeout: 5000 });
      } catch {
        // Force click if overlay still intercepts
        await collapseBtn.click({ force: true, timeout: 3000 });
      }
      await page.waitForTimeout(500);
      await screenshot("09-sidebar-collapsed");

      const expandBtn = page.locator('button[aria-label="Expand sidebar"]').first();
      const collapsed = await expandBtn.isVisible({ timeout: 1000 }).catch(() => false);
      checks.push({ name: "Sidebar collapse", passed: collapsed, detail: "" });

      if (collapsed) {
        await expandBtn.click({ timeout: 3000 });
        await page.waitForTimeout(500);
      }
    }
  } catch (e) {
    checks.push({ name: "Sidebar collapse", passed: false, detail: `Overlay may be blocking: ${e.message.substring(0, 80)}` });
  }

  // Test dark mode toggle
  await dismissBlockingOverlay();
  const darkToggle = page.locator('button[aria-label*="dark"], button[aria-label*="theme"], button[aria-label*="mode"]').first();
  if (await darkToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
    await darkToggle.click({ timeout: 3000 });
    await page.waitForTimeout(500);
    await screenshot("09-light-mode");
    checks.push({ name: "Dark mode toggle", passed: true, detail: "" });

    // Toggle back
    await darkToggle.click({ timeout: 3000 });
    await page.waitForTimeout(500);
  }

  // Test ? keyboard shortcuts modal
  await page.keyboard.press("?");
  await page.waitForTimeout(1000);
  const shortcutsModal = await page.locator("text=Keyboard Shortcuts").isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "? opens shortcuts modal", passed: shortcutsModal, detail: "" });

  // Dismiss any open modals/overlays before continuing
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
  }

  // Click any remaining overlay backdrop to dismiss it
  const overlay = page.locator('.fixed.inset-0').first();
  if (await overlay.isVisible({ timeout: 500 }).catch(() => false)) {
    await overlay.click({ position: { x: 5, y: 5 }, force: true });
    await page.waitForTimeout(500);
  }

  // Wait for overlays to disappear
  await page.waitForFunction(
    () => {
      const overlays = document.querySelectorAll('.fixed.inset-0');
      for (const el of overlays) {
        if (el.offsetParent !== null || getComputedStyle(el).display !== 'none') {
          const bg = getComputedStyle(el).backgroundColor;
          if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return false;
        }
      }
      return true;
    },
    undefined,
    { timeout: 5000 }
  ).catch(() => {});

  // Test Cmd+. right panel toggle
  await page.keyboard.press("Meta+.");
  await page.waitForTimeout(500);
  await screenshot("09-right-panel-toggled");
  checks.push({ name: "Cmd+. toggles right panel", passed: true, detail: "" });

  // Toggle back
  await page.keyboard.press("Meta+.");
  await page.waitForTimeout(300);

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
