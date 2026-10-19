/** Scenario 94 — Coding run with decision-model triage and a simulated researcher (CF-SPEC-1).
 *
 * A short interview with four planted themes is uploaded; the project's research models code it
 * in a governed coding run; the project's decision model triages every code application; then a
 * simulated researcher reviews each application through the real review route (the same call as
 * the review queue's approve/reject), approving codes that match the line's planted theme. That
 * labels the decider's verdicts, which is what calibration and trust are built on.
 *
 * Live only (ISTARA_SIM_DECIDER_ENDPOINTS, three research endpoints). Small on purpose: it proves
 * the pipeline, not the trust threshold (50 labelled verdicts per scope). */

import { getApiBase } from "../lib/api-client.mjs";

export const name = "Coding Run Triage";
export const id = "94-coding-run-triage";

const MARKER = "sim94";
const LINES = [
  ["pricing", "The price went up twice this year and the per-seat cost is now hard to justify."],
  ["onboarding", "Setting up the first project took a whole afternoon; the onboarding never told me what to do next."],
  ["performance", "Every board takes five or six seconds to load, so the team stopped opening it in meetings."],
  ["support", "When the import broke, support answered after three days and only sent a help article."],
  ["pricing", "We compared plans and the cheaper competitor covers what we need for half the cost."],
  ["onboarding", "New hires still ask me how to invite people because the setup steps are buried."],
  ["performance", "Search is slow on big projects; sometimes it times out before showing anything."],
  ["support", "The chat support was friendly but nobody could fix the billing sync."],
  ["none", "I would love a dark mode and a calendar view for the boards."],
  ["none", "Our team mostly works remotely across three time zones."],
];
// The project codebook (Research Spine: deductive coding against governed definitions).
const CODEBOOK = [
  ["pricing-value", "Pricing and value", "The participant judges price, cost or plan value against what they get.", "Mentions of price, cost, plans or billing as a value judgement.", "Billing sync bugs (that is a support or product failure)."],
  ["onboarding-friction", "Onboarding friction", "Getting started or bringing others in takes effort or guidance is missing.", "Setup, first project, invitations, unclear next steps.", "Ongoing slowness after setup."],
  ["performance-latency", "Performance and latency", "The product is slow, times out or makes people avoid it.", "Load times, search speed, timeouts.", "Slow human replies from support."],
  ["support-quality", "Support quality", "Help from the vendor is slow, generic or does not fix the problem.", "Response time, canned answers, unresolved tickets.", "Self-serve setup confusion."],
];
const THEME_CODE = { pricing: "pricing-value", onboarding: "onboarding-friction", performance: "performance-latency", support: "support-quality" };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function themeOf(text) {
  const found = LINES.find(([, line]) => text.includes(line.slice(0, 40)));
  return found ? found[0] : null;
}

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const check = (name, passed, detail = "") => checks.push({ name, passed: Boolean(passed), detail });
  const finish = (summary) => {
    const passed = checks.filter((c) => c.passed).length;
    return { checks, passed, failed: checks.length - passed, summary };
  };
  const decider = String(process.env.ISTARA_SIM_DECIDER_ENDPOINTS || "").split(",")[0].trim();
  const projectId = ctx.projectId;
  if (!decider || !projectId) {
    check("Live decider configured", false, "not_runnable: set ISTARA_SIM_DECIDER_ENDPOINTS on a live stack");
    return finish("not runnable");
  }

  // 1. Upload the interview; its evidence units are the coding input.
  const transcript =
    `Interview ${MARKER}: project-management tool, mid-market team lead.\n\n` +
    LINES.map(([, line], i) => `Participant (${i + 1}): ${line}`).join("\n\n");
  let docId = null;
  try {
    const form = new FormData();
    form.append("file", new Blob([transcript], { type: "text/plain" }), `${MARKER}-interview.txt`);
    const headers = { ...api._headers() };
    delete headers["Content-Type"];
    const response = await fetch(`${getApiBase()}/api/files/upload/${projectId}`, { method: "POST", headers, body: form });
    if (!response.ok) throw new Error(`upload ${response.status}`);
    const uploaded = await response.json();
    docId = uploaded.doc_id;
    check("Interview uploaded", Boolean(docId), `doc=${docId} chunks=${uploaded.chunks_indexed}`);
  } catch (e) {
    check("Interview uploaded", false, e.message);
    return finish("upload failed");
  }
  // The project may already hold many units; page through all of them for this document's.
  let units = [];
  for (let attempt = 0; attempt < 10 && units.length === 0; attempt += 1) {
    for (let offset = 0; ; offset += 500) {
      const page = await api
        .get(`/api/research-validity/${projectId}/evidence-units?limit=500&offset=${offset}`)
        .catch(() => []);
      units.push(...(page || []).filter((unit) => unit.source_document_id === docId));
      if (!page || page.length < 500) break;
    }
    if (!units.length) await sleep(3000);
  }
  check("Evidence units created from the interview", units.length > 0, `${units.length} unit(s)`);
  if (!units.length) return finish("no evidence units");

  // 2. Codebook version for the project, then a governed coding run that applies it.
  // One fixed codebook version, reused across runs: trust is earned per codebook version (DEC-22).
  const CODEBOOK_VERSION = `${MARKER}-v1`;
  let codebookVersionId = null;
  try {
    const versions = await api.get(`/api/codebook-versions/${projectId}`).catch(() => []);
    const list = Array.isArray(versions) ? versions : versions.versions || [];
    const existing = list.find((item) => item.version === CODEBOOK_VERSION);
    const version =
      existing ||
      (await api.post("/api/codebook-versions", {
        project_id: projectId,
        version: CODEBOOK_VERSION,
        methodology: "codebook_ta",
        change_log: "Scenario 94 codebook for the planted interview themes",
        codes: CODEBOOK.map(([code_id, label, definition, inclusion, exclusion]) => ({
          code_id,
          label,
          definition,
          inclusion_criteria: inclusion,
          exclusion_criteria: exclusion,
        })),
      }));
    codebookVersionId = version.id;
    check("Codebook version ready", Boolean(codebookVersionId), `${CODEBOOK_VERSION} id=${codebookVersionId}`);
  } catch (e) {
    check("Codebook version ready", false, e.message);
    return finish("codebook failed");
  }
  let runInfo = null;
  try {
    runInfo = await api.post(`/api/research-validity/${projectId}/coding-runs`, {
      evidence_unit_ids: units.map((unit) => unit.id),
      codebook_version_id: codebookVersionId,
      max_coders: 3,
      limit: 12,
    });
    check(
      "Coding run with three model coders",
      runInfo.code_application_count > 0,
      `run=${runInfo.id} applications=${runInfo.code_application_count} kappa=${runInfo.kappa} alpha=${runInfo.alpha} status=${runInfo.status}`
    );
  } catch (e) {
    check("Coding run with three model coders", false, e.message);
    return finish("coding run failed");
  }

  // 3. The decider triaged the run's applications (recorded verdicts with the served version).
  const healthBefore = await api.get(`/api/metrics/${projectId}/decision-models`);
  const triage = (healthBefore.scopes || []).filter(
    (scope) => scope.endpoint_id === decider && String(scope.question_set).startsWith("code-application-triage")
  );
  const verdicts = triage.reduce((sum, scope) => sum + scope.verdicts, 0);
  check(
    `${decider} triaged the code applications`,
    verdicts > 0,
    triage.map((s) => `${s.question_set} served=${s.served_model} verdicts=${s.verdicts}`).join("; ") || "no triage scope"
  );

  // 4. Simulated researcher: review every application of this run through the real review route.
  const pending = await api.get(`/api/code-applications/${projectId}/pending`);
  const items = (pending.items || pending || []).filter((item) => item.coding_run_id === runInfo.id);
  let approved = 0;
  let rejected = 0;
  for (const item of items) {
    const theme = themeOf(String(item.source_text || ""));
    const code = String(item.code_id || "");
    // A researcher accepts only the governed code that fits the line; anything else is rejected.
    const matches = Boolean(theme) && code === THEME_CODE[theme];
    const status = matches ? "approved" : "rejected";
    try {
      await api.patch(`/api/code-applications/${item.id}/review?project_id=${projectId}`, {
        review_status: status,
        rationale: matches ? `matches the planted ${theme} theme` : `does not express the planted ${theme || "unknown"} theme`,
      });
      if (matches) approved += 1;
      else rejected += 1;
    } catch {}
  }
  check("Simulated researcher reviewed the run", approved + rejected === items.length && items.length > 0, `${items.length} reviewed: ${approved} approved, ${rejected} rejected`);

  // 5. The reviews labelled the decider's verdicts.
  const healthAfter = await api.get(`/api/metrics/${projectId}/decision-models`);
  const labelled = (healthAfter.scopes || [])
    .filter((scope) => scope.endpoint_id === decider && String(scope.question_set).startsWith("code-application-triage"))
    .reduce((sum, scope) => sum + (scope.labelled || 0), 0);
  check(`Human reviews labelled ${decider}'s verdicts`, labelled > 0, `${labelled} labelled verdict(s); trust is evaluated from 50`);

  return finish(`${checks.filter((c) => c.passed).length}/${checks.length} coding-run triage checks`);
}
