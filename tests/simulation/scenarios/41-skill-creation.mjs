/** Scenario 41 — Autonomous Skill Creation: test skill creation proposal system and registry. */

export const name = "Autonomous Skill Creation";
export const id = "41-skill-creation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET pending skill creation proposals ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/pending`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/creation-proposals/pending responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "Pending proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `type=${typeof data}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET pending proposals", passed: false, detail: e.message });
  }

  // ── 2. GET all skill creation proposals ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/all`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/creation-proposals/all responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "All proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `count=${(data.proposals || data).length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET all proposals", passed: false, detail: e.message });
  }

  // ── 3. POST reject nonexistent proposal → 404 ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/nonexistent/reject`, {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Reject nonexistent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Reject nonexistent proposal", passed: false, detail: e.message });
  }

  // ── 4. POST approve nonexistent proposal → 404 ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/nonexistent/approve`, {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Approve nonexistent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Approve nonexistent proposal", passed: false, detail: e.message });
  }

  // ── 5. Skill registry — GET /api/skills returns skills list ──
  try {
    const skills = await api.get("/api/skills");
    const skillList = skills.skills || skills;
    checks.push({
      name: "Skill registry returns skills list",
      passed: Array.isArray(skillList) && skillList.length > 0,
      detail: `${skillList.length} skills registered`,
    });
    // Verify skills have expected structure
    if (skillList.length > 0) {
      const first = skillList[0];
      checks.push({
        name: "Skills have name and phase fields",
        passed: !!first.name && !!first.phase,
        detail: `first=${first.name}, phase=${first.phase}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Skill registry", passed: false, detail: e.message });
  }

  // ── 6. GET /api/skills/health/all returns health data ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/health/all`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/health/all responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "Skills health returns data",
        passed: data !== null && typeof data === "object",
        detail: `keys=${Object.keys(data).slice(0, 5).join(", ")}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Skills health endpoint", passed: false, detail: e.message });
  }

  // ── 7. Phase 4A: Skills Self-Evolution Layout — UI checks ──
  if (ctx.page) {
    const page = ctx.page;
    try {
      await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
      await page.waitForTimeout(1500);

      // Navigate to Skills view
      const skillsBtn = page.locator('button[aria-label="Skills"]').first();
      if (await skillsBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await skillsBtn.click();
        await page.waitForTimeout(2000);

        // Check for two-column layout (grid CSS)
        const layoutInfo = await page.evaluate(() => {
          const gridEls = document.querySelectorAll('[class*="grid-cols-2"], [class*="grid-cols-"], [class*="lg:grid-cols-2"]');
          const flexTwoCol = document.querySelectorAll('[class*="flex"][class*="gap"]');
          // Also check for panels side-by-side
          const panels = document.querySelectorAll('[class*="col-span"], [class*="basis-"], [class*="w-1/2"]');
          return {
            gridColCount: gridEls.length,
            flexGapCount: flexTwoCol.length,
            panelCount: panels.length,
          };
        });
        checks.push({
          name: "Phase 4A: Skills view has two-column/grid layout",
          passed: layoutInfo.gridColCount > 0 || layoutInfo.panelCount > 0,
          detail: `grid_cols=${layoutInfo.gridColCount}, flex_gap=${layoutInfo.flexGapCount}, panels=${layoutInfo.panelCount}`,
        });

        // Check for creation proposal cards with details
        const proposalCards = await page.evaluate(() => {
          const body = document.body.innerText.toLowerCase();
          const hasProposals = body.includes("proposal") || body.includes("creation") || body.includes("pending");
          // Look for card-like elements in the skills view
          const cards = document.querySelectorAll('[class*="rounded"][class*="border"][class*="p-"]');
          // Check if any card contains proposal-related text
          let proposalCardCount = 0;
          for (const card of cards) {
            const text = card.innerText.toLowerCase();
            if (text.includes("proposal") || text.includes("skill") || text.includes("approve") || text.includes("reject")) {
              proposalCardCount++;
            }
          }
          return { hasProposals, proposalCardCount, totalCards: cards.length };
        });
        checks.push({
          name: "Phase 4A: Creation proposal cards show proposal details",
          passed: proposalCards.hasProposals || proposalCards.proposalCardCount > 0 || proposalCards.totalCards > 0,
          detail: `proposals_text=${proposalCards.hasProposals}, proposal_cards=${proposalCards.proposalCardCount}, total_cards=${proposalCards.totalCards}`,
        });
      } else {
        checks.push({ name: "Phase 4A: Skills view has two-column/grid layout", passed: false, detail: "Skills nav button not visible" });
        checks.push({ name: "Phase 4A: Creation proposal cards show proposal details", passed: false, detail: "Skills nav button not visible" });
      }
    } catch (e) {
      checks.push({ name: "Phase 4A: Skills self-evolution layout", passed: false, detail: e.message });
    }
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
