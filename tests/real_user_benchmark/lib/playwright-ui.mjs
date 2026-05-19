import { join } from "path";

const CHAT_INPUT_SELECTORS = [
  "textarea[placeholder*='Ask about your research']",
  "textarea[placeholder*='Viewer access is read-only']",
];

async function screenshot(page, logger, name) {
  const path = join(logger.paths.screenshots, `${String(logger.metrics.screenshots + 1).padStart(3, "0")}-${name}.png`);
  await page.screenshot({ path, fullPage: true }).catch(() => {});
  logger.noteScreenshot();
  logger.action("ui.screenshot", { name, path });
  return path;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function isVisible(page, selector, timeout = 250) {
  try {
    return await page.locator(selector).first().isVisible({ timeout });
  } catch {
    return false;
  }
}

async function bodyText(page) {
  try {
    return (await page.locator("body").innerText({ timeout: 1000 })).replace(/\s+/g, " ").trim();
  } catch {
    return "";
  }
}

async function clickByText(page, text) {
  const exact = new RegExp(`^${escapeRegExp(text)}$`, "i");
  const loose = new RegExp(escapeRegExp(text), "i");
  const locators = [
    page.getByRole("tab", { name: loose }),
    page.getByRole("button", { name: loose }),
    page.getByRole("link", { name: loose }),
    page.getByText(exact),
    page.getByText(loose),
  ];
  for (const locator of locators) {
    try {
      if (await locator.first().isVisible({ timeout: 1500 })) {
        await locator.first().click({ timeout: 5000 });
        return true;
      }
    } catch {}
  }
  return false;
}

async function installNetworkTokenRoute(page, api, logger) {
  const token = api?.networkAccessToken || "";
  const apiBase = api?.apiBase || "";
  if (!token || !apiBase) return;
  const basePattern = new RegExp(`^${escapeRegExp(apiBase.replace(/\/$/, ""))}/`);
  await page.route(basePattern, async (route) => {
    await route.continue({
      headers: {
        ...route.request().headers(),
        "X-Access-Token": token,
      },
    });
  });
  logger.action("ui.network_token_route.installed", { actor_token_configured: true });
}

const NAV_VIEW_IDS = new Map([
  ["Chat", "chat"],
  ["Documents", "documents"],
  ["Tasks", "tasks"],
  ["Findings", "findings"],
  ["Integrations", "integrations"],
  ["Interfaces", "interfaces"],
  ["Loops", "loops"],
  ["Autoresearch", "autoresearch"],
  ["Settings", "settings"],
]);

async function clickLocator(locator, method) {
  try {
    if ((await locator.count()) === 0) return null;
    const target = locator.first();
    await target.scrollIntoViewIfNeeded({ timeout: 1500 }).catch(() => {});
    if (await target.isVisible({ timeout: 1500 })) {
      await target.click({ timeout: 5000 });
      return { clicked: true, method };
    }
    await target.click({ timeout: 5000, force: true });
    return { clicked: true, method: `${method}:force` };
  } catch {
    return null;
  }
}

async function clickNavigationItem(page, text) {
  const exact = new RegExp(`^${escapeRegExp(text)}$`, "i");
  const sidebar = page.locator("aside[role='navigation']").first();
  const clickTab = async () => {
    const tabResult = await clickLocator(sidebar.getByRole("tab", { name: exact }), "sidebar-tab");
    if (tabResult) return tabResult;
    const buttonResult = await clickLocator(sidebar.getByRole("button", { name: exact }), "sidebar-button");
    if (buttonResult) return buttonResult;
    return await clickLocator(sidebar.locator("button").filter({ hasText: exact }), "sidebar-text");
  };

  const firstAttempt = await clickTab();
  if (firstAttempt) return firstAttempt;
  try {
    const more = sidebar.getByRole("button", { name: /More views|More/i }).first();
    if (await more.isVisible({ timeout: 1000 })) {
      await more.click({ timeout: 3000 });
      await page.waitForTimeout(250);
    }
  } catch {}
  const expandedAttempt = await clickTab();
  if (expandedAttempt) return expandedAttempt;

  const domAttempt = await page.evaluate((label) => {
    const normalize = (value) => String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
    const aside = document.querySelector("aside[role='navigation']");
    if (!aside) return { clicked: false, reason: "no-sidebar" };
    const candidates = Array.from(aside.querySelectorAll("button, [role='tab'], a"));
    const target = candidates.find((element) => {
      const accessible = element.getAttribute("aria-label") || element.getAttribute("title") || element.textContent;
      return normalize(accessible) === normalize(label);
    });
    if (!target) {
      return {
        clicked: false,
        reason: "target-not-found",
        candidates: candidates.map((element) => element.getAttribute("aria-label") || element.textContent || "").slice(0, 30),
      };
    }
    target.scrollIntoView({ block: "center", inline: "nearest" });
    target.click();
    return { clicked: true, label: target.getAttribute("aria-label") || target.textContent || "" };
  }, text);
  if (domAttempt.clicked) return { clicked: true, method: "dom-sidebar-click", detail: domAttempt };

  const view = NAV_VIEW_IDS.get(text);
  if (view) {
    await page.evaluate((viewId) => {
      localStorage.setItem("istara_active_view", viewId);
      window.dispatchEvent(new CustomEvent("istara:navigate", { detail: { view: viewId } }));
    }, view);
    return { clicked: true, method: "istara-navigate-event", detail: domAttempt };
  }

  return { clicked: false, method: "not-found", detail: domAttempt };
}

async function fillFirst(page, selectors, value) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    try {
      if (await locator.isVisible({ timeout: 1000 })) {
        await locator.fill(value);
        return true;
      }
    } catch {}
  }
  return false;
}

