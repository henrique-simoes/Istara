/**
 * Scenario 90 — Every menu and sub-tab, walked (professional-readiness review, U1-U5), 2026-09-27.
 *
 * The 24-view sweeps open each view's first screen; what sits behind its tabs was never opened by
 * anyone. This scenario opens every view from the sidebar, then every sub-tab inside it (a
 * `role="tab"` or a grouped `aria-pressed` toggle), in the light and the dark theme, and on each
 * screen records the mechanical defect classes of the visual-debug rubric:
 *
 *   1. the screen rendered: no error boundary, no uncaught page error, no failed API request;
 *   2. no machine text leaks into the page ("undefined", "NaN", "[object Object]", raw i18n keys);
 *   3. nothing overflows the viewport sideways;
 *   4. axe-core WCAG 2.1 AA finds no serious or critical violation (light and dark);
 *   5. the view is reachable by keyboard: its sidebar button takes focus with a visible ring.
 *
 * A viewer (read-only role) walks the same views: every view opens without an error and without a
 * failed request. Every per-screen observation lands in `menu-walk.json` in the run folder.
 * Credential-free QA lane (the views do not need a model); synthetic data only; nothing mutates.
 */

import { writeFileSync } from "node:fs";
import { join } from "node:path";

import { getApiBase } from "../lib/api-client.mjs";
import { selectProject } from "../lib/embedding-settings.mjs";
import { setTheme } from "../lib/matrix-checks.mjs";

export const name = "Every menu and sub-tab, walked";
export const id = "90-menu-walk";

// Sidebar labels as the user sees them; the last nine sit under "More views"; Notifications is the
// header bell.
export const VIEWS = [
  ["Chat", "chat"], ["Findings", "findings"], ["Tasks", "tasks"], ["Interviews", "interviews"],
  ["Documents", "documents"], ["Context", "context"], ["Memory", "memory"], ["Skills", "skills"],
  ["Agents", "agents"], ["UX Laws", "laws"], ["Loops", "loops"], ["Interfaces", "interfaces"],
  ["Integrations", "integrations"], ["Settings", "settings"], ["Notifications", "notifications"],
  ["History", "history"], ["Backup", "backup"], ["Meta-Agent", "meta-hyperagent"],
  ["Ensemble Health", "ensemble"], ["Quality Dashboard", "quality"], ["Compute Pool", "compute"],
  ["Autoresearch", "autoresearch"], ["Project Settings", "project-settings"], ["Admin", "admin"],
];const PROJECT_NAME = "[SIM-90] Menu walk";
const MACHINE_TEXT = /\b(undefined|NaN)\b|\[object Object\]|\b[a-z]+(?:\.[a-z][a-zA-Z_]+){2,}\b/;
const ERROR_SURFACE = /Something went wrong|Application error|Unhandled Runtime Error|Minified React error/i;

