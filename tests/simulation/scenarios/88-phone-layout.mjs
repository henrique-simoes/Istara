/**
 * Scenario 88 — Every view fits a phone (375 px), 2026-09-26.
 *
 * Settings, Quality, Skills, Backup, Ensemble health and Meta-Hyperagent sized their content column
 * to its widest card (Settings: 527 px at 375 px), and `main` clipped the right side of every card.
 * The page never scrolled sideways, so a scroll-width check could not see it. Chat kept its 224 px
 * chat list open, leaving the conversation 151 px with the send button off screen; Interviews kept
 * three columns (list 320 px, tags 288 px); the Documents toolbar and the Notifications header could
 * not wrap. This scenario drives each view at 375 px the way a phone user sees it:
 *
 *   1. every shell view: nothing inside the view is cut off and the page does not scroll sideways;
 *   2. Chat: the list starts closed; the "Chats" button opens it as a drawer; picking a chat closes
 *      it; Escape closes it; the send button is on screen;
 *   3. Interviews: with a synthetic transcript open, the interview fills the screen, "All interviews"
 *      returns to the list and picking the transcript opens it again; tags start collapsed and open
 *      over the interview, on screen;
 *   4. the matrix: keyboard Tab reaches the "Chats" button with visible focus and Enter opens the
 *      drawer; the dark theme renders the drawer; at 1280 px the chat list is an open column and
 *      Interviews keeps its list beside the interview.
 *
 * Setup and cleanup (the "[SIM-88]" project and its transcript upload) are API-behind-browser.
 * Synthetic data only; runs in the credential-free QA lane (layout does not depend on a model).
 */

import { getApiBase, authHeaders } from "../lib/api-client.mjs";
import { clippedInMain, keyboardFocusCheck } from "../lib/matrix-checks.mjs";
import { navigateTo, selectProject } from "../lib/embedding-settings.mjs";

export const name = "Every view fits a phone (375 px)";
export const id = "88-phone-layout";

const PROJECT_NAME = "[SIM-88] Phone layout";
const TRANSCRIPT = "s88-phone-interview.txt";
const VIEWS = [
  ["Chat", "chat"], ["Findings", "findings"], ["Tasks", "tasks"], ["Interviews", "interviews"],
  ["Documents", "documents"], ["Context", "context"], ["Memory", "memory"], ["Skills", "skills"],
  ["Agents", "agents"], ["History", "history"], ["Laws", "laws"], ["Loops", "loops"],
  ["Notifications", "notifications"], ["Backup", "backup"], ["Meta-Hyperagent", "meta-hyperagent"],
  ["Ensemble", "ensemble"], ["Quality", "quality"], ["Compute", "compute"], ["Integrations", "integrations"],
  ["Interfaces", "interfaces"], ["Autoresearch", "autoresearch"], ["Project settings", "project-settings"],
  ["Admin", "admin"], ["Settings", "settings"],
];
const DRAWER = "#chat-sessions";
const CHATS_BUTTON = 'button[aria-controls="chat-sessions"]';
const EXPLORER = 'aside[aria-label="Interviews explorer"]';
const TAGS = 'aside[aria-label="Tags and grounded nuggets"]';

