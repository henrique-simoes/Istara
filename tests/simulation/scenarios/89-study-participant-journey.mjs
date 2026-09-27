/**
 * Scenario 89 — A research study through messaging channels, as a researcher runs it (2026-09-26).
 *
 * Professional-readiness review, Phase 1. Before this round a participant's greeting was stored as
 * the answer to question 1, the closing question's answer was lost, the wizard's adaptive switch
 * did nothing, there was no consent, screener, quota or reminder, the Questionnaire Studio came
 * pre-filled with sample answers that one click stored as evidence, and nothing could be exported.
 * This scenario drives the whole study the way a researcher does:
 *
 *   1. Deployments tab empty state, then the wizard: questions, consent (on by default) and a
 *      screener, adaptive follow-ups off, three channels, target 2, a closing question;
 *   2. the dashboard: Activate gives visible feedback; six synthetic participants answer through
 *      Telegram, Slack and WhatsApp (consent yes/no, screened out, STOP, completed, study full);
 *   3. the Participant Tracker shows each outcome; Export CSV downloads a pseudonymous file whose
 *      answers are attributed to the questions actually asked and contain no greetings, consent
 *      replies, screener answers or withdrawals;
 *   4. Pause: a participant is told the study is paused and nothing is stored;
 *   5. Surveys tab: the Questionnaire Studio starts empty and refuses to record nothing;
 *   6. the matrix: export error state, 375 px, dark mode through the app toggle, keyboard focus on
 *      Export CSV, and roles (researcher exports; viewer cannot create or export; stranger held).
 *
 * Participants are external to Istara, so their messages are API-behind-browser: they go through
 * `POST /api/channels/{id}/simulate-inbound`, the same inbound path a Telegram/Slack/WhatsApp
 * webhook takes. Channel adapters start against the local protocol simulator. Setup and cleanup are
 * API-behind-browser. Synthetic data only; credential-free (adaptive follow-ups are off, so no
 * model is needed).
 */

import { readFile } from "fs/promises";

import { ChannelProtocolSimulator } from "../lib/channel-protocol-simulator.mjs";
import { navigateTo, selectProject } from "../lib/embedding-settings.mjs";
import { keyboardFocusCheck, reflow375Check, setTheme } from "../lib/matrix-checks.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";
import { createVariantLedger } from "../lib/variant-obligations.mjs";

export const name = "Research study through messaging channels";
export const id = "89-study-participant-journey";

const PROJECT_NAME = "[SIM-89] Study journey";
const STUDY_NAME = "[SIM-89] Export habits";
const Q1 = "How do you share reports with your team today?";
const Q2 = "What slows that down?";
const CLOSING = "Is there anything else you would like to tell us?";
const SCREENER = "Do you export reports every week?";
const EXPORT_BUTTON = 'button:has-text("Export CSV")';
const WIZARD = 'section[aria-label="New deployment wizard"]';

export async function run(ctx) {
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=admin", expectation: "admin creates, runs, pauses and exports a study; attribution, consent, screener, quota and withdrawal hold" },
    { variantId: "role=researcher", expectation: "researcher opens the study dashboard and can export" },
    { variantId: "role=viewer", expectation: "viewer can follow studies but cannot create one or export raw data" },
    { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
  ]);

  const simulator = new ChannelProtocolSimulator({ port: 18089 });
  const state = { projectId: null, channels: {}, deploymentId: null, simulatorUrl: "" };
  const adminStart = checks.length;
  try {
    state.simulatorUrl = await simulator.start();
    await setup(ctx, checks, state);
    if (state.projectId) {
      await ctx.page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
      await selectProject(ctx.page, PROJECT_NAME);
      const steps = [emptyState, createThroughWizard, activateAndRunParticipants, trackerShowsOutcomes, exportCsv, pauseStudy, studioStartsEmpty, matrix];
      for (const step of steps) {
        await step(ctx, checks, state);
      }
    }
  } catch (e) {
    checks.push({ name: "Study journey completed without an exception", passed: false, detail: e.message });
  }
  const adminFailed = checks.slice(adminStart).filter((c) => !c.passed).length;

  const provisioning = await ensureRoleAccounts(ctx);
  if (state.projectId && provisioning.ok) {
    for (const role of ["researcher", "viewer"]) {
      try {
        await ctx.api.post(`/api/projects/${state.projectId}/members`, { user_id: provisioning.accounts[role].id, role });
      } catch {
        // already a member
      }
    }
  }
  for (const role of ["researcher", "viewer"]) {
    await driveRoleCell(ctx, {
      ledger,
      role,
      provisioning,
      shotName: `89-role-${role}`,
      drive: async (rolePage) => driveRole(rolePage, role),
    });
  }
  await driveRoleCell(ctx, { ledger, role: "stranger", provisioning, shotName: "89-role-stranger" });
  ledger.record({
    variantId: "role=admin",
    result: adminFailed === 0 ? "pass" : "fail",
    detail: adminFailed === 0 ? "admin study journey clean" : `${adminFailed} admin check(s) failed`,
    artifacts: ["screenshots/89-wizard-consent.png", "screenshots/89-tracker.png", "screenshots/89-dark.png"],
  });
  checks.push(...ledger.finalize());

  await cleanup(ctx, checks, state);
  await simulator.stop().catch(() => {});
  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