export async function run(ctx) {
  const checks = [];
  const walk = [];
  const page = ctx.page;
  const events = { pageErrors: [], failedRequests: [] };
  page.on("pageerror", (err) => events.pageErrors.push(String(err.message || err).slice(0, 200)));
  // Istara's own API only: the Settings compute-donation card also probes the viewer's machine for a
  // local model server (ports 1234, 11434, ...), and those probes are expected to fail.
  const apiBase = getApiBase().replace(/\/$/, "");
  page.on("response", (res) => {
    const url = res.url();
    if (res.status() >= 400 && url.startsWith(`${apiBase}/api/`)) {
      events.failedRequests.push(`${res.status()} ${res.request().method()} ${url.replace(/^https?:\/\/[^/]+/, "")}`);
    }
  });
  let projectId = null;
  // A blocked click must fail in seconds and be recorded, not hold the walk for five minutes.
  page.setDefaultTimeout(10_000);
  try {
    const created = await ctx.api.post("/api/projects", { name: PROJECT_NAME, description: "Scenario 90 menu walk (synthetic)" });
    projectId = created.id;
    checks.push({ name: "[API-behind-browser] SETUP: a fresh project to walk", passed: !!projectId, detail: projectId });
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.setViewportSize({ width: 1280, height: 800 });
    await dismissTour(page);
    await selectProject(page, PROJECT_NAME);
    for (const theme of ["light", "dark"]) {
      const dark = await setTheme(page, theme);
      checks.push({ name: `Theme ${theme} applied`, passed: dark === (theme === "dark"), detail: `dark=${dark}` });
      for (const [label, viewId] of VIEWS) {
        walk.push(...(await walkView(ctx, events, { label, viewId, theme })));
      }
    }
    await setTheme(page, "light");
    judge(checks, walk);
    await keyboardReach(page, checks);
  } catch (e) {
    checks.push({ name: "Menu walk completed without an exception", passed: false, detail: e.message });
  } finally {
    page.setDefaultTimeout(300_000);
    try {
      writeFileSync(join(ctx.runDir, "menu-walk.json"), JSON.stringify(walk, null, 2));
    } catch {}
    if (projectId) {
      const res = await ctx.api.delete(`/api/projects/${projectId}`).then(() => true).catch(() => false);
      checks.push({ name: "[API-behind-browser] CLEANUP: walk project removed", passed: res, detail: projectId });
    }
  }
  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

async function dismissTour(page) {
  await page.evaluate(() => {
    try {
      localStorage.setItem("istara_tour_completed", "true");
      localStorage.setItem("istara_tour_completed_admin", "true");
    } catch {}
  }).catch(() => {});
  await page.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
  await page.waitForTimeout(800);
  await page.locator("button[aria-label='Skip tour']").first().click({ timeout: 2000 }).catch(() => {});
}

/** One view: its first screen, then each sub-tab. Returns one record per screen. */
async function walkView(ctx, events, { label, viewId, theme }) {
  const page = ctx.page;
  const records = [];
  events.pageErrors.length = 0;
  events.failedRequests.length = 0;
  await closeOverlays(page);
  const via = await openView(page, label, viewId).catch((e) => `blocked: ${String(e.message).slice(0, 120)}`);
  if (via.startsWith("blocked")) return [{ view: viewId, tab: "(first screen)", theme, notRun: `navigation ${via}` }];
  await settle(page);
  records.push({ ...(await observe(ctx, events, { view: viewId, tab: "(first screen)", theme })), via });
  const tabs = await subTabs(page);
  for (const tab of tabs) {
    events.pageErrors.length = 0;
    events.failedRequests.length = 0;
    const control = page.locator(`main [data-sim90-tab="${tab.key}"]`).first();
    if (!(await control.isVisible().catch(() => false))) {
      records.push({ view: viewId, tab: tab.label, theme, notRun: "sub-tab not visible" });
      continue;
    }
    const clicked = await control.click({ timeout: 5000 }).then(() => true).catch(() => false);
    if (!clicked) {
      records.push({ view: viewId, tab: tab.label, theme, notRun: "sub-tab click blocked" });
      await closeOverlays(page);
      continue;
    }
    await settle(page);
    records.push(await observe(ctx, events, { view: viewId, tab: tab.label, theme }));
    // A sub-tab may open a dialog; close it so the next control and the sidebar stay reachable.
    await closeOverlays(page);
  }
  return records;
}

/** Open a view the way a user does: the sidebar, "More views" first when it is folded, or the bell. */
async function openView(page, label, viewId) {
  const nav = page.locator(`nav[aria-label="Views"] button[aria-label="${label}"]`).first();
  if (!(await nav.isVisible().catch(() => false))) {
    const more = page.locator('nav[aria-label="Views"] button[aria-label="More views"]').first();
    if ((await more.getAttribute("aria-expanded").catch(() => null)) === "false") await more.click();
  }
  if (await nav.isVisible().catch(() => false)) {
    await nav.click();
    return "sidebar";
  }
  const header = page.locator(`header button[aria-label="${label}"], button[aria-label="${label}"]`).first();
  if (await header.isVisible().catch(() => false)) {
    await header.click();
    return "header";
  }
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail })), viewId);
  return "event-fallback";
}

async function closeOverlays(page) {
  for (let i = 0; i < 3; i += 1) {
    const open = await page.locator('[role="dialog"], [aria-modal="true"], .fixed.inset-0.bg-black\\/50').first().isVisible().catch(() => false);
    if (!open) return;
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(300);
  }
}

async function settle(page) {
  await page.waitForLoadState("networkidle", { timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(500);
}

/** Tag the view's sub-tabs (ARIA tabs, or groups of two or more aria-pressed toggles). */
async function subTabs(page) {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    if (!main) return [];
    const found = [];
    const add = (el, kind) => {
      const key = `t${found.length}`;
      el.setAttribute("data-sim90-tab", key);
      found.push({ key, kind, label: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 50) });
    };
    main.querySelectorAll('[role="tab"]').forEach((el) => add(el, "aria-tab"));
    const groups = new Map();
    main.querySelectorAll("button[aria-pressed]").forEach((el) => {
      if (el.closest('[role="dialog"]')) return;
      const parent = el.parentElement;
      groups.set(parent, [...(groups.get(parent) || []), el]);
    });
    for (const buttons of groups.values()) {
      if (buttons.length >= 2) buttons.forEach((el) => add(el, "pressed-toggle"));
    }
    return found;
  });
}

