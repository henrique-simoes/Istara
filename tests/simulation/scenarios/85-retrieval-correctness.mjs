/**
 * Scenario 85 — Retrieval correctness in the Memory view (September 2026 evaluation fixes).
 *
 * Drives the knowledge-base search the way a researcher does — navigate to Memory, type a query,
 * press Search, read the results — and asserts WHAT comes back, not only that something does:
 *
 *   1. a two-word query returns the exact-phrase match AND a chunk with the same words apart
 *      (keyword search used to run the OR query only when the phrase matched nothing);
 *   2. a two-character research token ("UX") retrieves its chunk (tokens of <= 2 chars were dropped);
 *   3. reprocessing an uploaded file does not grow the index (deletes used the basename while chunks
 *      are stored under the full path, so every reprocess appended another copy);
 *   4. the results show a rank, not the raw fusion score as a percentage ("1.6%" for the best match);
 *   5. the Memory view passes the matrix AGENTS.md asks of every changed surface: keyboard focus is
 *      visible on the search box, 375px reflow has no horizontal scroll, dark mode renders, and
 *      axe-core WCAG 2.1 AA finds no serious or critical violation on the results in the light and
 *      the dark theme, each set through the app's own toggle (2026-09-26: the dark theme's grey
 *      metadata text was 4.23:1, unseen while only one theme was scanned).
 *
 * Steps 1-3 seed and reprocess through the API (labelled "API-behind-browser" per AGENTS.md); every
 * assertion about retrieval is read from the rendered page. Synthetic data only. Runs in the
 * credential-free QA lane: under the provider stub embeddings are hash noise, so what this measures
 * is the keyword path and the fusion plumbing, which is exactly where the defects were.
 *
 * What discriminates in this lane: the rank badge (old code rendered a percentage) and reprocess
 * idempotence (old code appended a copy per reprocess). The two relevance checks (1, 2) are presence
 * checks here, because a noise vector above the 0.3 threshold can surface either chunk; the keyword
 * behaviour behind them is pinned by tests/test_retrieval_correctness_fixes.py, which fails on
 * origin/main. On the live lane, with real embeddings, they read as relevance checks.
 */

import { getApiBase, authHeaders } from "../lib/api-client.mjs";
import { setTheme } from "../lib/matrix-checks.mjs";

export const name = "Retrieval correctness (Memory search)";
export const id = "85-retrieval-correctness";

const DOC_PHRASE = [
  "Scenario85 marker ALPHA.",
  "Participants said the billing previews were confusing during checkout.",
  "They asked for clearer totals before paying.",
].join("\n");
const DOC_APART = [
  "Scenario85 marker BRAVO.",
  "P1 reported that the UX of the export flow felt slow.",
  "The billing tab hid the order previews until the last step.",
].join("\n");

async function upload(ctx, name, text) {
  const form = new FormData();
  form.append("file", new Blob([text], { type: "text/plain" }), name);
  const res = await fetch(`${getApiBase()}/api/files/upload/${ctx.projectId}`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  return res;
}

async function keywordChunks(ctx) {
  const stats = await ctx.api.get(`/api/memory/${ctx.projectId}/stats`);
  return stats.keyword_chunks;
}

async function openMemory(ctx) {
  const { page } = ctx;
  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('button[aria-label="Memory"], main', { timeout: 15000 }).catch(() => {});
  const projectBtn = page.locator("text=[SIM]").first();
  if (await projectBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectBtn.click();
  }
  const nav = page.locator('button[aria-label="Memory"]').first();
  if (await nav.isVisible({ timeout: 3000 }).catch(() => false)) {
    await nav.click();
  } else {
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "memory" })));
  }
  await page.waitForSelector('input[aria-label="Search knowledge base"]', { timeout: 15000 });
}

async function searchInUi(ctx, query) {
  const { page } = ctx;
  const box = page.locator('input[aria-label="Search knowledge base"]');
  await box.fill(query);
  // The view clears its results before it fetches, so waiting for THIS search's response and then
  // for the region (or the empty state) cannot read the previous search's results. A CSS list mixed
  // with a `text=` engine is not a valid selector, which is what the first version of this wait was:
  // it threw, the catch swallowed it, and the page was read before anything rendered.
  const response = page
    .waitForResponse(
      (r) => r.url().includes(`/api/memory/${encodeURIComponent(ctx.projectId)}/search`) && r.request().method() === "GET",
      { timeout: 20000 },
    )
    .catch(() => null);
  await page.locator('button[aria-label="Run search"]').click();
  await response;
  const region = page.locator('[role="region"][aria-label="Search results"]');
  const empty = page.getByText("No results found.", { exact: true });
  await region.or(empty).first().waitFor({ state: "visible", timeout: 20000 }).catch(() => {});
  if (!(await region.isVisible().catch(() => false))) return { text: "", badges: [] };
  const text = await region.innerText();
  const badges = await region.locator("[data-testid=memory-result-rank]").allInnerTexts();
  return { text, badges };
}

