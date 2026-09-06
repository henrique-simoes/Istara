import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { ChannelProtocolSimulator } from "./lib/channel-protocol-simulator.mjs";

async function main() {
  const token = process.env.TOK || process.env.ISTARA_TEST_AUTH_TOKEN;
  if (!token) {
    console.error("Missing TOK env var");
    process.exit(1);
  }

  const outDir = "/work/tests/simulation/.results/screenshots_channels";
  mkdirSync(outDir, { recursive: true });

  const BACKEND_URL = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONTEND_URL = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  // 1. Start Protocol Simulator
  const simulator = new ChannelProtocolSimulator({ port: 18080 });
  const simulatorUrl = await simulator.start();
  console.log(`Simulator listening at ${simulatorUrl}`);

  // 2. Resolve or create dedicated simulation project (protects live production runs)
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  let PROJECT_ID = process.env.SIMULATION_PROJECT_ID;
  if (!PROJECT_ID) {
    try {
      const listRes = await fetch(`${BACKEND_URL}/api/projects`, { headers });
      if (listRes.ok) {
        const projs = await listRes.json();
        const simProj = projs.find((p) => p.name === "[SIM] Automated Evaluation Project" || p.name === "[SIM] Integrations & Surveys UI Evaluation");
        if (simProj) {
          PROJECT_ID = simProj.id;
        }
      }
    } catch {}
  }
  if (!PROJECT_ID) {
    try {
      const createRes = await fetch(`${BACKEND_URL}/api/projects`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          name: "[SIM] Integrations & Surveys UI Evaluation",
          description: "Simulation project for channels & surveys visual inspection.",
          company_context: "TechStart Inc — evaluation project.",
        }),
      });
      if (createRes.ok) {
        const data = await createRes.json();
        PROJECT_ID = data.id;
      }
    } catch {}
  }
  console.log(`Using simulation project for UI capture: ${PROJECT_ID}`);

  let tgId = null;
  let smId = null;
  let depId = null;

  try {
    // Create Telegram Channel
    const tgRes = await fetch(`${BACKEND_URL}/api/channels`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        platform: "telegram",
        name: "Research Telegram Bot",
        config: {
          bot_token: "123456789:SIM_TOKEN",
          base_url: `${simulatorUrl}/bot`,
        },
        project_id: PROJECT_ID,
      }),
    });
    if (tgRes.ok) {
      const tgData = await tgRes.json();
      tgId = tgData.id;
      await fetch(`${BACKEND_URL}/api/channels/${tgId}/start?project_id=${PROJECT_ID}`, {
        method: "POST",
        headers,
      });
      console.log("Created & started Telegram channel:", tgId);
    }

    // Create SurveyMonkey Integration
    const smRes = await fetch(`${BACKEND_URL}/api/surveys/integrations`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        platform: "surveymonkey",
        name: "Customer Feedback 2026",
        config: {
          access_token: "sm_token_live_ui",
          base_url: simulatorUrl,
        },
        project_id: PROJECT_ID,
      }),
    });
    if (smRes.ok) {
      const smData = await smRes.json();
      smId = smData.id;
      console.log("Created SurveyMonkey integration:", smId);
    }

    // Create Deployment
    if (tgId) {
      const depRes = await fetch(`${BACKEND_URL}/api/deployments`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          project_id: PROJECT_ID,
          name: "Q1 Usability Pulse Interview",
          deployment_type: "interview",
          questions: [
            { text: "What workflow step causes the most frustration?" },
            { text: "How can Istara simplify insight synthesis?" },
          ],
          channel_instance_ids: [tgId],
          config: {
            adaptive: true,
            max_followups: 2,
            research_goals: "Understand synthesis bottlenecks",
          },
          target_responses: 10,
        }),
      });
      if (depRes.ok) {
        const depData = await depRes.json();
        depId = depData.id;
        await fetch(`${BACKEND_URL}/api/deployments/${depId}/activate?project_id=${PROJECT_ID}`, {
          method: "POST",
          headers,
        });
        console.log("Created & activated deployment:", depId);
      }
    }

    // 3. Launch Playwright
    const browser = await chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-gpu"],
    });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    console.log("Navigating to frontend...");
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.evaluate(
      ({ tok, pId }) => {
        localStorage.clear();
        localStorage.setItem("istara_token", tok);
        localStorage.setItem("istara_auth_user_id", "simulation-admin");
        localStorage.setItem("istara_tour_completed_simulation-admin", "true");
        localStorage.setItem("istara_tour_completed_admin", "true");
        localStorage.setItem("istara_tour_completed_anonymous", "true");
        localStorage.setItem(
          "istara_tour_state",
          JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true })
        );
        localStorage.setItem("istara-active-project", pId);
        localStorage.setItem("istara_active_view", "integrations");
      },
      { tok: token, pId: PROJECT_ID }
    );

    const themes = ["dark", "light"];

    for (const theme of themes) {
      console.log(`\nCapturing theme: ${theme}`);
      await page.evaluate((th) => {
        localStorage.setItem("istara-theme", th);
        if (th === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }, theme);

      await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      // Helper to click tab
      const switchTab = async (name) => {
        await page.evaluate((tabName) => {
          const btns = Array.from(document.querySelectorAll("div.border-b button"));
          const btn = btns.find((b) => b.textContent?.trim().includes(tabName));
          if (btn) btn.click();
        }, name);
        await page.waitForTimeout(1500);
      };

      // Tab 1: Overview
      await switchTab("Overview");
      await page.screenshot({ path: `${outDir}/integrations_overview_${theme}.png` });
      console.log(`  ✅ Captured integrations_overview_${theme}.png`);

      // Tab 2: Messaging
      await switchTab("Messaging");
      // Click channel card to open detail panel
      const cardTitle = page.locator('h3:has-text("Research Telegram Bot")').first();
      if (await cardTitle.isVisible().catch(() => false)) {
        await cardTitle.click();
        await page.waitForTimeout(1500);
      }
      await page.screenshot({ path: `${outDir}/integrations_messaging_${theme}.png` });
      console.log(`  ✅ Captured integrations_messaging_${theme}.png`);

      // Tab 3: Surveys
      await switchTab("Surveys");
      await page.screenshot({ path: `${outDir}/integrations_surveys_${theme}.png` });
      console.log(`  ✅ Captured integrations_surveys_${theme}.png`);

      // Tab 4: Deployments
      await switchTab("Deployments");
      await page.screenshot({ path: `${outDir}/integrations_deployments_${theme}.png` });
      console.log(`  ✅ Captured integrations_deployments_${theme}.png`);
    }

    await browser.close();
    console.log("All screenshots captured successfully!");
  } finally {
    await simulator.stop();
    // Clean up created resources
    if (depId) {
      await fetch(`${BACKEND_URL}/api/deployments/${depId}?project_id=${PROJECT_ID}`, { method: "DELETE", headers }).catch(() => {});
    }
    if (smId) {
      await fetch(`${BACKEND_URL}/api/surveys/integrations/${smId}?project_id=${PROJECT_ID}`, { method: "DELETE", headers }).catch(() => {});
    }
    if (tgId) {
      await fetch(`${BACKEND_URL}/api/channels/${tgId}?project_id=${PROJECT_ID}`, { method: "DELETE", headers }).catch(() => {});
    }
  }
}

main().catch(console.error);