async function classifyUiState(page) {
  const text = await bodyText(page);
  const chatInputVisible = (await Promise.all(
    CHAT_INPUT_SELECTORS.map((selector) => isVisible(page, selector, 150)),
  )).some(Boolean);
  const navigationVisible = await isVisible(page, "aside[role='navigation']", 150);
  const mainVisible = await isVisible(page, "main#main-content", 150);
  const authFormVisible = (
    await isVisible(page, "#login-username, input[aria-label='Username'], textarea#join-connection-string", 150)
  );
  const loginVisible = !navigationVisible && (
    authFormVisible || /Sign In|Create Admin Account|Join Server/i.test(text)
  );
  const connecting = /Connecting to Istara/i.test(text);
  const serverUnreachable = /Cannot connect to the Istara server/i.test(text);
  const onboardingVisible = /Create your first project|Initial Setup|Save your recovery codes|Add a passkey/i.test(text);
  const noProject = /No Project Selected/i.test(text);
  const errorBoundary = /Something went wrong|Try again|Error/i.test(text) && mainVisible;

  let state = "unknown";
  if (!text && !mainVisible && !navigationVisible) state = "blank";
  else if (serverUnreachable) state = "server_unreachable";
  else if (connecting) state = "connecting";
  else if (chatInputVisible) state = "chat";
  else if (loginVisible) state = "login";
  else if (onboardingVisible) state = "onboarding";
  else if (noProject) state = "no_project";
  else if (navigationVisible && mainVisible) state = "shell";
  else if (errorBoundary) state = "error";

  return {
    state,
    url: page.url(),
    chatInputVisible,
    navigationVisible,
    mainVisible,
    textPreview: text.slice(0, 500),
  };
}

async function waitForUiState(page, logger, label, {
  timeoutMs = 45000,
  accepted = ["login", "chat", "shell", "no_project", "onboarding", "server_unreachable"],
} = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = await classifyUiState(page);
  while (Date.now() < deadline) {
    last = await classifyUiState(page);
    if (accepted.includes(last.state)) {
      logger.action("ui.state.ready", { label, ...last });
      return last;
    }
    await page.waitForTimeout(500);
  }
  logger.action("ui.state.timeout", { label, ...last });
  return last;
}

async function installBenchmarkSession(page, { api, projectId }) {
  if (!api.token) return;
  await page.evaluate(({ token, userId, projectId: activeProjectId }) => {
    const uid = userId || "benchmark-admin";
    localStorage.setItem("istara_token", token);
    localStorage.setItem("istara_auth_user_id", uid);
    localStorage.setItem("istara-active-project", activeProjectId);
    localStorage.setItem("istara_active_view", "chat");
    localStorage.setItem(`istara_tour_completed_${uid}`, "true");
    localStorage.setItem("istara_tour_completed_anonymous", "true");
    localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 0 }));
    window.dispatchEvent(new Event("istara:auth-changed"));
  }, { token: api.token, userId: api.userId, projectId });
}

