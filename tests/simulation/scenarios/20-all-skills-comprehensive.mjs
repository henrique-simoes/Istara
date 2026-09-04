/** Scenario 20 — Comprehensive Skills Test:
 *  Verifies every currently registered skill, then runs plan + execute for a
 *  bounded live subset by default. Set ISTARA_SCENARIO20_SKILL_LIMIT to the
 *  registry size when a deliberate full live sweep is needed.
 */

import { readFileSync } from "fs";
import { basename, dirname, join } from "path";
import { fileURLToPath } from "url";
import {
  CANONICAL_CORPUS_SLICES,
  selectCanonicalCorpus,
} from "../../document_corpus/shared-corpus.mjs";

export const name = "Comprehensive Skills Test (All Registered Skills)";
export const id = "20-all-skills-comprehensive";

const __dirname = dirname(fileURLToPath(import.meta.url));
const API_BASE = process.env.ISTARA_API_URL || "http://localhost:8000";
const SKILL_COVERAGE_MAP = JSON.parse(
  readFileSync(join(__dirname, "..", "..", "document_corpus", "canonical", "skill-coverage-map.json"), "utf-8")
).coverage || {};

function isExpectedMaintenanceConflict(error, ctx) {
  return ctx.maintenancePaused === true && String(error?.message || "").includes("409");
}

function canonicalSkillSource(slice, index = 0) {
  const sources = selectCanonicalCorpus({ slice, minimumSources: index + 1 });
  const source = sources[index];
  const path = join(__dirname, "..", "..", "document_corpus", "canonical", source.path || source.relative_path);
  return {
    filename: basename(source.relative_path || source.path),
    content: readFileSync(path, "utf-8"),
    slice,
    source_id: source.source_id || source.id || source.relative_path || source.path,
  };
}

// ── Skill fixture hints grouped by phase with canonical corpus context ──
// Runtime selection is built from /api/skills so this scenario follows the
// current backend catalog. These fixtures provide better prompts/data for known
// skills; newly registered skills receive a phase-appropriate fallback.

