/** Scenario 19 — File Preview: test file content API, preview, and serving endpoints. */

export const name = "File Preview & Content";
export const id = "19-file-preview";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // 1. Upload a test text file
  let testFilename = null;
  try {
    const testContent = `Interview Transcript — Participant P010
Date: 2024-02-10

[00:00:15] Interviewer: Tell me about your experience with the onboarding process.

[00:00:30] P010: The onboarding was mostly smooth. I liked the guided setup but felt overwhelmed by all the options on the dashboard afterwards.

[00:01:15] Interviewer: What specifically felt overwhelming?

[00:01:25] P010: There were too many buttons and I didn't know where to start. I think a "start here" guide or tutorial would help new users like me.

[00:02:00] Interviewer: What features did you use most?

[00:02:10] P010: Definitely the search. I search for everything. The file upload was straightforward too.
`;
    const blob = new Blob([testContent], { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", blob, "sim-preview-test.txt");
    const res = await fetch(`http://localhost:8000/api/files/upload/${ctx.projectId}`, {
      method: "POST",
      body: formData,
    });
    const result = await res.json();
    testFilename = result.saved_as;
    checks.push({
      name: "Upload test file",
      passed: res.ok && !!testFilename,
      detail: `filename=${testFilename}`,
    });
  } catch (e) {
    checks.push({ name: "Upload test file", passed: false, detail: e.message });
  }

  // 2. Get file content via API
  if (testFilename) {
    try {
      const content = await api.get(`/api/files/${ctx.projectId}/content/${testFilename}`);
      const hasContent = typeof content.content === "string" && content.content.length > 100;
      checks.push({
        name: "Get file content API",
        passed: hasContent,
        detail: `type=${content.type}, size=${content.size}`,
      });

      // Check content contains expected text
      if (hasContent) {
        const hasExpected = content.content.includes("onboarding") && content.content.includes("P010");
        checks.push({
          name: "Content matches uploaded text",
          passed: hasExpected,
          detail: `contains onboarding=${content.content.includes("onboarding")}`,
        });
      }
    } catch (e) {
      checks.push({ name: "Get file content API", passed: false, detail: e.message });
    }
  }

  // 3. Serve file directly
  if (testFilename) {
    try {
      const res = await fetch(`http://localhost:8000/api/files/${ctx.projectId}/serve/${testFilename}`);
      checks.push({
        name: "Serve file endpoint",
        passed: res.ok,
        detail: `status=${res.status}, content-type=${res.headers.get("content-type")}`,
      });
    } catch (e) {
      checks.push({ name: "Serve file endpoint", passed: false, detail: e.message });
    }
  }

  // 4. List files includes the uploaded file
  try {
    const files = await api.get(`/api/files/${ctx.projectId}`);
    const fileList = files.files || [];
    const found = fileList.some((f) => f.name === testFilename);
    checks.push({
      name: "File appears in list",
      passed: found,
      detail: `${fileList.length} files, found=${found}`,
    });
  } catch (e) {
    checks.push({ name: "File appears in list", passed: false, detail: e.message });
  }

  // 5. UI — navigate to Interviews and check file appears
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Select project
  const projectBtn = page.locator("text=[SIM]").first();
  if (await projectBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectBtn.click();
    await page.waitForTimeout(500);
  }

  // Navigate to Interviews (Cmd+4)
  await page.keyboard.press("Meta+4");
  await page.waitForTimeout(2000);

  const interviewsVisible = await page.locator("text=Interviews").first().isVisible({ timeout: 3000 }).catch(() => false);
  checks.push({
    name: "Interviews view loads",
    passed: interviewsVisible,
    detail: "",
  });

  await screenshot("19-file-preview");

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
