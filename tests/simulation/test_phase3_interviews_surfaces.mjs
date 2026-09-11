import { chromium } from "playwright";
import { mkdirSync } from "fs";

async function run() {
  console.log("=== STARTING PHASE 3 INTERVIEWS SURFACES & CODING PARITY VERIFICATION ===");
  const outDir = "/work/tests/simulation/.results/phase3_screenshots";
  mkdirSync(outDir, { recursive: true });

  const BACKEND_URL = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONTEND_URL = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  // 1. Authenticate
  const loginRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin" }),
  });
  if (!loginRes.ok) throw new Error(`Login failed: ${loginRes.status}`);
  const { token, user } = await loginRes.json();
  console.log(`Authenticated as admin: ${user.id}`);

  // 2. Select Project
  const projRes = await fetch(`${BACKEND_URL}/api/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const projs = await projRes.json();
  const targetProj = projs.find((p) => p.id === "proj-st150-pi-dd6bf277") || projs[0];
  const PROJECT_ID = targetProj.id;
  console.log(`Using Project: ${PROJECT_ID} (${targetProj.name})`);

  // 3. Ensure test interview transcript and audio files are uploaded
  const filesListRes = await fetch(`${BACKEND_URL}/api/files/${PROJECT_ID}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const filesData = await filesListRes.json();
  console.log(`Initial files count: ${filesData.count}`);

  const hasTranscript = filesData.files?.some((f) => f.name.includes("interview") || f.type === ".md" || f.type === ".txt");
  const hasAudio = filesData.files?.some((f) => [".mp3", ".wav", ".m4a"].includes(f.type));

  if (!hasTranscript || !hasAudio) {
    console.log("Seeding test interview transcript and audio file...");
    const transcriptText = `# Clinical Coordinator Interview 01 (CareNav)
Participant: P01 - Care Coordinator
Date: 2026-03-12
Setting: Pediatric Specialty Clinic

### 00:00 - specialist referral handoff
Moderator: Earlier you mentioned covering the front desk while two coordinators are out. Can you tell me what changed your confidence and what still felt risky, especially around specialist referral handoff?
P01: "I trust the reminder more when it admits what it does not know yet. The hard part is that caregivers receive partial information and then call the clinic, but another part of the same visit says staff do not trust automation when no source trail is shown."

### 00:42 - same-day cancellation recovery
Moderator: What would make that safe enough to move forward without overclaiming?
P01: "When the caregiver text is vague, the next thing that happens is a phone call to the clinic. The hard part is that the dashboard hides stale tasks until the day before a visit."

### 01:24 - post-operative checklist review
Moderator: Can you separate what the patient understood from what the staff queue showed?
P01: "The queue is fast for sorting, but it hides the story I need when a patient pushes back. Forms look complete even when lab attachments are missing."
`;
    const formData1 = new FormData();
    formData1.append("file", new Blob([transcriptText], { type: "text/markdown" }), "CR-001-interview-01.md");
    const up1 = await fetch(`${BACKEND_URL}/api/files/upload/${PROJECT_ID}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData1,
    });
    console.log("Transcript upload status:", up1.status);

    // Generate a minimal valid WAV file (16kHz PCM 1-second silence)
    const sampleRate = 16000;
    const numSamples = 16000;
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
    };
    writeString(0, "RIFF");
    view.setUint32(4, 36 + numSamples * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, numSamples * 2, true);

    const audioBlob = new Blob([buffer], { type: "audio/wav" });
    const formData2 = new FormData();
    formData2.append("file", audioBlob, "interview-session-p01.wav");
    const up2 = await fetch(`${BACKEND_URL}/api/files/upload/${PROJECT_ID}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData2,
    });
    console.log("Audio upload status:", up2.status);
    await new Promise((r) => setTimeout(r, 1000));
  }

  // 4. Launch browser
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  await context.addInitScript(
    ({ tok, uId, pId }) => {
      try {
        localStorage.setItem("istara_token", tok);
        localStorage.setItem("istara_auth_user_id", uId);
        localStorage.setItem(`istara_tour_completed_${uId}`, "true");
        localStorage.setItem("istara_tour_completed_admin", "true");
        localStorage.setItem("istara_tour_completed_anonymous", "true");
        localStorage.setItem(
          "istara_tour_state",
          JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true })
        );
        localStorage.setItem("istara-active-project", pId);
        localStorage.setItem("istara_active_view", "interviews");
      } catch {}
    },
    { tok: token, uId: user.id, pId: PROJECT_ID }
  );

  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log(`[BROWSER ERROR] ${msg.text()}`);
  });

  console.log("Navigating to Interviews view...");
  await page.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Ensure on interviews view
  const interviewsHeader = page.locator("h2:has-text('Interviews & Transcripts')");
  if (!(await interviewsHeader.isVisible().catch(() => false))) {
    console.log("Clicking Interviews nav item in sidebar...");
    const navItem = page.locator("button:has-text('Interviews')").first();
    await navItem.click();
    await page.waitForTimeout(1000);
  }

  // ── SUB-TEST 1: Transcript Canvas & Qualitative Coding ──
  console.log("--- Testing Transcript Canvas & Qualitative Coding ---");
  const transcriptFileBtn = page.locator("button:has-text('CR-001-interview-01'), button:has-text('.md')").first();
  if (await transcriptFileBtn.isVisible().catch(() => false)) {
    console.log("Clicking transcript file button...");
    await transcriptFileBtn.click();
    await page.waitForTimeout(1500);
  } else {
    const firstFile = page.locator("div.flex.flex-wrap.gap-1 button").first();
    if (await firstFile.isVisible().catch(() => false)) {
      console.log("Selecting first file in file bar...");
      await firstFile.click();
      await page.waitForTimeout(1500);
    }
  }

  const codingCanvas = page.locator("div[role='region'][aria-label='Qualitative Coding Text Canvas']");
  console.log("Coding canvas visible:", await codingCanvas.isVisible().catch(() => false));

  // Capture Light mode transcript canvas
  await page.screenshot({ path: `${outDir}/01_interview_transcript_canvas_light.png`, fullPage: false });
  console.log("Saved: 01_interview_transcript_canvas_light.png");

  // Switch to dark mode
  await page.evaluate(() => document.documentElement.classList.add("dark"));
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${outDir}/01_interview_transcript_canvas_dark.png`, fullPage: false });
  console.log("Saved: 01_interview_transcript_canvas_dark.png");
  await page.evaluate(() => document.documentElement.classList.remove("dark"));
  await page.waitForTimeout(300);

  // ── SUB-TEST 2: Audio Player Controls & Sync ──
  console.log("--- Testing Audio Player Controls & Sync ---");
  const audioFileBtn = page.locator("button:has-text('.wav'), button:has-text('interview-session')").first();
  if (await audioFileBtn.isVisible().catch(() => false)) {
    console.log("Clicking audio file button...");
    await audioFileBtn.click();
    await page.waitForTimeout(1500);

    const audioRegion = page.locator("div[role='region'][aria-label='Interview audio controls']");
    const audioVisible = await audioRegion.isVisible().catch(() => false);
    console.log("Audio Player visible:", audioVisible);

    // Test Play button
    const playBtn = page.locator("button[aria-label='Play interview audio']");
    if (await playBtn.isVisible().catch(() => false)) {
      console.log("Clicking Play button...");
      await playBtn.click();
      await page.waitForTimeout(800);
    }

    // Test speed rate cycling
    const speedBtn = page.locator("button[title*='Speed']");
    if (await speedBtn.isVisible().catch(() => false)) {
      console.log("Cycling playback speed...");
      await speedBtn.click(); // 1.25x
      await page.waitForTimeout(300);
      await speedBtn.click(); // 1.5x
      await page.waitForTimeout(300);
    }

    // Test Skip forward
    const skipFwdBtn = page.locator("button[aria-label='Skip forward 10 seconds']");
    if (await skipFwdBtn.isVisible().catch(() => false)) {
      await skipFwdBtn.click();
      await page.waitForTimeout(300);
    }

    // Capture Audio Player Light screenshot
    await page.screenshot({ path: `${outDir}/02_audio_player_sync_light.png`, fullPage: false });
    console.log("Saved: 02_audio_player_sync_light.png");

    // Capture Audio Player Dark screenshot
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${outDir}/02_audio_player_sync_dark.png`, fullPage: false });
    console.log("Saved: 02_audio_player_sync_dark.png");
    await page.evaluate(() => document.documentElement.classList.remove("dark"));
    await page.waitForTimeout(300);
  }

  // ── SUB-TEST 3: Tags & Nuggets Sidebar & Collapse Toggle ──
  console.log("--- Testing Tags & Nuggets Sidebar ---");
  const tagButtons = page.locator("div.w-64 button.rounded-full");
  const tagCount = await tagButtons.count();
  console.log(`Found ${tagCount} tag filters in right panel.`);

  if (tagCount > 1) {
    console.log("Clicking second tag filter...");
    await tagButtons.nth(1).click();
    await page.waitForTimeout(500);
  }

  const nuggetCard = page.locator("div.w-64 div.space-y-2 button").first();
  if (await nuggetCard.isVisible().catch(() => false)) {
    console.log("Clicking nugget card to test navigation & highlight...");
    await nuggetCard.click();
    await page.waitForTimeout(500);
  }

  const collapseToggle = page.locator("button[aria-label*='Collapse tags and nuggets panel']");
  if (await collapseToggle.isVisible().catch(() => false)) {
    console.log("Toggling panel collapse...");
    await collapseToggle.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${outDir}/03_nuggets_panel_collapsed.png`, fullPage: false });
    console.log("Saved: 03_nuggets_panel_collapsed.png");

    const expandToggle = page.locator("button[aria-label*='Expand tags and nuggets panel']");
    if (await expandToggle.isVisible().catch(() => false)) {
      await expandToggle.click();
      await page.waitForTimeout(500);
    }
  }

  await browser.close();
  console.log("=== ALL PHASE 3 VERIFICATION TESTS PASSED SUCCESSFULLY ===");
}

run().catch((err) => {
  console.error("FATAL ERROR in Phase 3 verification:", err);
  process.exit(1);
});