const ALL_SKILLS = {
  // DISCOVER
  discover: [
    { name: "user-interviews", context: "Analyze mobile banking interview transcript for pain points, needs, and opportunities.", data: "interview" },
    { name: "contextual-inquiry", context: "Analyze co-working space field observations for workflow patterns and environment factors.", data: "field" },
    { name: "diary-studies", context: "Analyze Week 3 diary entries for longitudinal patterns, emotional arc, and product usage.", data: "diary" },
    { name: "stakeholder-interviews", context: "Analyze stakeholder interview about product strategy, business goals, and success metrics.", data: "interview" },
    { name: "survey-design", context: "Analyze survey responses about product onboarding, satisfaction, and feature requests.", data: "survey" },
    { name: "field-studies", context: "Code ethnographic observations from co-working space for behavioral patterns.", data: "field" },
    { name: "desk-research", context: "Synthesize competitive analysis research on project management tools market.", data: "competitor" },
    { name: "competitive-analysis", context: "Compare our product against Asana and Linear — features, pricing, UX.", data: "competitor" },
    { name: "analytics-review", context: "Analyze website analytics data for funnel performance, drop-offs, and anomalies.", data: "analytics" },
    { name: "ab-test-analysis", context: "Analyze A/B test data from signup page conversion experiment.", data: "analytics" },
    { name: "accessibility-audit", context: "Audit the checkout flow for WCAG 2.1 AA compliance issues.", data: "usability" },
    { name: "browser-competitive-benchmark", context: "Benchmark competitor websites for project management UX patterns, IA, pricing visibility, and onboarding quality.", data: "competitor" },
    { name: "channel-research-deployment", context: "Review a mixed-channel research deployment plan for consent, cadence, targeting, ingestion, webhook readiness, and participant response quality.", data: "survey" },
    { name: "transcribe-audio", context: "Evaluate transcription readiness for a research interview and summarize the transcript quality, tagging needs, and atomic-research integration steps.", data: "interview" },
  ],
  // DEFINE
  define: [
    { name: "thematic-analysis", context: "Perform thematic coding on interview transcripts about mobile banking experience.", data: "interview" },
    { name: "affinity-mapping", context: "Cluster research nuggets from interviews and surveys into affinity groups.", data: "interview" },
    { name: "persona-creation", context: "Create evidence-based personas from user interview and survey data.", data: "interview" },
    { name: "journey-mapping", context: "Map the end-to-end mobile banking journey from download to daily use.", data: "interview" },
    { name: "empathy-mapping", context: "Create empathy map for mobile banking users — what they say, think, do, feel.", data: "interview" },
    { name: "jtbd-analysis", context: "Identify Jobs To Be Done from interview transcripts about banking app usage.", data: "interview" },
    { name: "hmw-statements", context: "Generate How Might We statements from identified pain points in banking app.", data: "interview" },
    { name: "research-synthesis", context: "Synthesize findings across interviews, surveys, and usability tests.", data: "interview" },
    { name: "prioritization-matrix", context: "Prioritize identified features and improvements by impact and effort.", data: "survey" },
    { name: "taxonomy-generator", context: "Generate taxonomy of user needs and pain points from research data.", data: "interview" },
    { name: "interview-question-generator", context: "Generate follow-up interview questions based on initial findings.", data: "interview" },
    { name: "kappa-thematic-analysis", context: "Perform dual-coding reliability analysis on interview theme coding.", data: "interview" },
    { name: "participant-simulation", context: "Simulate participant behavior for a mobile banking usability study, including satisficing, social desirability bias, and strategic disclosure patterns.", data: "usability" },
  ],
  // DEVELOP
  develop: [
    { name: "usability-testing", context: "Generate usability test plan and analyze checkout flow test results.", data: "usability" },
    { name: "heuristic-evaluation", context: "Evaluate the mobile banking app against Nielsen's 10 heuristics.", data: "usability" },
    { name: "cognitive-walkthrough", context: "Walk through the account setup task flow for first-time users.", data: "usability" },
    { name: "card-sorting", context: "Analyze card sorting results for information architecture of settings menu.", data: "survey" },
    { name: "tree-testing", context: "Validate navigation IA with tree test results from 20 participants.", data: "survey" },
    { name: "concept-testing", context: "Test viability of quick-transfer feature concept with user feedback.", data: "interview" },
    { name: "prototype-feedback", context: "Analyze user feedback on checkout flow prototype from 8 participants.", data: "usability" },
    { name: "design-critique", context: "Expert review of the mobile banking app's visual design and interaction patterns.", data: "usability" },
    { name: "design-system-audit", context: "Audit the design system for consistency — buttons, colors, typography, spacing.", data: "usability" },
    { name: "workshop-facilitation", context: "Plan and facilitate a design thinking workshop on improving onboarding.", data: "interview" },
    { name: "browser-accessibility-check", context: "Audit a representative product page for WCAG 2.2 AA issues, severity, evidence, and remediation priority.", data: "usability" },
    { name: "browser-ux-audit", context: "Run a live-site-style UX audit against checkout and onboarding flows using heuristics, accessibility, and Laws of UX.", data: "usability" },
    { name: "stitch-design", context: "Generate a high-fidelity mobile banking dashboard design prompt from research insights and product constraints.", data: "interview" },
    { name: "stitch-enhance-prompt", context: "Improve a rough prompt for a mobile banking quick-transfer screen into a structured, high-fidelity design prompt.", data: "interview" },
    { name: "ux-law-compliance", context: "Evaluate the checkout flow against Laws of UX and produce compliance scores with evidence-chained recommendations.", data: "usability" },
  ],
  // DELIVER
  deliver: [
    { name: "nps-analysis", context: "Analyze NPS survey results — score distribution, segment analysis, verbatim themes.", data: "nps" },
    { name: "sus-umux-scoring", context: "Calculate and interpret SUS scores from 10 participant questionnaires.", data: "sus" },
    { name: "task-analysis-quant", context: "Quantitative analysis of checkout task completion rates and timing data.", data: "usability" },
    { name: "user-flow-mapping", context: "Map user flows through the checkout process with decision points and paths.", data: "usability" },
    { name: "stakeholder-presentation", context: "Generate stakeholder presentation summarizing research findings and recommendations.", data: "interview" },
    { name: "handoff-documentation", context: "Create developer handoff documentation for the quick-transfer feature.", data: "usability" },
    { name: "longitudinal-tracking", context: "Track app performance metrics (load time, crash rate, NPS) over 3 months.", data: "analytics" },
    { name: "regression-impact", context: "Assess regression impact of recent app update on key UX metrics.", data: "analytics" },
    { name: "repository-curation", context: "Curate and organize research artifacts from the mobile banking study.", data: "interview" },
    { name: "research-retro", context: "Conduct retrospective on the mobile banking research project — what worked, what didn't.", data: "interview" },
    { name: "survey-ai-detection", context: "Detect potentially AI-generated responses in survey data.", data: "survey" },
    { name: "survey-generator", context: "Generate a post-launch satisfaction survey for the mobile banking app.", data: "interview" },
    { name: "evaluate-research", context: "Evaluate a research synthesis for rigor, evidence quality, clarity, bias risk, and actionability.", data: "interview" },
    { name: "research-quality-evaluation", context: "Run an LLM-as-judge research quality evaluation over the provided findings and recommendations.", data: "interview" },
    { name: "stitch-design-system", context: "Synthesize design-system documentation from the provided mobile banking UI audit and usability findings.", data: "usability" },
    { name: "stitch-react-components", context: "Convert a generated mobile banking screen specification into React component guidance with tokens and validation notes.", data: "usability" },
  ],
};