async function performCredentialLogin(page, logger, credentials) {
  if (!credentials?.username || !credentials?.password) return false;
  const state = await classifyUiState(page);
  if (state.state !== "login") return false;

  const registering = /Create Admin Account/i.test(state.textPreview);
  logger.action("ui.auth.form_detected", { registering, state: state.state });

  try {
    await page.getByLabel("Username").fill(credentials.username, { timeout: 5000 });
    await page.getByLabel("Password").fill(credentials.password, { timeout: 5000 });
    if (registering) {
      const email = `${credentials.username}@benchmark.istara.local`;
      await page.getByLabel("Email").fill(email, { timeout: 5000 });
    }
    await page.getByRole("button", { name: registering ? /^Create Admin Account$/i : /^Sign In$/i }).click({ timeout: 5000 });
    await page.waitForTimeout(1000);
    const afterSubmit = await waitForUiState(page, logger, "after-ui-auth", {
      timeoutMs: 45000,
      accepted: ["chat", "shell", "onboarding", "no_project", "login", "server_unreachable"],
    });
    const ok = !["login", "server_unreachable", "blank", "connecting"].includes(afterSubmit.state);
    logger.action("ui.auth.result", { ok, ...afterSubmit });
    return ok;
  } catch (error) {
    logger.action("ui.auth.error", { error: error.message, state });
    return false;
  }
}

async function captureDiagnostics(page, logger, title, detail, severity = "medium") {
  const state = await classifyUiState(page);
  await screenshot(page, logger, `diagnostic-${title}`.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase());
  logger.action("ui.diagnostic", { title, detail, ...state });
  logger.issue({
    area: "ui",
    severity,
    title,
    detail: `${detail} Current UI state: ${state.state}. Body preview: ${state.textPreview}`,
  });
  return state;
}

function attachPageDiagnostics(page, logger) {
  const counters = { console: 0, pageerror: 0, requestfailed: 0, http: 0 };
  page.on("console", (message) => {
    if (counters.console >= 80) return;
    counters.console += 1;
    const type = message.type();
    if (["error", "warning"].includes(type)) {
      logger.action("ui.console", { type, text: message.text().slice(0, 1000) });
    }
  });
  page.on("pageerror", (error) => {
    if (counters.pageerror >= 40) return;
    counters.pageerror += 1;
    logger.action("ui.pageerror", { error: error.message.slice(0, 1000) });
  });
  page.on("requestfailed", (request) => {
    if (counters.requestfailed >= 80) return;
    counters.requestfailed += 1;
    logger.action("ui.requestfailed", {
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "",
    });
  });
  page.on("response", (response) => {
    if (counters.http >= 80 || response.status() < 400) return;
    counters.http += 1;
    logger.action("ui.http_error", {
      status: response.status(),
      url: response.url(),
    });
  });
}

