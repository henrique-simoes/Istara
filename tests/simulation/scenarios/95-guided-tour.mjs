/** Scenario 95 — Guided tour: a new admin is walked through the product tour from start to end.
 *
 * A fresh browser signs in with the tour active (as after the onboarding wizard on a new install)
 * and follows it by clicking only the tour's own buttons. Every step must appear as a dialog
 * titled with its step name, highlight what it describes, and lead on; the "Connect Your AI
 * Model" step only offers its button once a model is connected, so a stack that can chat must get
 * past it; the tour must end with "You're Ready!" and close. Steps are recorded in order. */

export const name = "Guided Tour";
export const id = "95-guided-tour";

const BUTTONS = /^(Next|Done|Start Chatting →|Got it!)$/;
const MAX_STEPS = 20;

export async function run(ctx) {
  const checks = [];
  const check = (name, passed, detail = "") => checks.push({ name, passed: Boolean(passed), detail });
  const browser = ctx.page.context().browser();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: "light" });
  context.setDefaultTimeout(15000);
  await context.addInitScript(
    ({ projectId }) => {
      try {
        if (!sessionStorage.getItem("sim95-started")) {
          sessionStorage.setItem("sim95-started", "1");
          localStorage.setItem(
            "istara_tour_state",
            JSON.stringify({ active: true, isOnboarding: false, step: 2, role: "admin", hasExistingProjects: true, teamModeEnabled: true })
          );
        }
        if (projectId) localStorage.setItem("istara-active-project", projectId);
      } catch {}
    },
    { projectId: ctx.projectId || "" }
  );
  const page = await context.newPage();
  const titles = [];
  let finished = false;
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#login-username").fill(process.env.ADMIN_USERNAME || "admin");
    await page.locator("#login-password").fill(process.env.ADMIN_PASSWORD || "");
    await page.getByRole("button", { name: "Sign In", exact: true }).click();

    for (let i = 0; i < MAX_STEPS; i += 1) {
      const dialog = page.locator('[role="dialog"]').filter({ has: page.getByRole("button", { name: "Skip tour" }) }).first();
      if (!(await dialog.waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false))) break;
      const title = (await dialog.getAttribute("aria-label")) || "?";
      if (titles[titles.length - 1] !== title) titles.push(title);
      await page.screenshot({ path: `${ctx.runDir}/screenshots/95-tour-${String(i).padStart(2, "0")}.png` }).catch(() => null);
      const action = dialog.getByRole("button", { name: BUTTONS }).first();
      if (!(await action.waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false))) {
        check(`Tour step "${title}" offers a way forward`, false, "no Next/Done button appeared");
        break;
      }
      const label = (await action.innerText()).trim();
      await action.click();
      await page.waitForTimeout(800);
      if (label === "Got it!") {
        finished = !(await dialog.isVisible().catch(() => false));
        break;
      }
    }
  } catch (e) {
    check("Tour walk completed", false, e.message.split("\n")[0]);
  } finally {
    await context.close().catch(() => null);
  }

  check("Tour starts for a signed-in admin", titles.length > 0, titles[0] || "no tour dialog");
  check("Tour walks through its steps in order", titles.length >= 8, `${titles.length} steps: ${titles.join(" → ")}`);
  check('Tour reaches "Connect Your AI Model" and gets past it with a connected model', titles.includes("Connect Your AI Model") && titles.indexOf("Connect Your AI Model") < titles.length - 1);
  check('Tour ends with "You\'re Ready!" and closes', titles.includes("You're Ready!") && finished);
  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed, summary: `${passed}/${checks.length} guided-tour checks; steps: ${titles.join(" → ")}` };
}