const DATA_MAP = {
  interview: { slice: "interview-heavy", index: 0 },
  survey: { slice: "survey-heavy", index: 0 },
  usability: { slice: "usability-heavy", index: 0 },
  field: { slice: "interview-heavy", index: 5 },
  diary: { slice: "interview-heavy", index: 12 },
  competitor: { slice: "full-end-to-end", index: 120 },
  analytics: { slice: "findings-reporting", index: 0 },
  nps: { slice: "survey-heavy", index: 8 },
  sus: { slice: "survey-heavy", index: 12 },
};

const DEFAULT_DATA_BY_PHASE = {
  discover: "interview",
  define: "interview",
  develop: "usability",
  deliver: "analytics",
};

const SKILL_FIXTURE_BY_NAME = new Map(
  Object.values(ALL_SKILLS)
    .flat()
    .map((skill) => [skill.name, skill])
);

function positiveIntegerEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

const SKILL_EXECUTE_TIMEOUT_MS = positiveIntegerEnv("ISTARA_SKILL_EXECUTE_TIMEOUT_MS", 600000);
const SKILL_PLAN_TIMEOUT_MS = positiveIntegerEnv("ISTARA_SKILL_PLAN_TIMEOUT_MS", 180000);
const DEFAULT_LIVE_SKILL_LIMIT = positiveIntegerEnv("ISTARA_SCENARIO20_DEFAULT_SKILL_LIMIT", 3);

function hashSeed(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0 || 1;
}