/** SETUP (API-behind-browser): a project and three channels started against the simulator. */
async function setup(ctx, checks, state) {
  const label = "[API-behind-browser] SETUP: project and three running channels (protocol simulator)";
  try {
    const project = await ctx.api.post("/api/projects", { name: PROJECT_NAME, description: "Scenario 89 study journey (synthetic data)" });
    state.projectId = project.id;
    const q = `?project_id=${encodeURIComponent(project.id)}`;
    const configs = {
      telegram: { bot_token: "123456789:SIM89_TELEGRAM", base_url: `${state.simulatorUrl}/bot`, secret_token: "sim89-tg-secret" },
      slack: { bot_token: "xoxb-sim89", signing_secret: "sim89-slack-secret", base_url: `${state.simulatorUrl}/` },
      whatsapp: { phone_number_id: "sim89_phone", access_token: "sim89_wa_token", verify_token: "sim89_verify", app_secret: "sim89_app_secret", graph_api_base: state.simulatorUrl },
    };
    const started = [];
    for (const [platform, config] of Object.entries(configs)) {
      const channel = await ctx.api.post("/api/channels", { platform, name: `[SIM-89] ${platform}`, config, project_id: project.id });
      state.channels[platform] = channel.id;
      const res = await ctx.api.post(`/api/channels/${channel.id}/start${q}`, {});
      started.push(`${platform}=${res.status}`);
    }
    const ok = started.every((s) => s.endsWith("started") || s.endsWith("already_running"));
    checks.push({ name: label, passed: ok, detail: started.join(" ") });
  } catch (e) {
    checks.push({ name: label, passed: false, detail: e.message });
  }
}

async function openDeployments(page) {
  await navigateTo(page, "Integrations", "integrations");
  const tab = page.locator("main button", { hasText: "Deployments" }).first();
  await tab.waitFor({ state: "visible", timeout: 15000 });
  await tab.click();
  await page.waitForTimeout(800);
}

/** 1a. Empty state: no deployments yet, honest zero counts, a way to create one. */
async function emptyState(ctx, checks) {
  const { page } = ctx;
  await openDeployments(page);
  const createFirst = page.locator("main button", { hasText: "Create First Deployment" }).first();
  const visible = await shows(createFirst, 10000);
  const answersCard = page.locator("div", { hasText: /^Answers Stored/ }).locator("xpath=..").first();
  await page.waitForTimeout(800);
  const text = await page.locator("main").first().innerText();
  const zeroAnswers = /Answers Stored\s*0/.test(text);
  checks.push({
    name: "Deployments empty state: create button and real zero counts (no fake 'Findings Created')",
    passed: visible && zeroAnswers && !text.includes("Findings Created"),
    detail: `createFirst=${visible} answersZero=${zeroAnswers} card=${!!answersCard}`,
  });
  await ctx.screenshot("89-deployments-empty");
}

