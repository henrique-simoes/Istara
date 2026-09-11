/**
 * Shared role/variant driver for auth-adjacent simulation scenarios
 * (remediation plan W1.4-W1.5, blocker B5 — testing-to-main-remediation-20260909).
 *
 * Every scenario that touches an authenticated surface declares machine-checkable
 * cells for admin, researcher, viewer, and stranger. This helper provisions the
 * two synthetic non-admin roles and drives each cell in an ISOLATED browser
 * context:
 *
 *   - Provisioning is labeled SETUP: it uses the admin API (POST /api/auth/users,
 *     PATCH /api/auth/users/{id}/role, project membership) and is excluded from
 *     browser-act claims. The repository's admin UI has no create-user form
 *     (invite strings are a different token type), so an unavoidable provisioning
 *     API is the plan-sanctioned setup path.
 *   - Everything else is a real browser act: form login through the visible
 *     login screen, navigation clicks, and visible-state assertions. The
 *     localStorage init script below is lane setup (tour dismissal + active
 *     project), the same class of setup the runner already performs for admin.
 *   - `stranger` starts unauthenticated and must be held at the login screen.
 *   - Role cells REQUIRE the QA lane to run with TEAM_MODE enabled (real DB
 *     accounts). A credential-free required cell may never be recorded as
 *     not_runnable (variant-obligations contract), so a lane without role
 *     accounts records an honest FAIL naming the missing capability.
 */

import { join } from "path";

const ROLE_VIEWPORT = { width: 1280, height: 800 };
const SHELL_WAIT_TIMEOUT = 20000;

export const ROLE_CELLS = Object.freeze([
  { variantId: "role=admin", expectation: "authenticated admin drives the journey" },
  { variantId: "role=researcher", expectation: "synthetic researcher account drives the journey" },
  { variantId: "role=viewer", expectation: "synthetic viewer account drives the journey" },
  { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
]);

async function probeTeamMode(ctx) {
  // GET /api/auth/team-status is the same probe scenario 32 uses.
  const status = await ctx.api.get("/api/auth/team-status");
  return status;
}

function roleUsername(role) {
  return `qa-${role}-synthetic`;
}

function rolePassword() {
  return process.env.QA_ROLE_PASSWORD || process.env.ADMIN_PASSWORD || "";
}

async function findUserId(ctx, username) {
  try {
    const users = await ctx.api.get("/api/auth/users");
    const match = Array.isArray(users) ? users.find((u) => u.username === username) : null;
    return match ? match.id : null;
  } catch {
    return null;
  }
}

/**
 * Labeled SETUP: create (or reuse) the synthetic researcher/viewer accounts and
 * grant project membership. Returns { ok, accounts } or { ok: false, error }.
 */
export async function ensureRoleAccounts(ctx) {
  const password = rolePassword();
  if (!password) {
    return {
      ok: false,
      error:
        "capability: qa-lane credentials — no lane password available (ADMIN_PASSWORD/QA_ROLE_PASSWORD unset), role cells cannot log in honestly",
    };
  }

  let team = null;
  try {
    team = await probeTeamMode(ctx);
  } catch (e) {
    return { ok: false, error: `team-status probe failed: ${e.message}` };
  }
  if (team && team.team_mode === false) {
    return {
      ok: false,
      error:
        "capability: qa-lane TEAM_MODE role accounts — the lane runs local-mode admin only, so researcher/viewer logins are impossible (set QA_TEAM_MODE=true)",
    };
  }

  const accounts = {};
  for (const role of ["researcher", "viewer"]) {
    const username = roleUsername(role);
    let userId = await findUserId(ctx, username);
    if (!userId) {
      try {
        const created = await ctx.api.post("/api/auth/users", {
          username,
          password,
          email: `${username}@example.invalid`,
          display_name: `QA Synthetic ${role}`,
        });
        userId = created.id;
      } catch (e) {
        if (!String(e.message).includes("409")) {
          return { ok: false, error: `could not provision ${username}: ${e.message}` };
        }
        userId = await findUserId(ctx, username);
      }
    }
    if (!userId) return { ok: false, error: `could not resolve id for ${username}` };

    if (role === "viewer") {
      // The provisioning API creates researchers; promote the viewer account.
      try {
        await ctx.api.patch(`/api/auth/users/${userId}/role`, { role: "viewer" });
      } catch (e) {
        return { ok: false, error: `could not set ${username} to viewer: ${e.message}` };
      }
    }

    if (ctx.projectId) {
      try {
        await ctx.api.post(`/api/projects/${ctx.projectId}/members`, { user_id: userId, role });
      } catch {
        // Already a member (or the membership API refused) — the role user still
        // exists; the drive step records the honest outcome either way.
      }
    }
    accounts[role] = { id: userId, username, password };
  }
  return { ok: true, accounts };
}

async function waitForMarker(page, locator, timeoutMs = SHELL_WAIT_TIMEOUT) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await locator.isVisible({ timeout: 1000 }).catch(() => false)) return true;
    await page.waitForTimeout(500);
  }
  return false;
}