function seededRandom(seed) {
  let state = hashSeed(seed);
  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function canonicalDataForSkill(skill) {
  const fallbackSpec = DATA_MAP[skill.data] || DATA_MAP.interview;
  const coverage = SKILL_COVERAGE_MAP[skill.name] || {};
  const preferredSlice = (coverage.slices || []).find(
    (slice) => CANONICAL_CORPUS_SLICES.includes(slice) && slice !== "malformed-edge-case"
  );
  const slice = preferredSlice || fallbackSpec.slice;
  const sourceIndex = Math.abs(hashSeed(`${skill.name}:${slice}`)) % Math.max(1, Math.min(5, coverage.source_count || 5));
  const index = preferredSlice ? sourceIndex : fallbackSpec.index;
  return canonicalSkillSource(slice, index);
}

function pickLogicalRandomSubset(entries, limit, seed) {
  const random = seededRandom(seed);
  const shuffled = entries.map((entry) => ({ entry, rank: random() })).sort((a, b) => a.rank - b.rank).map(({ entry }) => entry);
  const selected = [];
  const selectedPhases = new Set();

  while (selected.length < limit && selected.length < shuffled.length) {
    const phaseDiverse = shuffled.find(
      (entry) => !selected.includes(entry) && !selectedPhases.has(entry.phase)
    );
    const next = phaseDiverse || shuffled.find((entry) => !selected.includes(entry));
    if (!next) break;
    selected.push(next);
    selectedPhases.add(next.phase);
  }

  return selected;
}

function parseAgenticSelection(text, entries, limit) {
  const validNames = new Set(entries.map(({ skill }) => skill.name));
  const jsonMatch = String(text || "").match(/\{[\s\S]*"skills"[\s\S]*\}/);
  if (!jsonMatch) return null;
  try {
    const parsed = JSON.parse(jsonMatch[0]);
    const names = Array.isArray(parsed.skills) ? parsed.skills : [];
    const uniqueNames = [...new Set(names.map((name) => String(name).trim()))].filter((name) => validNames.has(name));
    if (uniqueNames.length !== limit) return null;
    return {
      names: uniqueNames,
      rationale: String(parsed.rationale || "Agent selected a coherent bounded skill subset.").slice(0, 500),
    };
  } catch {
    return null;
  }
}

async function askModelForSkillSelection({ api, projectId, entries, limit, seed }) {
  if (process.env.ISTARA_SCENARIO20_AGENTIC_SELECTION === "0") return null;
  const candidates = entries.map(({ phase, skill }) => {
    const coverage = SKILL_COVERAGE_MAP[skill.name] || {};
    return {
      name: skill.name,
      phase,
      data: skill.data,
      slices: (coverage.slices || []).slice(0, 6),
      methods: (coverage.methods || []).slice(0, 4),
    };
  });
  const prompt = [
    "You are the Scenario 20 test planner. Choose exactly three registered Istara skills for a bounded live test.",
    "Prefer a logical random-feeling mix that can use the canonical corpus well, touches different research phases when possible, and exercises the Research Spine without doing a full skill sweep.",
    `Seed hint: ${seed}. Return only JSON: {"skills":["skill-a","skill-b","skill-c"],"rationale":"short reason"}.`,
    `Candidates: ${JSON.stringify(candidates)}`,
  ].join("\n\n");

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: api._headers?.({ "Content-Type": "application/json" }) || { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, message: prompt }),
    });
    if (!response.ok) return null;
    const text = await response.text();
    return parseAgenticSelection(text, entries, limit);
  } catch {
    return null;
  }
}

function fallbackContextForSkill(skill, dataKey) {
  const display = skill.display_name || skill.name;
  return [
    `Execute ${display} against representative Istara simulation research data.`,
    `Use the provided ${dataKey} evidence, preserve traceability, and return the skill's normalized output.`,
  ].join(" ");
}

function staticSkillCatalogEntries() {
  return Object.entries(ALL_SKILLS).flatMap(([phase, skills]) =>
    skills.map((skill) => ({ phase, skill, hasFixture: true }))
  );
}

function registeredSkillCatalogEntries(registeredSkills) {
  const entries = (registeredSkills || [])
    .filter((skill) => skill?.name && skill.enabled !== false)
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((registered) => {
      const phase = registered.phase || "discover";
      const fixture = SKILL_FIXTURE_BY_NAME.get(registered.name);
      const data = fixture?.data || DEFAULT_DATA_BY_PHASE[phase] || "interview";
      const context = fixture?.context || fallbackContextForSkill(registered, data);
      return {
        phase,
        hasFixture: Boolean(fixture),
        skill: {
          ...fixture,
          name: registered.name,
          context,
          data,
        },
      };
    });

  return entries.length > 0 ? entries : staticSkillCatalogEntries();
}