export async function run(ctx) {
  const checks = [];
  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // ── Seed (API-behind-browser) ──
  const before = await keywordChunks(ctx).catch(() => null);
  const a = await upload(ctx, "s85-phrase.txt", DOC_PHRASE);
  const b = await upload(ctx, "s85-apart.txt", DOC_APART);
  checks.push({ name: "[API-behind-browser] seed two synthetic transcripts", passed: a.ok && b.ok, detail: `status=${a.status}/${b.status}` });
  const afterUpload = await keywordChunks(ctx).catch(() => null);

  // ── 1. phrase first, non-adjacent terms still retrieved ──
  await openMemory(ctx);
  const phrase = await searchInUi(ctx, "billing previews");
  await ctx.screenshot("85-search-billing-previews");
  checks.push({
    name: "Search 'billing previews' shows the exact-phrase chunk",
    passed: phrase.text.includes("Scenario85 marker ALPHA"),
    detail: phrase.text.slice(0, 160),
  });
  checks.push({
    name: "…and the chunk with the same words apart (BM25 over every term, not phrase-only)",
    passed: phrase.text.includes("Scenario85 marker BRAVO"),
    detail: phrase.text.includes("Scenario85 marker BRAVO") ? "both documents listed" : "only the phrase match was returned",
  });

  // ── 4. rank, not a raw fused score rendered as a percentage ──
  checks.push({
    name: "Results show a rank, not the raw fusion score as a percentage",
    passed: phrase.badges.length > 0 && phrase.badges.every((badge) => /^#\d+$/.test(badge.trim())),
    detail: `badges=${JSON.stringify(phrase.badges.slice(0, 5))}`,
  });

  // ── 2. two-character research token ──
  const ux = await searchInUi(ctx, "UX");
  checks.push({
    name: "Search 'UX' retrieves the chunk that uses it (two-character tokens are kept)",
    passed: ux.text.includes("Scenario85 marker BRAVO"),
    detail: ux.text.slice(0, 160),
  });

  // ── 3. reprocess does not duplicate (API-behind-browser) ──
  const reprocess = await fetch(`${getApiBase()}/api/files/${ctx.projectId}/reprocess`, {
    method: "POST",
    headers: authHeaders(),
  }).catch((e) => ({ ok: false, status: e.message }));
  const afterReprocess = await keywordChunks(ctx).catch(() => null);
  checks.push({
    name: "[API-behind-browser] reprocessing does not grow the keyword index",
    passed: reprocess.ok && afterUpload !== null && afterReprocess === afterUpload,
    detail: `before=${before} afterUpload=${afterUpload} afterReprocess=${afterReprocess} status=${reprocess.status}`,
  });

  // ── 5. the matrix: keyboard, reflow, dark mode, axe ──
  const { page } = ctx;
  await openMemory(ctx);
  await page.locator('input[aria-label="Search knowledge base"]').focus();
  const focusVisible = await page.evaluate(() => {
    const el = document.activeElement;
    if (!el) return false;
    const style = getComputedStyle(el);
    return style.outlineStyle !== "none" || style.boxShadow !== "none";
  });
  checks.push({ name: "Keyboard focus on the search box is visible", passed: focusVisible, detail: `focus-visible=${focusVisible}` });

  const viewport = page.viewportSize();
  await page.setViewportSize({ width: 375, height: 812 });
  await searchInUi(ctx, "billing previews");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  await ctx.screenshot("85-memory-375px");
  checks.push({ name: "375px reflow: no horizontal page scroll", passed: overflow <= 1, detail: `overflow=${overflow}px` });
  if (viewport) await page.setViewportSize(viewport);

  // Both themes, through the app's own toggle (an earlier scenario may have stored a choice).
  const startedDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  for (const theme of ["light", "dark"]) {
    const isDark = await setTheme(page, theme);
    await openMemory(ctx);
    await searchInUi(ctx, "billing previews");
    if (theme === "dark") {
      await ctx.screenshot("85-memory-dark");
      const darkBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      checks.push({ name: "Dark mode renders the results", passed: isDark && !/rgb\(255, 255, 255\)/.test(darkBg), detail: `html.dark=${isDark} body=${darkBg}` });
    }
    checks.push({ name: `axe-core WCAG 2.1 AA (${theme}): no serious or critical violation on the results`, ...(await axeResults(page)) });
  }
  await setTheme(page, startedDark ? "dark" : "light");

  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

async function axeResults(page) {
  try {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const result = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    const detail = blocking.length
      ? blocking
          .map((v) => `${v.id}(${v.nodes.length}): ${v.nodes.slice(0, 3).map((n) => `${n.target.join(" ")} ${(n.any?.[0]?.message || "").slice(0, 90)}`).join(" | ")}`)
          .join("; ")
      : `0 serious/critical; ${result.violations.length} minor/moderate`;
    return { passed: blocking.length === 0, detail };
  } catch (e) {
    return { passed: false, detail: e.message };
  }
}