/**
 * Drive one role cell in an isolated context. `drive(page, helpers)` performs
 * the scenario's real browser acts for an AUTHENTICATED role and returns
 * { ok, detail, artifacts? }. For `stranger`, the helper itself asserts the
 * login-screen hold. The result is recorded into the variant ledger.
 */
export async function driveRoleCell(ctx, { ledger, role, provisioning, drive, shotName }) {
  const cell = ROLE_CELLS.find((c) => c.variantId === `role=${role}`);
  const expectation = cell ? cell.expectation : `role=${role}`;

  const browser = ctx.page.context().browser();
  const context = await browser.newContext({
    viewport: ROLE_VIEWPORT,
    colorScheme: "dark",
  });
  context.setDefaultTimeout(15000);
  const page = await context.newPage();
  // Evidence integrity: capture the ROLE page itself. ctx.screenshot() closes
  // over the runner's admin page, so using it here would misattribute admin
  // screenshots as role evidence (W2 finding F-W2-2). Write to the same run
  // screenshots dir via ctx.runDir instead.
  const shot = async (suffix) => {
    if (typeof shotName !== "string") return;
    try {
      await page.screenshot({ path: join(ctx.runDir, "screenshots", `${shotName}-${suffix}.png`) });
    } catch {}
  };

  try {
    // Lane setup (same class as the runner's admin init): dismiss the tour
    // with the keys the tour store actually reads (istara_tour_state +
    // per-user istara_tour_completed_<id> — the bare legacy flags alone do
    // not suppress it, W2 round-2 evidence) and preselect the shared
    // simulation project before the visitor arrives.
    const setupUserId =
      provisioning.ok && role !== "stranger" && provisioning.accounts[role]
        ? provisioning.accounts[role].id
        : "";
    await context.addInitScript(
      ({ projectId, userId }) => {
        try {
          localStorage.setItem("istara_tour_completed", "true");
          localStorage.setItem("istara_tour_completed_admin", "true");
          localStorage.setItem(
            "istara_tour_state",
            JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }),
          );
          if (projectId) localStorage.setItem("istara-active-project", projectId);
          if (userId) {
            localStorage.setItem("istara_auth_user_id", userId);
            localStorage.setItem(`istara_tour_completed_${userId}`, "true");
          }
        } catch {}
      },
      { projectId: ctx.projectId || "", userId: setupUserId },
    );

    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);

    if (role === "stranger") {
      const logo = await waitForMarker(page, page.locator('[aria-label="Istara logo"]').first(), 10000);
      const shellHidden = !(await page.locator('nav[aria-label="Views"]').isVisible().catch(() => false));
      await shot("stranger-login");
      ledger.record({
        variantId: "role=stranger",
        result: logo && shellHidden ? "pass" : "fail",
        detail: `unauthenticated visit held at login screen: logo=${logo} shellHidden=${shellHidden}`,
        artifacts: shotName ? [`screenshots/${shotName}-stranger-login.png`] : [],
      });
      return;
    }

    if (!provisioning.ok) {
      // Honest failure: a credential-free required cell may never be
      // not_runnable, so the lane's missing capability is recorded as a fail.
      ledger.record({ variantId: `role=${role}`, result: "fail", detail: provisioning.error });
      return;
    }

    const account = provisioning.accounts[role];
    await page.locator("#login-username").fill(account.username);
    await page.locator("#login-password").fill(account.password);
    await shot(`${role}-credentials`);
    await page.locator('form button[type="submit"]').first().click();
    await page.waitForTimeout(2500);

    let shell = await waitForMarker(page, page.locator('nav[aria-label="Views"]').first());
    if (!shell) {
      // Login rate limiting windows at 60s: wait once and retry the form
      // submission before recording a failure.
      const rateLimited = await page
        .locator("text=Too many login attempts")
        .first()
        .isVisible()
        .catch(() => false);
      if (rateLimited) {
        await page.waitForTimeout(61000);
        await page.locator("#login-password").fill(account.password);
        await page.locator('form button[type="submit"]').first().click();
        await page.waitForTimeout(2500);
        shell = await waitForMarker(page, page.locator('nav[aria-label="Views"]').first());
      }
    }
    if (!shell) {
      await shot(`${role}-login-failed`);
      ledger.record({
        variantId: `role=${role}`,
        result: "fail",
        detail: `form login for ${account.username} never reached the authenticated shell`,
        artifacts: shotName ? [`screenshots/${shotName}-${role}-login-failed.png`] : [],
      });
      return;
    }
    await shot(`${role}-shell`);

    const outcome = (await drive(page, { shot })) || { ok: true, detail: "shell reached" };
    ledger.record({
      variantId: `role=${role}`,
      result: outcome.ok ? "pass" : "fail",
      detail: outcome.detail || "driven",
      artifacts: shotName ? [`screenshots/${shotName}-${role}*.png`] : [],
    });
  } catch (error) {
    ledger.record({ variantId: `role=${role}`, result: "fail", detail: `role cell error: ${error.message}` });
  } finally {
    await context.close().catch(() => {});
  }
}