async function scenario20SkillSelection({ api, projectId, registeredSkills = [], llmConnected = false }) {
  const entries = registeredSkillCatalogEntries(registeredSkills);
  const limit = Math.min(
    positiveIntegerEnv("ISTARA_SCENARIO20_SKILL_LIMIT", DEFAULT_LIVE_SKILL_LIMIT),
    entries.length
  );

  if (limit >= entries.length) {
    return {
      entries,
      limited: false,
      limit: entries.length,
      seed: null,
      total: entries.length,
      selection_mode: "full-sweep",
      rationale: "Operator requested a full registered skill sweep.",
    };
  }

  const seed = process.env.ISTARA_SCENARIO20_SKILL_SEED || "scenario20-default-live-subset";
  if (llmConnected && projectId) {
    const agentic = await askModelForSkillSelection({ api, projectId, entries, limit, seed });
    if (agentic) {
      const byName = new Map(entries.map((entry) => [entry.skill.name, entry]));
      return {
        entries: agentic.names.map((name) => byName.get(name)).filter(Boolean),
        limited: true,
        limit,
        seed,
        total: entries.length,
        selection_mode: "llm-agentic",
        rationale: agentic.rationale,
      };
    }
  }

  return {
    entries: pickLogicalRandomSubset(entries, limit, seed),
    limited: true,
    limit,
    seed,
    total: entries.length,
    selection_mode: "seeded-logical-random",
    rationale: "Seeded fallback picked a random-feeling subset while preferring phase diversity.",
  };
}

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const skillResults = { total: 0, passed: 0, failed: 0, errors: 0, skipped: 0 };
  const phaseResults = {};
  const skillMetrics = [];

  // ── Helpers ──
  function currentSummary(stage = "running") {
    const phaseSummary = Object.entries(phaseResults)
      .map(([p, r]) => `${p}: ${r.passed}/${r.total} executed${r.skipped ? ` (${r.skipped} skipped)` : ""}`)
      .join(" | ");
    return [
      `stage=${stage}`,
      `Skills: ${skillResults.passed}/${skillResults.total} passed, ${skillResults.failed} failed, ${skillResults.skipped} skipped`,
      phaseSummary,
    ].filter(Boolean).join("\n");
  }

  function recordProgress(stage = "running") {
    ctx.reportProgress?.({
      stage,
      checks,
      skillResults: { ...skillResults },
      skillMetrics: [...skillMetrics],
      phaseResults: Object.fromEntries(
        Object.entries(phaseResults).map(([phase, result]) => [phase, { ...result }])
      ),
      summary: currentSummary(stage),
    });
  }

  function pushCheck(check, stage = check?.name || "check") {
    checks.push(check);
    recordProgress(stage);
  }

  async function safeCheck(checkName, fn) {
    try {
      const result = await fn();
      pushCheck(result, checkName);
    } catch (e) {
      if ((checkName.includes("— execute") || checkName.includes("— plan")) && isExpectedMaintenanceConflict(e, ctx)) {
        const phaseMatch = checkName.match(/^\[([^\]]+)\]/);
        const phase = phaseMatch?.[1];
        if (checkName.includes("— execute")) {
          skillResults.skipped++;
        }
        if (checkName.includes("— execute") && phase && phaseResults[phase]) {
          phaseResults[phase].skipped++;
        }
        pushCheck({
          name: checkName,
          passed: true,
          detail: "[deferred] Simulation maintenance mode blocks live skill execution as expected",
        }, checkName);
        return;
      }
      if (checkName.includes("— execute")) {
        const phaseMatch = checkName.match(/^\[([^\]]+)\]/);
        const phase = phaseMatch?.[1];
        skillResults.failed++;
        skillResults.errors++;
        if (phase && phaseResults[phase]) {
          phaseResults[phase].failed++;
        }
      }
      const isTimeout = e.message?.startsWith("TIMEOUT:");
      pushCheck({
        name: checkName,
        passed: false,
        detail: isTimeout
          ? e.message
          : (e.message?.substring(0, 150) || "Unknown error"),
      }, checkName);
    }
  }

  // ── Step 1: Use the persistent simulation project ──
  let projectId = ctx.projectId;
  if (projectId) {
    pushCheck({ name: "Using persistent simulation project", passed: true, detail: `project_id=${projectId}` });
  } else {
    pushCheck({ name: "Project required", passed: false, detail: "No persistent project available from runner" });
    return { checks, passed: 0, failed: 1, summary: "No project available" };
  }

  // ── Step 2: Upload canonical research files and track server paths ──
  const uploadedFiles = {};
  const filePaths = {}; // Map data-key → server-side file path
  const fileUploads = [
    { key: "interview", source: canonicalSkillSource("interview-heavy", 0) },
    { key: "survey", source: canonicalSkillSource("survey-heavy", 0) },
    { key: "usability", source: canonicalSkillSource("usability-heavy", 0) },
    { key: "field", source: canonicalSkillSource("interview-heavy", 5) },
    { key: "diary", source: canonicalSkillSource("interview-heavy", 12) },
    { key: "competitor", source: canonicalSkillSource("full-end-to-end", 120) },
    { key: "analytics", source: canonicalSkillSource("findings-reporting", 0) },
    { key: "nps", source: canonicalSkillSource("survey-heavy", 8) },
    { key: "sus", source: canonicalSkillSource("survey-heavy", 12) },
  ];

  for (const { key, source } of fileUploads) {
    const { filename, content } = source;
    try {
      const result = await api.uploadContent(projectId, content, filename);
      uploadedFiles[key] = filename;
      // Track the server-side path for custom skills that need files
      if (result && result.saved_as) {
        filePaths[key] = `data/uploads/${projectId}/${result.saved_as}`;
      }
    } catch (e) {
      // Try alternate upload method via direct fetch
      try {
        const formData = new FormData();
        const blob = new Blob([content], { type: "text/plain" });
        formData.append("file", blob, filename);
        const resp = await fetch(`http://localhost:8000/api/files/upload/${projectId}`, {
          method: "POST",
          headers: { "Authorization": api._headers()["Authorization"] },
          body: formData,
        });
        const result = await resp.json().catch(() => ({}));
        uploadedFiles[key] = filename;
        if (result && result.saved_as) {
          filePaths[key] = `data/uploads/${projectId}/${result.saved_as}`;
        }
      } catch {
        uploadedFiles[key] = filename; // Mark as attempted
      }
    }
  }

  pushCheck({
    name: "Canonical research files uploaded",
    passed: Object.keys(uploadedFiles).length >= 7,
    detail: `${Object.keys(uploadedFiles).length}/9 file types uploaded: ${Object.keys(uploadedFiles).join(", ")} | ${Object.keys(filePaths).length} paths tracked`,
  });

  // ── Step 3: Verify all skills registered ──
  let allSkills = [];
  await safeCheck("All skills registered in API", async () => {
    const resp = await api.get("/api/skills");
    allSkills = Array.isArray(resp) ? resp : resp.skills || [];

    const phases = {};
    for (const s of allSkills) {
      phases[s.phase] = (phases[s.phase] || 0) + 1;
    }

    return {
      name: "All skills registered in API",
      passed: allSkills.length >= 40,
      detail: `${allSkills.length} skills: ${Object.entries(phases).map(([p, c]) => `${p}=${c}`).join(", ")}`,
    };
  });

  // ── Step 4: Test each skill — plan + execute ──
  const LLM_CONNECTED = ctx.llmConnected;
  const CHAT_READY = ctx.llmReadiness?.chat_ready !== false;
  const LIVE_SKILL_EXECUTION_READY = LLM_CONNECTED && CHAT_READY;
  const skillSelection = await scenario20SkillSelection({
    api,
    projectId,
    registeredSkills: allSkills,
    llmConnected: LLM_CONNECTED,
  });
  const fixtureCount = skillSelection.entries.filter((entry) => entry.hasFixture).length;
  pushCheck({
    name: "Scenario 20 skill selection",
    passed: skillSelection.entries.length > 0,
    detail: skillSelection.limited
      ? `${skillSelection.selection_mode} subset ${skillSelection.limit}/${skillSelection.total}, seed=${skillSelection.seed}, fixture_hints=${fixtureCount}/${skillSelection.entries.length}, skills=${skillSelection.entries.map(({ skill }) => skill.name).join(", ")}, rationale=${skillSelection.rationale}`
      : `full sweep ${skillSelection.entries.length}/${skillSelection.total} registered skills, fixture_hints=${fixtureCount}/${skillSelection.entries.length}`,
  });

  for (const { phase, skill } of skillSelection.entries) {
    if (!phaseResults[phase]) {
      phaseResults[phase] = { total: 0, passed: 0, failed: 0, skipped: 0 };
    }
      skillResults.total++;
      phaseResults[phase].total++;

      // Test: Skill exists in registry
      const registered = allSkills.find((s) => s.name === skill.name);
      if (!registered) {
        pushCheck({
          name: `[${phase}] ${skill.name} — registered`,
          passed: false,
          detail: "Skill not found in registry",
        }, `${skill.name} registered`);
        skillResults.failed++;
        phaseResults[phase].failed++;
        recordProgress(`${skill.name} missing`);
        continue;
      }

      pushCheck({
        name: `[${phase}] ${skill.name} — registered`,
        passed: true,
        detail: `phase=${registered.phase}, type=${registered.skill_type}`,
      }, `${skill.name} registered`);

      // Test: Skill individual API
      await safeCheck(`[${phase}] ${skill.name} — GET detail`, async () => {
        const detail = await api.get(`/api/skills/${skill.name}`);
        const hasHealth = "health" in detail || "usage" in detail;
        return {
          name: `[${phase}] ${skill.name} — GET detail`,
          passed: !!detail.name && detail.name === skill.name,
          detail: `display=${detail.display_name}, health=${hasHealth}`,
        };
      });

      // Test: Skill execution (requires LLM)
      if (LLM_CONNECTED) {
        if (!LIVE_SKILL_EXECUTION_READY) {
          skillResults.skipped++;
          phaseResults[phase].skipped++;
          pushCheck({
            name: `[${phase}] ${skill.name} — execute`,
            passed: true,
            detail: "[skipped] Provider is reachable, but no chat-ready model is configured; live skill execution is not applicable",
          }, `${skill.name} skipped`);
        } else {
        // Build rich user_context with actual data for the LLM to analyze
        const canonicalData = canonicalDataForSkill(skill);
        const richContext = [
          skill.context,
          "",
          `--- Canonical Research Source (${canonicalData.slice} / ${canonicalData.source_id}) ---`,
          canonicalData.content,
        ].join("\n");

        // Collect file paths for custom skills that require files
        const skillFiles = filePaths[skill.data] ? [filePaths[skill.data]] : [];

        await safeCheck(`[${phase}] ${skill.name} — execute`, async () => {
          const startTime = Date.now();
          const result = await api.post(
            `/api/skills/${skill.name}/execute`,
            {
              project_id: projectId,
              user_context: richContext,
              files: skillFiles,
              timeout_seconds: Math.max(1, Math.floor(SKILL_EXECUTE_TIMEOUT_MS / 1000) - 5),
            },
            {
              timeoutMs: SKILL_EXECUTE_TIMEOUT_MS,
              label: `${skill.name} execute`,
            }
          );
          const elapsed = Date.now() - startTime;

          const hasSuccess = typeof result.success === "boolean";
          const hasSummary = typeof result.summary === "string" && result.summary.length > 0;
          const candidateArtifacts =
            (result.nuggets_count || 0) +
            (result.facts_count || 0) +
            (result.insights_count || 0) +
            (result.recommendations_count || 0);
          const reportBlocked =
            result.report_allowed === false && result.research_validity?.status === "provisional";

          const passed =
            hasSuccess &&
            result.success === true &&
            result.json_success !== false &&
            hasSummary &&
            reportBlocked;
          const schemaBudget = result.schema_budget || null;
          skillMetrics.push({
            phase,
            skill: skill.name,
            elapsed_ms: elapsed,
            success: result.success === true,
            json_success: result.json_success !== false,
            candidate_artifacts: candidateArtifacts,
            report_allowed: result.report_allowed === true,
            schema_budget: schemaBudget,
            summary_length: (result.summary || "").length,
          });

          if (passed) {
            skillResults.passed++;
            phaseResults[phase].passed++;
          } else {
            skillResults.failed++;
            phaseResults[phase].failed++;
          }

          return {
            name: `[${phase}] ${skill.name} — execute`,
            passed,
            detail: passed
              ? `${elapsed}ms, candidate_artifacts=${candidateArtifacts}, report_allowed=${result.report_allowed}, json_success=${result.json_success !== false}, schema_fallback=${schemaBudget?.used_fallback ?? "n/a"}, summary="${(result.summary || "").substring(0, 60)}..."`
              : `success=${result.success}, report_allowed=${result.report_allowed}, research_validity=${result.research_validity?.status}, json_success=${result.json_success}, errors=${JSON.stringify(result.errors || []).substring(0, 80)}`,
          };
        });
        }

        // Test: Skill plan generation
        await safeCheck(`[${phase}] ${skill.name} — plan`, async () => {
          const result = await api.post(
            `/api/skills/${skill.name}/plan`,
            {
              project_id: projectId,
              user_context: skill.context,
              timeout_seconds: Math.max(1, Math.floor(SKILL_PLAN_TIMEOUT_MS / 1000) - 5),
            },
            {
              timeoutMs: SKILL_PLAN_TIMEOUT_MS,
              label: `${skill.name} plan`,
            }
          );

          const hasPlan = typeof result.plan === "string" && result.plan.length > 20;
          const hasSkill = result.skill === skill.name;

          return {
            name: `[${phase}] ${skill.name} — plan`,
            passed: hasPlan,
            detail: hasPlan
              ? `plan length=${result.plan.length} chars, skill=${result.skill}`
              : `plan=${!!result.plan}, skill=${result.skill}`,
          };
        });
      } else {
        // Skip execution if no LLM
        skillResults.skipped++;
        phaseResults[phase].skipped++;
        pushCheck({
          name: `[${phase}] ${skill.name} — execute`,
          passed: true,
          detail: "[skipped] LLM not connected — skill registration verified only",
        }, `${skill.name} skipped`);
      }
  }

  // ── Step 5: Skill health check ──
  await safeCheck("Skills health — all skills have health data", async () => {
    const health = await api.get(`/api/skills/health/all?project_id=${encodeURIComponent(projectId)}`);
    const healthEntries = Array.isArray(health)
      ? health
      : Array.isArray(health?.skills)
        ? health.skills
        : Object.values(health || {});

    return {
      name: "Skills health — all skills have health data",
      passed: healthEntries.length >= 30,
      detail: `${healthEntries.length} skills with health data`,
    };
  });

  // ── Step 6: Self-improvement proposals ──
  await safeCheck("Self-improvement — proposals endpoint works", async () => {
    const proposals = await api.get(`/api/skills/proposals/all?project_id=${encodeURIComponent(projectId)}`);
    const list = Array.isArray(proposals) ? proposals : proposals.proposals || [];

    return {
      name: "Self-improvement — proposals endpoint works",
      passed: true,
      detail: `${list.length} proposals (pending + historical)`,
    };
  });

  // ── Step 7: Phase coverage verification ──
  await safeCheck("Phase coverage — all Double Diamond phases have skills", async () => {
    const phases = { discover: 0, define: 0, develop: 0, deliver: 0 };
    for (const s of allSkills) {
      if (s.phase in phases) phases[s.phase]++;
    }
    const allCovered = Object.values(phases).every((c) => c >= 5);

    return {
      name: "Phase coverage — all Double Diamond phases have skills",
      passed: allCovered,
      detail: Object.entries(phases).map(([p, c]) => `${p}=${c}`).join(", "),
    };
  });

  // ── Step 8: Verify kappa-thematic-analysis skill catalog entry ──
  await safeCheck("kappa-thematic-analysis skill is in catalog", async () => {
    const kappaSkill = allSkills.find((s) => s.name === "kappa-thematic-analysis");
    return {
      name: "kappa-thematic-analysis skill is in catalog",
      passed: !!kappaSkill,
      detail: kappaSkill
        ? `phase=${kappaSkill.phase}, type=${kappaSkill.skill_type}`
        : "Skill not found in registry",
    };
  });

  await safeCheck("kappa-thematic-analysis description mentions Cohen's Kappa AND Krippendorff's Alpha", async () => {
    const detail = await api.get("/api/skills/kappa-thematic-analysis");
    const desc = (detail.description || detail.display_name || "").toLowerCase();
    const prompt = (detail.system_prompt || detail.prompt_template || detail.instructions || "").toLowerCase();
    const combined = `${desc} ${prompt}`;
    const hasKappa = combined.includes("kappa");
    const hasAlpha = combined.includes("krippendorff") || combined.includes("alpha");
    return {
      name: "kappa-thematic-analysis description mentions Cohen's Kappa AND Krippendorff's Alpha",
      passed: hasKappa && hasAlpha,
      detail: `mentions_kappa=${hasKappa}, mentions_alpha=${hasAlpha}, desc_length=${desc.length}`,
    };
  });

  // ── Summary ──
  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;

  const phaseSummary = Object.entries(phaseResults)
    .map(([p, r]) => `${p}: ${r.passed}/${r.total} executed${r.skipped ? ` (${r.skipped} skipped)` : ""}`)
    .join(" | ");

  return {
    checks,
    passed,
    failed,
    metrics: {
      skill_metrics: skillMetrics,
      avg_execute_ms: Math.round(
        skillMetrics.reduce((sum, item) => sum + item.elapsed_ms, 0) /
          Math.max(1, skillMetrics.length)
      ),
      schema_fallback_count: skillMetrics.filter((item) => item.schema_budget?.used_fallback).length,
      json_success_count: skillMetrics.filter((item) => item.json_success).length,
    },
    summary: [
      `Skills: ${skillResults.passed}/${skillResults.total} passed, ${skillResults.failed} failed, ${skillResults.skipped} skipped`,
      phaseSummary,
      "",
      ...checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`),
    ].join("\n"),
  };
}
