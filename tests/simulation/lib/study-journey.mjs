/**
 * Helpers for scenario 89 (a research study through messaging channels): the synthetic participant
 * script, a waiting visibility check, and a small RFC 4180 CSV reader for the export.
 */

/** Messages each synthetic participant sends (sender, channel, texts). */
export const PARTICIPANT_SCRIPT = [
  ["p1", "telegram", ["hi", "yes", "yes", "We email PDFs around", "Big exports time out", "No, that's all"]],
  ["p2", "slack", ["hello", "no", "actually exports are slow"]],
  ["p3", "whatsapp", ["hi", "yes", "no"]],
  ["p4", "slack", ["hi", "yes", "yes", "Shared drive", "STOP", "one more thing"]],
  ["p5", "whatsapp", ["hey", "sure", "Yes", "Screenshots in chat", "Finding the latest version", "Nothing else"]],
  ["p6", "telegram", ["hi there", "yes"]],
];

/** Texts that are never research answers: greetings, consent and screener replies, post-STOP. */
export const NOT_ANSWERS = ["hi", "hello", "yes", "no", "STOP", "sure", "hey", "one more thing", "actually exports are slow"];

/** Playwright's isVisible() does not wait; this does. */
export async function shows(locator, timeout = 8000) {
  return locator.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
}

export function parseCsv(text) {
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