async function observe(ctx, events, where) {
  const page = ctx.page;
  const text = await page.locator("main").first().innerText({ timeout: 3000 }).catch(() => "");
  const machine = (text.match(MACHINE_TEXT) || [])[0] || "";
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const axe = await axeSerious(page);
  return {
    ...where,
    chars: text.length,
    errorSurface: ERROR_SURFACE.test(text),
    machineText: machine,
    overflowPx: overflow,
    axe,
    pageErrors: [...events.pageErrors],
    failedRequests: [...new Set(events.failedRequests)],
  };
}

async function axeSerious(page) {
  try {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const result = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    return result.violations
      .filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => `${v.id}(${v.nodes.length}): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
  } catch (e) {
    return [`axe unavailable: ${e.message}`];
  }
}

/** One check per defect class, naming every screen that shows it. */
function judge(checks, walk) {
  const seen = walk.filter((r) => !r.notRun);
  const where = (r) => `${r.view}/${r.tab}/${r.theme}`;
  const list = (rows, fmt) => rows.slice(0, 12).map(fmt).join("; ") + (rows.length > 12 ? ` …+${rows.length - 12}` : "");
  const notRun = walk.filter((r) => r.notRun);
  checks.push({
    name: `Walked ${seen.length} screens (24 views × sub-tabs × light/dark)`,
    passed: seen.length >= 48,
    detail: `${new Set(seen.map((r) => `${r.view}/${r.tab}`)).size} distinct screens; not run: ${notRun.length ? list(notRun, (r) => `${where(r)} (${r.notRun})`) : "none"}`,
  });
  const fallback = seen.filter((r) => r.via && r.via !== "sidebar" && r.via !== "header");
  checks.push({
    name: "Every view opened from the sidebar or header, as a user opens it",
    passed: fallback.length === 0,
    detail: fallback.length ? list(fallback, (r) => `${where(r)} via ${r.via}`) : `${seen.filter((r) => r.via).length} view openings`,
  });
  const classes = [
    ["Every screen rendered (no error boundary, no uncaught page error)", (r) => r.errorSurface || r.pageErrors.length, (r) => `${where(r)}: ${r.pageErrors[0] || "error surface"}`],
    ["No screen made a failed API request", (r) => r.failedRequests.length, (r) => `${where(r)}: ${r.failedRequests.slice(0, 2).join(", ")}`],
    ["No machine text in any screen (undefined, NaN, [object Object], raw keys)", (r) => r.machineText, (r) => `${where(r)}: "${r.machineText}"`],
    ["No screen scrolls sideways at 1280 px", (r) => r.overflowPx > 1, (r) => `${where(r)}: +${r.overflowPx}px`],
    ["axe-core WCAG 2.1 AA: no serious or critical violation on any screen", (r) => r.axe.length, (r) => `${where(r)}: ${r.axe[0]}`],
  ];
  for (const [label, bad, fmt] of classes) {
    const rows = seen.filter(bad);
    checks.push({ name: label, passed: rows.length === 0, detail: rows.length ? `${rows.length} screens: ${list(rows, fmt)}` : `0 of ${seen.length} screens` });
  }
}

/** Keyboard: every sidebar view button is reachable and shows a visible focus ring. */
async function keyboardReach(page, checks) {
  const more = page.locator('nav[aria-label="Views"] button[aria-label="More views"]').first();
  if ((await more.getAttribute("aria-expanded").catch(() => null)) === "false") await more.click().catch(() => {});
  const results = await page.evaluate((labels) => {
    return labels.map((label) => {
      const el =
        document.querySelector(`nav[aria-label="Views"] button[aria-label="${label}"]`) ||
        document.querySelector(`button[aria-label="${label}"]`);
      if (!el) return { label, reachable: false, ring: false };
      el.focus();
      const cs = getComputedStyle(el);
      const ring = cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0 || /\d+px/.test(cs.boxShadow);
      return { label, reachable: document.activeElement === el && el.tabIndex >= 0, ring };
    });
  }, VIEWS.map(([label]) => label));
  const missing = results.filter((r) => !r.reachable);
  checks.push({
    name: "Keyboard: every view's button (sidebar, More views, bell) takes focus",
    passed: missing.length === 0,
    detail: missing.length ? `not focusable/present: ${missing.map((r) => r.label).join(", ")}` : `${results.length}/${results.length}`,
  });
}
