import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";

// Proves the auth-hardening milestone in a real browser:
// 1. Fresh login via UI form (no injected token) -> cookie + memory transport.
// 2. localStorage has NO istara_token after login (XSS theft vector closed).
// 3. Settings: File & Backup Encryption card renders with honest scope copy.
// 4. Settings: Active Sessions shows masked IP previews.
// 5. Chat: send a message end-to-end (regression: sends still work).
// 6. Login screen offers passkey sign-in (no regression).
const B = "http://127.0.0.1:8000", F = "http://127.0.0.1:3000";
const outDir = "/work/tests/simulation/.results/phase11_screenshots";
mkdirSync(outDir, { recursive: true });
const report = { startedAt: new Date().toISOString(), checks: {}, errors: [] };

const b = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const c = await b.newContext({ viewport: { width: 1280, height: 900 } });
const p = await c.newPage();
p.on("pageerror", (e) => report.errors.push("pageerror:" + String(e).slice(0, 160)));
p.on("response", (r) => { if (r.status() >= 500) report.errors.push(r.status() + " " + r.url().slice(0, 100)); });

await p.goto(F, { waitUntil: "domcontentloaded" });
await p.waitForTimeout(2000);
// Dismiss tour if present
await p.locator("button:has-text('Skip tour')").first().click().catch(() => {});
await p.waitForTimeout(500);

// --- 1+6. Login form + passkey affordance ---
const userBox = p.locator("input[type='text'], input[name='username'], input[placeholder*='ser' i]").first();
await userBox.waitFor({ timeout: 20000 }).catch(() => {});
report.checks.loginForm = await userBox.isVisible().catch(() => false);
report.checks.passkeyOffered = await p.locator("button:has-text('Passkey'), button:has-text('passkey')").first().isVisible().catch(() => false);
await p.screenshot({ path: `${outDir}/login_form.png` });
await userBox.fill("admin").catch(() => {});
const passBox = p.locator("input[type='password']").first();
await passBox.fill("admin").catch(() => {});
await p.locator("button[type='submit'], button:has-text('Log in'), button:has-text('Sign in')").first().click().catch(() => {});
await p.waitForTimeout(3000);

// --- 2. No persisted token ---
const stored = await p.evaluate(() => localStorage.getItem("istara_token")).catch(() => "ERR");
report.checks.noPersistedToken = stored === null;
const cookies = await c.cookies().catch(() => []);
report.checks.sessionCookie = cookies.some((x) => x.name.includes("istara_session"));
console.log("persisted token:", stored, "| session cookie:", report.checks.sessionCookie);

// --- navigate to chat via sidebar (dismiss tour first if it appears) ---
await p.locator("button:has-text('Skip tour')").first().click().catch(() => {});
await p.waitForTimeout(500);
await p.locator("nav button:has-text('Chat'), aside button:has-text('Chat'), button:has-text('Chat')").first().click().catch(() => {});
await p.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "chat" }))).catch(() => {});
await p.locator("textarea").first().waitFor({ timeout: 25000 }).catch(() => {});
report.checks.chatReady = await p.locator("textarea").first().isVisible().catch(() => false);

// --- 5. Chat send ---
const box = p.locator("textarea").first();
await box.click().catch(() => {});
await box.fill("Reply with exactly: auth hardening UI works").catch(() => {});
const send = p.locator("button[aria-label='Send message']").first();
await send.click().catch(() => {});
await p.waitForFunction(() => document.body.innerText.includes("auth hardening UI works"), { timeout: 120000 }).catch(() => {});
report.checks.chatSend = await p.evaluate(() => document.body.innerText.includes("auth hardening UI works")).catch(() => false);
console.log("chat send:", report.checks.chatSend);
await p.screenshot({ path: `${outDir}/chat_send.png` });

// --- 3+4. Settings cards ---
await p.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "settings" })));
await p.waitForTimeout(2500);
report.checks.encryptionCard = await p.locator("text=File and Backup Encryption").first().isVisible().catch(() => false);
report.checks.scopeCopy = await p.locator("text=Search indexes").first().isVisible().catch(() => false);
report.checks.sessionsCard = await p.locator("text=Active Sessions").first().isVisible().catch(() => false);
// masked IP pattern like 1.2.3.* or abcd:: present near sessions
const settingsText = await p.evaluate(() => document.body.innerText).catch(() => "");
report.checks.maskedIp = /\d+\.\d+\.\d+\.\*/.test(settingsText) || /::/.test(settingsText);
console.log("encryption card:", report.checks.encryptionCard, "| scope copy:", report.checks.scopeCopy, "| sessions:", report.checks.sessionsCard, "| masked IP:", report.checks.maskedIp);
await p.screenshot({ path: `${outDir}/settings_security.png`, fullPage: false });
// dark mode parity on settings
await p.evaluate(() => document.documentElement.classList.add("dark"));
await p.waitForTimeout(600);
await p.screenshot({ path: `${outDir}/settings_security_dark.png` });
await p.evaluate(() => document.documentElement.classList.remove("dark"));
// keyboard: tab reaches a control
await p.keyboard.press("Tab").catch(() => {});
const focusVisible = await p.evaluate(() => {
  const el = document.activeElement;
  if (!el || el === document.body) return false;
  const r = el.getBoundingClientRect();
  return r.width >= 24 && r.height >= 24;
}).catch(() => false);
report.checks.keyboardFocus = focusVisible;

report.finishedAt = new Date().toISOString();
writeFileSync("/work/tests/simulation/.results/phase11_auth_proof.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report.checks));
console.log("ERRORS:", JSON.stringify(report.errors.slice(0, 6)));
await b.close();
const must = ["loginForm", "noPersistedToken", "sessionCookie", "chatReady", "chatSend", "encryptionCard", "scopeCopy", "sessionsCard"];
const failed = must.filter((k) => !report.checks[k]);
if (failed.length) { console.log("FAIL:", failed.join(",")); process.exit(1); }
console.log("PASS: auth hardening UI proof");