export async function runUiJourney({ frontendUrl, api, projectId, logger, chatTurns = [], credentials = null, actor = "admin" }) {
  let chromium;
  try {
    ({ chromium } = await import("playwright"));
  } catch {
    ({ chromium } = await import("../../simulation/node_modules/playwright/index.mjs"));
  }
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 920 },
    recordVideo: undefined,
  });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false }).catch(() => {});
  const page = await context.newPage();
  attachPageDiagnostics(page, logger);
  const results = {
    visited: false,
    onboarding: false,
    chatUiTurns: 0,
    uploadAttempted: false,
    nav: [],
    finalState: "",
  };

  try {
    logger.action("ui.journey.start", { actor });
    await installNetworkTokenRoute(page, api, logger);
    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
    results.visited = true;
    await screenshot(page, logger, "landing");

    let state = await waitForUiState(page, logger, "landing");
    if (state.state === "login") {
      const loggedIn = await performCredentialLogin(page, logger, credentials);
      if (loggedIn) await screenshot(page, logger, "ui-login-complete");
      state = await classifyUiState(page);
    }

    if (api.token && projectId && ["chat", "shell", "no_project", "onboarding"].includes(state.state)) {
      logger.action("ui.session.align", {
        reason: state.state,
        note: "Completing benchmark tour state and selecting the generated project after real UI authentication.",
      });
      await installBenchmarkSession(page, { api, projectId });
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
      await screenshot(page, logger, "authenticated-chat-ready");
      state = await waitForUiState(page, logger, "after-session-align", {
        accepted: ["chat", "shell", "no_project", "onboarding", "server_unreachable"],
      });
    }

    if (api.token && ["login", "blank", "connecting", "server_unreachable", "onboarding", "no_project"].includes(state.state)) {
      logger.action("ui.session.install", {
        reason: state.state,
        note: "Installing known benchmark session after observing current app state.",
      });
      await installBenchmarkSession(page, { api, projectId });
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
      await screenshot(page, logger, "authenticated-home");
      state = await waitForUiState(page, logger, "after-session-install", {
        accepted: ["chat", "shell", "no_project", "onboarding", "server_unreachable"],
      });
    }

    results.onboarding = ["chat", "shell", "no_project"].includes(state.state);
    if (!["chat", "shell", "no_project"].includes(state.state)) {
      results.finalState = state.state;
      await captureDiagnostics(page, logger, "Playwright UI shell was not ready", "The benchmark did not navigate because the app shell was not in a usable state.", "high");
      return results;
    }

    for (const nav of ["Chat", "Documents", "Tasks", "Findings", "Integrations", "Interfaces", "Loops", "Autoresearch", "Settings"]) {
      const beforeNav = await waitForUiState(page, logger, `before-nav-${nav}`, {
        timeoutMs: 15000,
        accepted: ["chat", "shell", "no_project"],
      });
      if (!["chat", "shell", "no_project"].includes(beforeNav.state)) {
        results.nav.push({ nav, clicked: false, reason: beforeNav.state });
        logger.action("ui.nav.skip", { nav, reason: beforeNav.state });
        continue;
      }
      const navResult = await clickNavigationItem(page, nav);
      results.nav.push({ nav, ...navResult });
      logger.action("ui.nav", { nav, ...navResult });
      if (navResult.clicked) {
        await page.waitForTimeout(700);
        await screenshot(page, logger, `nav-${nav.toLowerCase()}`);
      }
    }

    const chatNavResult = await clickNavigationItem(page, "Chat");
    logger.action("ui.nav.return_to_chat", chatNavResult);
    await waitForUiState(page, logger, "chat-before-turns", {
      timeoutMs: 20000,
      accepted: ["chat", "shell", "no_project"],
    });
    for (const turn of chatTurns.slice(0, 5)) {
      let filled = await fillFirst(page, CHAT_INPUT_SELECTORS, turn.content);
      if (!filled) {
        const chatState = await classifyUiState(page);
        logger.action("ui.chat_input.retry", { turn: turn.turn, ...chatState });
        if (api.token) {
          await installBenchmarkSession(page, { api, projectId });
          const retryNavResult = await clickNavigationItem(page, "Chat");
          logger.action("ui.nav.retry_chat", retryNavResult);
          await page.waitForTimeout(750);
          filled = await fillFirst(page, CHAT_INPUT_SELECTORS, turn.content);
        }
      }
      if (!filled) {
        await captureDiagnostics(
          page,
          logger,
          "Chat composer unavailable after UI readiness checks",
          "Playwright waited for render, verified the app state, retried session/project selection, and still could not locate a usable Chat composer.",
          "high",
        );
        break;
      }
      const sent = await clickByText(page, "Send message") || await clickByText(page, "Send");
      if (!sent) {
        await page.keyboard.press("Meta+Enter").catch(() => {});
        await page.keyboard.press("Enter").catch(() => {});
      }
      results.chatUiTurns += 1;
      await page.waitForTimeout(1200);
      await screenshot(page, logger, `chat-turn-${turn.turn}`.replace(/\s+/g, "-"));
    }

    try {
      results.uploadAttempted = (await page.locator("input[type=file]").count()) > 0;
    } catch {
      results.uploadAttempted = false;
    }
    logger.action("ui.chat_upload_probe", { upload_input_present: results.uploadAttempted });
    const finalState = await classifyUiState(page);
    results.finalState = finalState.state;
    logger.action("ui.final_state", finalState);
  } catch (error) {
    logger.issue({
      area: "ui",
      severity: "high",
      title: "Playwright UI journey failed",
      detail: error.message,
    });
  } finally {
    await context.tracing.stop({ path: join(logger.paths.traces, `ui-journey-${actor}-trace.zip`) }).catch(() => {});
    await browser.close().catch(() => {});
  }
  return results;
}