/** 1b. The wizard, as a researcher fills it. */
async function createThroughWizard(ctx, checks) {
  const { page } = ctx;
  await page.locator("main button", { hasText: "Create First Deployment" }).first().click();
  const wizard = page.locator(WIZARD).first();
  await wizard.waitFor({ state: "visible", timeout: 15000 });
  await wizard.locator("button", { hasText: "Structured conversational interviews" }).first().click();
  await clickNext(page);

  const inputs = wizard.locator('input[aria-label^="Question"]');
  await inputs.nth(0).fill(Q1);
  await wizard.locator("button", { hasText: "Add Question" }).first().click();
  await inputs.nth(1).fill(Q2);
  await clickNext(page);

  const consentBox = wizard.locator("label", { hasText: "Ask for informed consent" }).locator('input[type="checkbox"]').first();
  const consentDefault = await consentBox.isChecked();
  const statement = await wizard.locator("#deployment-consent").inputValue();
  await wizard.locator("button", { hasText: "Add screening question" }).first().click();
  await wizard.locator('input[aria-label="Screening question 1"]').fill(SCREENER);
  await wizard.locator('input[aria-label="Qualifying answers for screening question 1"]').fill("yes");
  await ctx.screenshot("89-wizard-consent");
  checks.push({
    name: "Wizard: informed consent is on by default with an editable statement",
    passed: consentDefault && statement.includes("STOP"),
    detail: `checked=${consentDefault} statementChars=${statement.length}`,
  });
  await clickNext(page);

  const adaptive = wizard.locator("label", { hasText: "Enable Adaptive Follow-ups" }).locator('input[type="checkbox"]').first();
  if (await adaptive.isChecked()) await adaptive.click();
  await clickNext(page);

  for (const platform of ["telegram", "slack", "whatsapp"]) {
    await wizard.locator("label", { hasText: `[SIM-89] ${platform}` }).first().click();
  }
  await clickNext(page);

  await wizard.locator("#deployment-name").fill(STUDY_NAME);
  const target = wizard.locator("#deployment-target");
  await target.fill("2");
  await wizard.locator("#deployment-closing").fill(CLOSING);
  const targetCopy = await wizard.innerText();
  checks.push({
    name: "Wizard: the target explains what happens when it is reached (no false auto-complete claim)",
    passed: targetCopy.includes("new people are told the study is full") && !targetCopy.includes("auto-complete"),
    detail: "targets step copy",
  });
  await clickNext(page);

  const summary = await wizard.innerText();
  await wizard.locator("button", { hasText: "Create Deployment" }).first().click();
  const created = await page.locator("text=Deployment Created!").first().waitFor({ state: "visible", timeout: 15000 }).then(() => true).catch(() => false);
  checks.push({
    name: "Wizard: the summary names consent and screening, and the deployment is created",
    passed: created && summary.includes("asked first") && /Screening questions:\s*1/.test(summary),
    detail: `created=${created}`,
  });
  await wizard.locator("button", { hasText: "Done" }).first().click();
  await page.waitForTimeout(800);
}

async function clickNext(page) {
  await page.locator(WIZARD).locator("button", { hasText: "Next" }).last().click({ timeout: 10000 });
  await page.waitForTimeout(300);
}

async function say(ctx, state, platform, sender, text) {
  const q = `?project_id=${encodeURIComponent(state.projectId)}`;
  const res = await ctx.api.post(`/api/channels/${state.channels[platform]}/simulate-inbound${q}`, {
    text,
    sender_id: sender,
    sender_name: `Synthetic ${sender}`,
  });
  return res.reply || "";
}