export async function run(ctx) {
  const checks = [];
  const projectId = await setup(ctx, checks);
  try {
    await ctx.page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    if (projectId) await selectProject(ctx.page, PROJECT_NAME);
    await ctx.page.setViewportSize({ width: 375, height: 812 });
    await ctx.page.waitForTimeout(600);
    for (const step of [checkEveryView, checkChatDrawer, checkInterviews, checkKeyboard, checkDark]) {
      await step(ctx, checks);
    }
    await ctx.page.setViewportSize({ width: 1280, height: 800 });
    await ctx.page.waitForTimeout(600);
    await checkDesktop(ctx, checks);
  } catch (e) {
    checks.push({ name: "Phone journey completed without an exception", passed: false, detail: e.message });
  } finally {
    await cleanup(ctx, checks, projectId);
  }
  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

/** SETUP (API-behind-browser): a fresh project with one synthetic transcript. */
async function setup(ctx, checks) {
  const name = "[API-behind-browser] SETUP: a fresh project with one synthetic transcript";
  try {
    const created = await ctx.api.post("/api/projects", { name: PROJECT_NAME, description: "Scenario 88 phone layout (synthetic data)" });
    const form = new FormData();
    const text = "# Scenario88 interview\n\nInterviewer: Where do you keep receipts?\n\nP1: In the apron pocket until the van, then a shoebox.\n";
    form.append("file", new Blob([text], { type: "text/plain" }), TRANSCRIPT);
    const res = await fetch(`${getApiBase()}/api/files/upload/${created.id}`, { method: "POST", headers: authHeaders(), body: form });
    checks.push({ name, passed: !!created.id && res.ok, detail: `id=${created.id} upload=${res.status}` });
    return created.id || null;
  } catch (e) {
    checks.push({ name, passed: false, detail: e.message });
    return null;
  }
}

async function openView(page, label, viewId) {
  await navigateTo(page, label, viewId);
  await page.locator("main").first().waitFor({ state: "visible", timeout: 15000 });
  await page.waitForTimeout(1200);
  await dismissToasts(page);
}

/** A toast spans a phone's width at the top; a user dismisses it before reaching what it covers. */
async function dismissToasts(page) {
  const dismiss = page.locator('[aria-label="Toast notifications"] button[aria-label="Dismiss notification"]');
  for (let i = 0; i < 6 && (await dismiss.count()) > 0; i += 1) {
    await dismiss.first().click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(250);
  }
}

async function isOnScreen(page, selector) {
  const box = await page.locator(selector).first().boundingBox().catch(() => null);
  const width = page.viewportSize()?.width || 375;
  return !!box && box.width > 0 && box.x >= -1 && box.x + box.width <= width + 1;
}

/** 1. Every shell view: nothing cut off, no sideways page scroll. */
async function checkEveryView(ctx, checks) {
  const { page } = ctx;
  const bad = [];
  for (const [label, viewId] of VIEWS) {
    await openView(page, label, viewId);
    const clipped = await clippedInMain(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (clipped.length || overflow > 5) bad.push(`${viewId}: ${clipped.length} cut off${overflow > 5 ? `, page scrolls ${overflow}px` : ""} ${clipped.slice(0, 2).join("; ")}`);
    await ctx.screenshot(`88-375-${viewId}`);
  }
  checks.push({
    name: `375px: nothing is cut off in any of the ${VIEWS.length} views`,
    passed: bad.length === 0,
    detail: bad.length ? bad.join(" | ") : `${VIEWS.length} views clean`,
  });
}

/** 2. Chat: the list is a drawer on a phone. */
async function checkChatDrawer(ctx, checks) {
  const { page } = ctx;
  await openView(page, "Chat", "chat");
  const drawer = page.locator(DRAWER).first();
  const closedAtStart = !(await drawer.isVisible().catch(() => false));
  await page.locator(CHATS_BUTTON).first().click({ timeout: 10000 });
  const opened = await drawer.waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  const drawerOnScreen = opened && (await isOnScreen(page, DRAWER));
  const expanded = await page.locator(CHATS_BUTTON).first().getAttribute("aria-expanded");
  await ctx.screenshot("88-chat-drawer-open");
  await drawer.locator('button[aria-label="New chat"]').first().click({ timeout: 10000 });
  const closedAfterPick = await drawer.waitFor({ state: "hidden", timeout: 5000 }).then(() => true).catch(() => false);
  await page.locator(CHATS_BUTTON).first().click({ timeout: 10000 });
  await drawer.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  await page.keyboard.press("Escape");
  const closedByEscape = await drawer.waitFor({ state: "hidden", timeout: 5000 }).then(() => true).catch(() => false);
  checks.push({
    name: "Chat on a phone: the list starts closed, opens as a drawer, closes on a pick and on Escape",
    passed: closedAtStart && opened && drawerOnScreen && expanded === "true" && closedAfterPick && closedByEscape,
    detail: `closedAtStart=${closedAtStart} opened=${opened} onScreen=${drawerOnScreen} aria-expanded=${expanded} closedAfterPick=${closedAfterPick} closedByEscape=${closedByEscape}`,
  });
  const sendOnScreen = await isOnScreen(page, 'button[aria-label="Send message"]');
  const clipped = await clippedInMain(page);
  checks.push({
    name: "Chat on a phone: the send button is on screen and nothing is cut off",
    passed: sendOnScreen && clipped.length === 0,
    detail: `send=${sendOnScreen} cutOff=${clipped.length} ${clipped.slice(0, 2).join("; ")}`,
  });
}

/** 3. Interviews: the list and the interview take turns; tags open over the interview. */
async function checkInterviews(ctx, checks) {
  const { page } = ctx;
  await openView(page, "Interviews", "interviews");
  const back = page.getByRole("button", { name: "All interviews" }).first();
  const interviewFirst = await back.waitFor({ state: "visible", timeout: 10000 }).then(() => true).catch(() => false);
  const listHidden = !(await page.locator(EXPLORER).first().isVisible().catch(() => false));
  const tagsCollapsed = !(await page.locator(TAGS).first().isVisible().catch(() => false));
  await ctx.screenshot("88-interviews-open");
  await back.click({ timeout: 10000 });
  const listShown = await page.locator(EXPLORER).first().waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  const listFits = listShown && (await isOnScreen(page, EXPLORER));
  await ctx.screenshot("88-interviews-list");
  await page.locator(EXPLORER).first().getByText("s88", { exact: false }).first().click({ timeout: 10000 });
  const reopened = await back.waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  checks.push({
    name: "Interviews on a phone: the open interview fills the screen and 'All interviews' returns to the list",
    passed: interviewFirst && listHidden && listShown && listFits && reopened,
    detail: `interviewFirst=${interviewFirst} listHidden=${listHidden} listShown=${listShown} listFits=${listFits} reopened=${reopened}`,
  });
  await page.locator('button[aria-label="Expand tags and nuggets panel"]').first().click({ timeout: 10000 });
  const tagsOpen = await page.locator(TAGS).first().waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  const tagsFit = tagsOpen && (await isOnScreen(page, TAGS));
  await ctx.screenshot("88-interviews-tags");
  await page.locator('button[aria-label="Collapse tags and nuggets panel"]').first().click().catch(() => {});
  checks.push({
    name: "Interviews on a phone: tags start collapsed and open on screen over the interview",
    passed: tagsCollapsed && tagsOpen && tagsFit,
    detail: `collapsedAtStart=${tagsCollapsed} opened=${tagsOpen} onScreen=${tagsFit}`,
  });
}

/** 4a. Keyboard: Tab reaches "Chats" with visible focus; Enter opens the drawer. */
async function checkKeyboard(ctx, checks) {
  const { page } = ctx;
  await openView(page, "Chat", "chat");
  await page.locator("body").click({ position: { x: 5, y: 5 } }).catch(() => {});
  await keyboardFocusCheck(page, checks, { name: "Chats button (375px)", targetSelector: CHATS_BUTTON, maxTabs: 120 });
  await page.keyboard.press("Enter");
  const opened = await page.locator(DRAWER).first().waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  checks.push({ name: "Enter on the focused Chats button opens the drawer", passed: opened, detail: `opened=${opened}` });
  await page.keyboard.press("Escape");
}

/** 4b. Dark theme renders the drawer. */
async function checkDark(ctx, checks) {
  const { page } = ctx;
  const toDark = page.locator('button[aria-label="Switch to dark mode"]').first();
  const wasLight = await toDark.isVisible({ timeout: 3000 }).catch(() => false);
  if (wasLight) await toDark.click({ timeout: 10000 });
  await page.waitForTimeout(500);
  await dismissToasts(page);
  await page.locator(CHATS_BUTTON).first().click({ timeout: 10000 });
  await page.locator(DRAWER).first().waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  const isDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  const bg = await page.locator(DRAWER).first().evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "");
  await ctx.screenshot("88-chat-drawer-dark");
  checks.push({ name: "Dark theme renders the chat drawer", passed: isDark && !!bg && !/rgb\(255, 255, 255\)|rgba\(0, 0, 0, 0\)/.test(bg), detail: `html.dark=${isDark} bg=${bg}` });
  await page.keyboard.press("Escape");
  if (wasLight) await page.locator('button[aria-label="Switch to light mode"]').first().click().catch(() => {});
}

/** 4c. Desktop keeps the columns: the chat list is open, Interviews shows the list beside the interview. */
async function checkDesktop(ctx, checks) {
  const { page } = ctx;
  await openView(page, "Chat", "chat");
  const listOpen = await page.locator(DRAWER).first().isVisible().catch(() => false);
  const toggleHidden = !(await page.locator(CHATS_BUTTON).first().isVisible().catch(() => false));
  await openView(page, "Interviews", "interviews");
  const explorer = await page.locator(EXPLORER).first().isVisible().catch(() => false);
  const backHidden = !(await page.getByRole("button", { name: "All interviews" }).first().isVisible().catch(() => false));
  await ctx.screenshot("88-desktop-interviews");
  checks.push({
    name: "1280px keeps the desktop columns (chat list open, interview list beside the interview)",
    passed: listOpen && toggleHidden && explorer && backHidden,
    detail: `chatList=${listOpen} chatsButtonHidden=${toggleHidden} interviewList=${explorer} backHidden=${backHidden}`,
  });
}

/** CLEANUP (API-behind-browser): delete the scenario project; restore the desktop viewport. */
async function cleanup(ctx, checks, projectId) {
  await ctx.page.setViewportSize({ width: 1280, height: 800 }).catch(() => {});
  if (!projectId) return;
  const res = await fetch(`${getApiBase()}/api/projects/${projectId}`, { method: "DELETE", headers: authHeaders() }).catch(() => null);
  checks.push({ name: "[API-behind-browser] CLEANUP: the scenario project is deleted", passed: !!res && res.ok, detail: `status=${res?.status}` });
}