/** 2. Activate from the dashboard, then six synthetic participants (API-behind-browser). */
async function activateAndRunParticipants(ctx, checks, state) {
  const { page } = ctx;
  await page.locator("main button", { hasText: STUDY_NAME }).first().click();
  await page.locator("main button", { hasText: "Activate" }).first().click();
  const live = await page.locator("text=Study is live").first().waitFor({ state: "visible", timeout: 10000 }).then(() => true).catch(() => false);
  const pauseShown = await page.locator("main button", { hasText: "Pause" }).first().isVisible().catch(() => false);
  checks.push({
    name: "Dashboard: Activate gives visible feedback and the controls follow the new state",
    passed: live && pauseShown,
    detail: `notice=${live} pauseButton=${pauseShown}`,
  });
  const deployments = await ctx.api.get(`/api/deployments?project_id=${encodeURIComponent(state.projectId)}`);
  state.deploymentId = (deployments || []).find((d) => d.name === STUDY_NAME)?.id || null;

  const label = "[API-behind-browser] participants answer through Telegram, Slack and WhatsApp";
  const replies = {};
  const script = [
    ["p1", "telegram", ["hi", "yes", "yes", "We email PDFs around", "Big exports time out", "No, that's all"]],
    ["p2", "slack", ["hello", "no", "actually exports are slow"]],
    ["p3", "whatsapp", ["hi", "yes", "no"]],
    ["p4", "slack", ["hi", "yes", "yes", "Shared drive", "STOP", "one more thing"]],
    ["p5", "whatsapp", ["hey", "sure", "Yes", "Screenshots in chat", "Finding the latest version", "Nothing else"]],
    ["p6", "telegram", ["hi there", "yes"]],
  ];
  try {
    for (const [sender, platform, texts] of script) {
      replies[sender] = [];
      for (const text of texts) replies[sender].push(await say(ctx, state, platform, sender, text));
    }
    const p1 = replies.p1;
    checks.push({
      name: `${label}: consent first, then screener, then questions, closing question asked on its own`,
      passed: p1[0].includes("YES") && !p1[0].includes(Q1) && p1[1].includes(SCREENER) && p1[2].includes(Q1) && p1[3] === Q2 && p1[4] === CLOSING,
      detail: JSON.stringify(p1.map((r) => r.slice(0, 40))),
    });
    checks.push({
      name: `${label}: a NO ends the study for that participant; screened out and STOP are honoured`,
      passed: !replies.p2[1].includes(Q1) && !replies.p2[2] && !replies.p3[2].includes(Q1) && /left the study/i.test(replies.p4[4]) && !replies.p4[5],
      detail: `p2=${JSON.stringify(replies.p2)} p3last=${replies.p3[2].slice(0, 40)} p4stop=${replies.p4[4].slice(0, 40)}`,
    });
    checks.push({
      name: `${label}: once 2 participants finished, a new participant is told the study is full`,
      passed: /all the participants it needs/i.test(replies.p6[0]) && !replies.p6[1],
      detail: `p6=${JSON.stringify(replies.p6)}`,
    });
  } catch (e) {
    checks.push({ name: label, passed: false, detail: e.message });
  }
}

/** 3a. The tracker shows each participant's outcome in words a researcher reads. */
async function trackerShowsOutcomes(ctx, checks) {
  const { page } = ctx;
  // Still on the dashboard opened before the participants arrived: it must refresh by itself.
  const updated = await page
    .locator("main", { hasText: "2 / 2 participants finished" })
    .first()
    .waitFor({ state: "visible", timeout: 25000 })
    .then(() => true)
    .catch(() => false);
  checks.push({
    name: "Dashboard refreshes by itself while open (participants finished counter updates)",
    passed: updated,
    detail: `counter reached 2/2 without reopening: ${updated}`,
  });
  await page.locator('button[aria-label="Back to deployments"]').first().click();
  await page.waitForTimeout(600);
  const overviewText = await page.locator("main").first().innerText();
  await page.locator("main button", { hasText: STUDY_NAME }).first().click();
  await page.locator("main button", { hasText: "Participant Tracker" }).first().click();
  await page.waitForTimeout(800);
  const text = await page.locator("main").first().innerText();
  const outcomes = ["completed", "declined consent", "screened out", "withdrew", "study full"];
  const missing = outcomes.filter((o) => !text.includes(o));
  await ctx.screenshot("89-tracker");
  checks.push({
    name: "Participant Tracker names every outcome (completed, declined, screened out, withdrew, study full)",
    passed: missing.length === 0,
    detail: missing.length ? `missing: ${missing.join(", ")}` : "all five outcomes shown",
  });
  checks.push({
    name: "Deployments overview counts real data (6 conversations, 2 finished, 7 answers)",
    passed: /Conversations Started\s*6/.test(overviewText) && /Participants Finished\s*2/.test(overviewText) && /Answers Stored\s*7/.test(overviewText),
    detail: overviewText.replace(/\s+/g, " ").slice(0, 200),
  });
}

/** 3b. Export CSV through the browser download, then read it. */
async function exportCsv(ctx, checks) {
  const { page } = ctx;
  try {
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 15000 }),
      page.locator(EXPORT_BUTTON).first().click(),
    ]);
    const path = await download.path();
    const csv = path ? await readFile(path, "utf8") : "";
    const rows = parseCsv(csv);
    const answers = rows.filter((r) => r.answer);
    const pairs = answers.map((r) => `${r.participant}|${r.question}|${r.answer}`);
    const expected = [
      `P01|${Q1}|We email PDFs around`, `P01|${Q2}|Big exports time out`, `P01|${CLOSING}|No, that's all`,
      `P04|${Q1}|Shared drive`,
      `P05|${Q1}|Screenshots in chat`, `P05|${Q2}|Finding the latest version`, `P05|${CLOSING}|Nothing else`,
    ];
    const leaked = ["hi", "hello", "yes", "no", "STOP", "sure", "hey", "one more thing", "actually exports are slow"].filter((t) => answers.some((r) => r.answer === t));
    checks.push({
      name: "Export CSV: every answer is attributed to the question actually asked; nothing else is data",
      passed: JSON.stringify(pairs) === JSON.stringify(expected) && leaked.length === 0,
      detail: leaked.length ? `leaked: ${leaked.join(",")}` : `${answers.length} answers, file ${download.suggestedFilename()}`,
    });
    const consent = Object.fromEntries(rows.map((r) => [r.participant, r.consent]));
    checks.push({
      name: "Export CSV: pseudonymous participants with consent status; no chat handles or names",
      passed: consent.P01 === "given" && consent.P02 === "declined" && !/Synthetic p\d|\bp[1-6]\b/.test(csv),
      detail: JSON.stringify(consent),
    });
  } catch (e) {
    checks.push({ name: "Export CSV downloads from the dashboard", passed: false, detail: e.message });
  }
}

/** Playwright's isVisible() does not wait; this does. */
async function shows(locator, timeout = 8000) {
  return locator.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
}

function parseCsv(text) {
  const lines = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); field = "";
      if (row.some((c) => c !== "")) lines.push(row);
      row = [];
    } else field += ch;
  }
  if (field || row.length) { row.push(field); lines.push(row); }
  const [header, ...body] = lines;
  return (body || []).map((cells) => Object.fromEntries((header || []).map((h, i) => [h, cells[i] ?? ""])));
}

/** 4. Pause: participants are told, and nothing they send is stored. */
async function pauseStudy(ctx, checks, state) {
  const { page } = ctx;
  await page.locator("main button", { hasText: "Pause" }).first().click();
  const notice = await page.locator("text=Study paused").first().waitFor({ state: "visible", timeout: 10000 }).then(() => true).catch(() => false);
  const resume = await page.locator("main button", { hasText: "Resume" }).first().isVisible().catch(() => false);
  let reply = "";
  let stored = -1;
  try {
    // A finished participant writes after the pause: nothing is stored and no agent answers.
    reply = await say(ctx, state, "telegram", "p1", "one more thought after pausing");
    const overview = await ctx.api.get(`/api/deployments/overview?project_id=${encodeURIComponent(state.projectId)}`);
    stored = overview.answers_stored;
  } catch (e) {
    reply = `error: ${e.message}`;
  }
  checks.push({
    name: "Pause gives feedback, offers Resume, and later messages are not stored",
    passed: notice && resume && stored === 7 && !/Istara agent|assistant/i.test(reply),
    detail: `notice=${notice} resume=${resume} answersStored=${stored} reply=${reply.slice(0, 60)}`,
  });
}

/** 5. The Questionnaire Studio records real answers only; it starts empty. */
async function studioStartsEmpty(ctx, checks) {
  const { page } = ctx;
  await page.locator('button[aria-label="Back to deployments"]').first().click().catch(() => {});
  await page.locator("main button", { hasText: "Surveys" }).first().click();
  await page.locator("main button", { hasText: "Questionnaire Studio" }).first().click();
  await page.waitForTimeout(600);
  const title = await page.locator("#studio-survey-title").inputValue().catch(() => "missing");
  const prefilled = await page.locator("main textarea").evaluateAll((els) => els.filter((el) => el.value.trim()).length).catch(() => -1);
  const text = await page.locator("main").first().innerText();
  await page.locator("main button", { hasText: "Record response" }).first().click();
  const refused = await shows(page.locator('[role="alert"]', { hasText: "enter at least one answer" }).first(), 5000);
  checks.push({
    name: "Questionnaire Studio starts empty (no sample answers) and refuses to record an empty response",
    passed: title === "" && prefilled === 0 && !text.includes("Caregiver") && !text.includes("Simulate Participant") && refused,
    detail: `title="${title}" prefilledAnswers=${prefilled} refused=${refused}`,
  });
  await ctx.screenshot("89-studio-empty");
}

/** 6. Error state, 375 px, dark theme, keyboard. */
async function matrix(ctx, checks, state) {
  const { page } = ctx;
  await page.locator("main button", { hasText: "Deployments" }).first().click();
  await page.locator("main button", { hasText: STUDY_NAME }).first().click();
  await page.waitForTimeout(600);

  // The export is a cross-origin request with an Authorization header: answer its CORS preflight
  // and send CORS headers, or the browser hides the 500 from the app.
  const origin = new URL(ctx.frontendUrl).origin;
  const cors = {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
  };
  let intercepted = 0;
  await page.route(/\/export\.csv/, (route) =>
    (intercepted += 1) && route.request().method() === "OPTIONS"
      ? route.fulfill({ status: 204, headers: cors })
      : route.fulfill({ status: 500, headers: { ...cors, "Content-Type": "application/json" }, body: JSON.stringify({ detail: "synthetic failure" }) }),
  );
  await page.locator(EXPORT_BUTTON).first().click();
  const errorShown = await page
    .locator('[role="alert"]', { hasText: "Export failed" })
    .first()
    .waitFor({ state: "visible", timeout: 8000 })
    .then(() => true)
    .catch(() => false);
  const messages = await page.locator('main [role="alert"], main [role="status"]').allInnerTexts().catch(() => []);
  await ctx.screenshot("89-export-error");
  await page.unroute(/\/export\.csv/);
  checks.push({
    name: "Export error is shown to the researcher (no silent failure)",
    passed: errorShown,
    detail: `alert=${errorShown} intercepted=${intercepted} messages=${JSON.stringify(messages).slice(0, 160)}`,
  });

  await keyboardFocusCheck(page, checks, { name: "Study dashboard", targetSelector: "button", targetText: "Export CSV", maxTabs: 60 });
  await reflow375Check(page, checks, { name: "Study dashboard" });

  const dark = await setTheme(page, "dark");
  await ctx.screenshot("89-dark");
  const exportVisible = await page.locator(EXPORT_BUTTON).first().isVisible().catch(() => false);
  checks.push({ name: "Dark theme (app toggle): the dashboard renders with its controls", passed: dark && exportVisible, detail: `dark=${dark}` });
  await setTheme(page, "light");
}

async function driveRole(page, role) {
  try {
    await selectProject(page, PROJECT_NAME);
    await navigateTo(page, "Integrations", "integrations");
    await page.locator("main button", { hasText: "Deployments" }).first().click({ timeout: 15000 });
    await page.waitForTimeout(800);
    const newButton = page.locator("main button", { hasText: "New Deployment" }).first();
    const canCreate = await newButton.isEnabled().catch(() => false);
    const study = page.locator("main button", { hasText: STUDY_NAME }).first();
    const seesStudy = await shows(study, 10000);
    if (seesStudy) await study.click();
    // Wait for the dashboard itself before judging whether Export is offered.
    const dashboard = seesStudy && (await shows(page.locator("main h2", { hasText: STUDY_NAME }).first(), 10000));
    await page.waitForTimeout(500);
    const exportShown = await page.locator(EXPORT_BUTTON).first().isVisible().catch(() => false);
    if (role === "viewer") {
      return { ok: dashboard && !canCreate && !exportShown, detail: `dashboard=${dashboard} canCreate=${canCreate} export=${exportShown}` };
    }
    return { ok: dashboard && canCreate && exportShown, detail: `dashboard=${dashboard} canCreate=${canCreate} export=${exportShown}` };
  } catch (e) {
    return { ok: false, detail: e.message };
  }
}

/** CLEANUP (API-behind-browser). */
async function cleanup(ctx, checks, state) {
  if (!state.projectId) return;
  const q = `?project_id=${encodeURIComponent(state.projectId)}`;
  try {
    if (state.deploymentId) await ctx.api.delete(`/api/deployments/${state.deploymentId}${q}`).catch(() => {});
    for (const channelId of Object.values(state.channels)) {
      await ctx.api.post(`/api/channels/${channelId}/stop${q}`, {}).catch(() => {});
      await ctx.api.delete(`/api/channels/${channelId}${q}`).catch(() => {});
    }
    await ctx.api.delete(`/api/projects/${state.projectId}`);
    checks.push({ name: "[API-behind-browser] CLEANUP: study, channels and project removed", passed: true, detail: state.projectId });
  } catch (e) {
    checks.push({ name: "[API-behind-browser] CLEANUP: study, channels and project removed", passed: false, detail: e.message });
  }
}
